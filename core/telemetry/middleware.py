"""
FastAPI Telemetry Middleware.
Auto-instruments requests with tracing, metrics, and logging.
"""

import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import request_counter, request_latency, active_connections
from .tracing import tracer, SpanStatus
from .logging import logger


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive telemetry middleware for FastAPI.
    
    Automatically:
    - Creates trace spans for each request
    - Records request metrics (count, latency)
    - Logs request/response details
    - Propagates trace context
    """
    
    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Extract or generate trace ID
        trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex[:16]
        
        # Start span
        span = tracer.start_span(
            name=f"{request.method} {request.url.path}",
            trace_id=trace_id,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.path": request.url.path,
                "http.host": request.headers.get("host", ""),
                "http.user_agent": request.headers.get("user-agent", "")[:100],
                "http.client_ip": self._get_client_ip(request)
            }
        )
        
        # Track active connections
        active_connections.inc()
        
        start_time = time.time()
        status_code = 500
        
        try:
            # Log request
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                trace_id=trace_id
            )
            
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Set span attributes
            span.set_attribute("http.status_code", status_code)
            span.set_attribute("http.response_size", response.headers.get("content-length", 0))
            
            if status_code >= 400:
                span.set_status(SpanStatus.ERROR, f"HTTP {status_code}")
            else:
                span.set_status(SpanStatus.OK)
            
            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            
            return response
            
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            
            logger.exception(
                f"Request failed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                trace_id=trace_id
            )
            
            raise
            
        finally:
            # Calculate latency
            latency = time.time() - start_time
            span.set_attribute("http.latency_ms", latency * 1000)
            
            # Record metrics
            request_counter.inc(
                method=request.method,
                endpoint=self._normalize_path(request.url.path),
                status=str(status_code)
            )
            
            request_latency.observe(
                latency,
                method=request.method,
                endpoint=self._normalize_path(request.url.path)
            )
            
            active_connections.dec()
            
            # End span
            tracer.end_span(span)
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {status_code}",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                latency_ms=round(latency * 1000, 2),
                trace_id=trace_id
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        # Check forwarded headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metrics.
        Replaces dynamic segments with placeholders.
        """
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            # Replace UUIDs
            if len(part) == 36 and part.count("-") == 4:
                normalized.append("{id}")
            # Replace numeric IDs
            elif part.isdigit():
                normalized.append("{id}")
            # Replace hex strings (like trace IDs)
            elif len(part) >= 16 and all(c in "0123456789abcdef" for c in part.lower()):
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/".join(normalized)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request context for logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Set logging context
        logger.set_context(
            request_id=request.headers.get("X-Request-ID", uuid.uuid4().hex[:8]),
            user_agent=request.headers.get("user-agent", "")[:50]
        )
        
        try:
            response = await call_next(request)
            return response
        finally:
            logger.clear_context()


def add_telemetry(app):
    """
    Add telemetry middleware to FastAPI app.
    
    Usage:
        from core.telemetry import add_telemetry
        add_telemetry(app)
    """
    app.add_middleware(TelemetryMiddleware)
    app.add_middleware(RequestContextMiddleware)
    
    logger.info("Telemetry middleware enabled")


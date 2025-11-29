"""
Distributed Tracing System.
Lightweight OpenTelemetry-compatible tracing.
"""

import time
import uuid
import threading
import contextvars
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
import json


class SpanStatus(Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """
    A single unit of work in a trace.
    """
    trace_id: str
    span_id: str
    name: str
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    
    def set_attribute(self, key: str, value: Any):
        """Set span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        """Add event to span."""
        self.events.append(SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attributes or {}
        ))
    
    def set_status(self, status: SpanStatus, message: str = None):
        """Set span status."""
        self.status = status
        if message:
            self.attributes["status_message"] = message
    
    def end(self):
        """End the span."""
        self.end_time = time.time()
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                    "attributes": e.attributes
                }
                for e in self.events
            ]
        }


# Context variable for current span
_current_span: contextvars.ContextVar[Optional[Span]] = contextvars.ContextVar(
    "current_span", default=None
)


class Tracer:
    """
    Distributed tracer with context propagation.
    """
    
    def __init__(self, service_name: str = "goai-platform", max_spans: int = 10000):
        self.service_name = service_name
        self.max_spans = max_spans
        self._spans: List[Span] = []
        self._traces: Dict[str, List[Span]] = {}
        self._lock = threading.Lock()
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return uuid.uuid4().hex[:16]
    
    def start_span(
        self,
        name: str,
        trace_id: str = None,
        parent_id: str = None,
        attributes: Dict[str, Any] = None
    ) -> Span:
        """
        Start a new span.
        
        If no trace_id provided, creates new trace.
        If parent_id provided, creates child span.
        """
        # Get parent from context if not provided
        current = _current_span.get()
        if current and not parent_id:
            trace_id = current.trace_id
            parent_id = current.span_id
        
        span = Span(
            trace_id=trace_id or self._generate_id(),
            span_id=self._generate_id(),
            name=name,
            parent_id=parent_id,
            attributes=attributes or {}
        )
        
        span.set_attribute("service.name", self.service_name)
        
        # Set as current span
        _current_span.set(span)
        
        return span
    
    def end_span(self, span: Span):
        """End and record a span."""
        span.end()
        
        with self._lock:
            self._spans.append(span)
            
            # Store by trace
            if span.trace_id not in self._traces:
                self._traces[span.trace_id] = []
            self._traces[span.trace_id].append(span)
            
            # Cleanup old spans
            if len(self._spans) > self.max_spans:
                old_spans = self._spans[:len(self._spans) - self.max_spans]
                self._spans = self._spans[-self.max_spans:]
                
                # Remove old traces
                old_traces = set(s.trace_id for s in old_spans)
                for trace_id in old_traces:
                    if trace_id in self._traces:
                        del self._traces[trace_id]
        
        # Restore parent as current
        if span.parent_id:
            for s in reversed(self._spans):
                if s.span_id == span.parent_id:
                    _current_span.set(s)
                    return
        _current_span.set(None)
    
    def get_current_span(self) -> Optional[Span]:
        """Get current active span."""
        return _current_span.get()
    
    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a trace."""
        with self._lock:
            spans = self._traces.get(trace_id, [])
            return [s.to_dict() for s in spans]
    
    def get_recent_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent traces."""
        with self._lock:
            # Get unique trace IDs from recent spans
            seen = set()
            traces = []
            
            for span in reversed(self._spans):
                if span.trace_id not in seen and span.parent_id is None:
                    seen.add(span.trace_id)
                    traces.append({
                        "trace_id": span.trace_id,
                        "name": span.name,
                        "start_time": datetime.fromtimestamp(span.start_time).isoformat(),
                        "duration_ms": span.duration_ms,
                        "status": span.status.value,
                        "span_count": len(self._traces.get(span.trace_id, []))
                    })
                    
                    if len(traces) >= limit:
                        break
            
            return traces
    
    def trace(self, name: str = None, attributes: Dict[str, Any] = None):
        """
        Decorator for tracing functions.
        
        Usage:
            @tracer.trace("my_operation")
            def my_function():
                ...
        """
        def decorator(func: Callable):
            span_name = name or func.__name__
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span = self.start_span(span_name, attributes=attributes)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(SpanStatus.OK)
                    return result
                except Exception as e:
                    span.set_status(SpanStatus.ERROR, str(e))
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
                finally:
                    self.end_span(span)
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span = self.start_span(span_name, attributes=attributes)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(SpanStatus.OK)
                    return result
                except Exception as e:
                    span.set_status(SpanStatus.ERROR, str(e))
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
                finally:
                    self.end_span(span)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    def stats(self) -> Dict[str, Any]:
        """Get tracer statistics."""
        with self._lock:
            status_counts = {}
            for span in self._spans:
                status = span.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_spans": len(self._spans),
                "total_traces": len(self._traces),
                "max_spans": self.max_spans,
                "by_status": status_counts
            }


# Global tracer instance
tracer = Tracer()


def get_tracer() -> Tracer:
    """Get global tracer."""
    return tracer


class SpanContext:
    """
    Context manager for spans.
    
    Usage:
        with SpanContext("my_operation") as span:
            span.set_attribute("key", "value")
            ...
    """
    
    def __init__(self, name: str, attributes: Dict[str, Any] = None):
        self.name = name
        self.attributes = attributes
        self.span: Optional[Span] = None
    
    def __enter__(self) -> Span:
        self.span = tracer.start_span(self.name, attributes=self.attributes)
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.span.set_status(SpanStatus.ERROR, str(exc_val))
            self.span.set_attribute("error.type", exc_type.__name__)
        else:
            self.span.set_status(SpanStatus.OK)
        
        tracer.end_span(self.span)
        return False


class AsyncSpanContext:
    """Async context manager for spans."""
    
    def __init__(self, name: str, attributes: Dict[str, Any] = None):
        self.name = name
        self.attributes = attributes
        self.span: Optional[Span] = None
    
    async def __aenter__(self) -> Span:
        self.span = tracer.start_span(self.name, attributes=self.attributes)
        return self.span
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.span.set_status(SpanStatus.ERROR, str(exc_val))
            self.span.set_attribute("error.type", exc_type.__name__)
        else:
            self.span.set_status(SpanStatus.OK)
        
        tracer.end_span(self.span)
        return False


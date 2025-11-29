# Telemetry Module - Metrics, Tracing, Logging
from .metrics import (
    metrics,
    MetricsRegistry,
    Counter,
    Gauge,
    Histogram,
    request_counter,
    request_latency,
    llm_requests,
    llm_tokens,
    llm_latency,
    embedding_requests,
    cache_operations,
    active_connections,
    queue_size,
    documents_total
)

from .tracing import (
    tracer,
    Tracer,
    Span,
    SpanStatus,
    SpanContext,
    AsyncSpanContext,
    get_tracer
)

from .logging import (
    logger,
    StructuredLogger,
    LogLevel,
    get_logger,
    setup_logging
)

from .middleware import (
    TelemetryMiddleware,
    RequestContextMiddleware,
    add_telemetry
)

__all__ = [
    # Metrics
    "metrics",
    "MetricsRegistry",
    "Counter",
    "Gauge", 
    "Histogram",
    "request_counter",
    "request_latency",
    "llm_requests",
    "llm_tokens",
    "llm_latency",
    "embedding_requests",
    "cache_operations",
    "active_connections",
    "queue_size",
    "documents_total",
    # Tracing
    "tracer",
    "Tracer",
    "Span",
    "SpanStatus",
    "SpanContext",
    "AsyncSpanContext",
    "get_tracer",
    # Logging
    "logger",
    "StructuredLogger",
    "LogLevel",
    "get_logger",
    "setup_logging",
    # Middleware
    "TelemetryMiddleware",
    "RequestContextMiddleware",
    "add_telemetry"
]


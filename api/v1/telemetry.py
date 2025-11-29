"""
Telemetry API - Metrics, traces, and logs endpoints.
"""

from fastapi import APIRouter, Query, Response
from fastapi.responses import PlainTextResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from core.telemetry import (
    metrics,
    tracer,
    logger,
    documents_total,
    queue_size
)

router = APIRouter()


class TelemetryOverview(BaseModel):
    """Telemetry system overview."""
    metrics: Dict[str, Any]
    tracing: Dict[str, Any]
    logging: Dict[str, Any]


class TraceDetail(BaseModel):
    """Trace detail response."""
    trace_id: str
    spans: List[Dict[str, Any]]


@router.get("/overview", response_model=TelemetryOverview)
async def get_telemetry_overview():
    """
    Get overview of all telemetry systems.
    """
    return {
        "metrics": {
            "total_metrics": len(metrics.collect_all()),
            **_get_key_metrics()
        },
        "tracing": tracer.stats(),
        "logging": logger.stats()
    }


def _get_key_metrics() -> Dict[str, Any]:
    """Extract key metrics for overview."""
    all_metrics = metrics.collect_all()
    
    result = {}
    for m in all_metrics:
        if m["name"] == "goai_requests_total":
            result["total_requests"] = m.get("value", 0)
        elif m["name"] == "goai_llm_requests_total":
            result["llm_requests"] = m.get("value", 0)
        elif m["name"] == "goai_request_duration_seconds":
            result["avg_latency_ms"] = m.get("mean", 0) * 1000
    
    return result


# ============ METRICS ============

@router.get("/metrics")
async def get_metrics():
    """
    Get all metrics in JSON format.
    """
    return {
        "metrics": metrics.collect_all(),
        "count": len(metrics.collect_all())
    }


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus text format.
    
    Compatible with Prometheus scraping.
    """
    # Update gauge metrics
    try:
        from core.performance import get_task_queue_sync
        task_queue = get_task_queue_sync()
        queue_size.set(task_queue._queue.qsize())
    except:
        pass
    
    try:
        from modules.rag import rag_engine
        stats = rag_engine.get_stats()
        if "database" in stats:
            documents_total.set(stats["database"].get("documents", 0))
    except:
        pass
    
    return metrics.get_prometheus_format()


# ============ TRACING ============

@router.get("/traces")
async def get_traces(
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get recent traces.
    """
    traces = tracer.get_recent_traces(limit=limit)
    return {
        "traces": traces,
        "count": len(traces)
    }


@router.get("/traces/{trace_id}", response_model=TraceDetail)
async def get_trace_detail(trace_id: str):
    """
    Get all spans for a specific trace.
    """
    spans = tracer.get_trace(trace_id)
    
    if not spans:
        return {"trace_id": trace_id, "spans": []}
    
    return {
        "trace_id": trace_id,
        "spans": spans
    }


# ============ LOGGING ============

@router.get("/logs")
async def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """
    Get recent log entries.
    
    Filter by level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    Filter by trace_id to see logs for a specific request.
    """
    logs = logger.get_recent_logs(
        limit=limit,
        level=level,
        trace_id=trace_id
    )
    
    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "level": level,
            "trace_id": trace_id
        }
    }


@router.get("/logs/levels")
async def get_log_levels():
    """Get available log levels."""
    return {
        "levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    }


# ============ DASHBOARD DATA ============

@router.get("/dashboard")
async def get_dashboard_data():
    """
    Get aggregated data for telemetry dashboard.
    """
    all_metrics = metrics.collect_all()
    
    # Aggregate request metrics
    requests_by_status = {}
    requests_by_endpoint = {}
    latency_by_endpoint = {}
    
    for m in all_metrics:
        if m["name"] == "goai_requests_total":
            status = m["labels"].get("status", "unknown")
            requests_by_status[status] = requests_by_status.get(status, 0) + m["value"]
            
            endpoint = m["labels"].get("endpoint", "unknown")
            requests_by_endpoint[endpoint] = requests_by_endpoint.get(endpoint, 0) + m["value"]
        
        elif m["name"] == "goai_request_duration_seconds":
            endpoint = m["labels"].get("endpoint", "unknown")
            latency_by_endpoint[endpoint] = {
                "mean": m.get("mean", 0) * 1000,
                "p95": m.get("p95", 0) * 1000,
                "p99": m.get("p99", 0) * 1000
            }
    
    # Get recent traces summary
    recent_traces = tracer.get_recent_traces(limit=10)
    
    # Get error logs
    error_logs = logger.get_recent_logs(limit=10, level="ERROR")
    
    return {
        "requests": {
            "by_status": requests_by_status,
            "by_endpoint": requests_by_endpoint,
            "total": sum(requests_by_status.values())
        },
        "latency": latency_by_endpoint,
        "traces": {
            "recent": recent_traces,
            "stats": tracer.stats()
        },
        "errors": {
            "recent": error_logs,
            "count": len([l for l in logger.get_recent_logs(limit=1000) if l["level"] == "ERROR"])
        }
    }


# ============ HEALTH ============

@router.get("/health")
async def telemetry_health():
    """Check telemetry system health."""
    return {
        "status": "healthy",
        "metrics": "ok",
        "tracing": "ok",
        "logging": "ok"
    }


"""
Performance API - Stats, cache management, and task queue.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from core.cache import cache
from core.performance import (
    get_embedding_service,
    get_llm_service,
    get_task_queue_sync
)

router = APIRouter()


class PerformanceStats(BaseModel):
    """Combined performance statistics."""
    cache: Dict[str, Any]
    embeddings: Dict[str, Any]
    llm: Dict[str, Any]
    tasks: Dict[str, Any]


class TaskSubmission(BaseModel):
    """Task submission request."""
    name: str
    type: str  # "ingest", "embed", "analyze"
    data: Dict[str, Any]


class TaskResponse(BaseModel):
    """Task response."""
    task_id: str
    status: str
    message: str


@router.get("/stats", response_model=PerformanceStats)
async def get_performance_stats():
    """
    Get comprehensive performance statistics.
    
    Returns cache hit rates, API call counts, latencies, and queue status.
    """
    try:
        embedding_service = get_embedding_service()
        llm_service = get_llm_service()
        task_queue = get_task_queue_sync()
        
        return {
            "cache": cache.stats(),
            "embeddings": embedding_service.get_stats(),
            "llm": llm_service.get_stats(),
            "tasks": task_queue.stats()
        }
    except Exception as e:
        return {
            "cache": cache.stats(),
            "embeddings": {"error": str(e)},
            "llm": {"error": str(e)},
            "tasks": {"error": str(e)}
        }


@router.post("/cache/clear/{namespace}")
async def clear_cache(namespace: str):
    """
    Clear cache for a specific namespace.
    
    Namespaces: embedding, llm, query, document, general
    """
    valid_namespaces = ["embedding", "llm", "query", "document", "general", "all"]
    
    if namespace not in valid_namespaces:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid namespace. Valid: {valid_namespaces}"
        )
    
    if namespace == "all":
        # Clear all
        total = 0
        for ns in ["embedding", "llm", "query", "document", "general"]:
            total += cache.clear_namespace(ns)
        return {"cleared": total, "namespace": "all"}
    
    count = cache.clear_namespace(namespace)
    return {"cleared": count, "namespace": namespace}


@router.get("/tasks", response_model=List[Dict[str, Any]])
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50
):
    """List background tasks."""
    from core.performance.task_queue import TaskStatus
    
    task_queue = get_task_queue_sync()
    
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    return task_queue.list_tasks(status=status_filter, limit=limit)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status."""
    task_queue = get_task_queue_sync()
    task = task_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending task."""
    task_queue = get_task_queue_sync()
    
    if task_queue.cancel(task_id):
        return {"cancelled": True, "task_id": task_id}
    
    raise HTTPException(
        status_code=400,
        detail="Cannot cancel task (not pending or not found)"
    )


@router.post("/tasks/cleanup")
async def cleanup_tasks(max_age_hours: int = 24):
    """Remove old completed/failed tasks."""
    task_queue = get_task_queue_sync()
    removed = task_queue.cleanup(max_age_hours)
    return {"removed": removed}


@router.get("/health")
async def performance_health():
    """
    Quick health check for performance systems.
    """
    try:
        cache_ok = cache.stats()["memory"]["size"] >= 0
        
        return {
            "status": "healthy",
            "cache": "ok" if cache_ok else "error",
            "task_queue": "ok"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }


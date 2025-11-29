"""
Async Background Task Queue.
Handles heavy operations without blocking API responses.
"""

import asyncio
import uuid
import time
from typing import Callable, Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Background task."""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0  # 0-100
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self._duration_ms()
        }
    
    def _duration_ms(self) -> Optional[float]:
        """Calculate task duration."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds() * 1000


class TaskQueue:
    """
    Async background task queue.
    
    Features:
    - Priority queue
    - Concurrency control
    - Progress tracking
    - Task cancellation
    - Error handling
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._tasks: Dict[str, Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._lock = asyncio.Lock()
        
        # Stats
        self._completed = 0
        self._failed = 0
    
    async def start(self):
        """Start worker tasks."""
        if self._running:
            return
        
        self._running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        print(f"✅ Task queue started with {self.max_workers} workers")
    
    async def stop(self):
        """Stop all workers."""
        self._running = False
        
        # Cancel pending tasks
        while not self._queue.empty():
            try:
                task_id = self._queue.get_nowait()
                if task_id in self._tasks:
                    self._tasks[task_id].status = TaskStatus.CANCELLED
            except asyncio.QueueEmpty:
                break
        
        # Wait for workers
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
    
    async def _worker(self, name: str):
        """Worker coroutine."""
        while self._running:
            try:
                # Wait for task
                task_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                
                if task_id not in self._tasks:
                    continue
                
                task = self._tasks[task_id]
                
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # Execute task
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                
                try:
                    # Check if async
                    if asyncio.iscoroutinefunction(task.func):
                        result = await task.func(*task.args, **task.kwargs)
                    else:
                        # Run sync function in executor
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            None,
                            lambda: task.func(*task.args, **task.kwargs)
                        )
                    
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.progress = 100
                    self._completed += 1
                    
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    self._failed += 1
                    print(f"❌ Task {task.name} failed: {e}")
                
                finally:
                    task.completed_at = datetime.now()
                    self._queue.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    
    async def submit(
        self,
        func: Callable,
        *args,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Submit task to queue.
        
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        async with self._lock:
            self._tasks[task_id] = task
        
        await self._queue.put(task_id)
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_result(self, task_id: str) -> Any:
        """Get task result."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.COMPLETED:
            return task.result
        return None
    
    async def wait(self, task_id: str, timeout: float = 60.0) -> Optional[Any]:
        """Wait for task to complete."""
        start = time.time()
        
        while time.time() - start < timeout:
            task = self._tasks.get(task_id)
            if not task:
                return None
            
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task.result
            
            await asyncio.sleep(0.1)
        
        return None
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        return False
    
    def update_progress(self, task_id: str, progress: float):
        """Update task progress."""
        task = self._tasks.get(task_id)
        if task:
            task.progress = min(100, max(0, progress))
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List tasks."""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by created_at desc
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return [t.to_dict() for t in tasks[:limit]]
    
    def cleanup(self, max_age_hours: int = 24):
        """Remove old completed/failed tasks."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for task_id, task in self._tasks.items():
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                if task.completed_at and task.completed_at.timestamp() < cutoff:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
        
        return len(to_remove)
    
    def stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        status_counts = {}
        for task in self._tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_tasks": len(self._tasks),
            "queue_size": self._queue.qsize(),
            "workers": len(self._workers),
            "running": self._running,
            "completed": self._completed,
            "failed": self._failed,
            "by_status": status_counts
        }


# Singleton instance
_task_queue: Optional[TaskQueue] = None


async def get_task_queue() -> TaskQueue:
    """Get task queue singleton."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
        await _task_queue.start()
    return _task_queue


def get_task_queue_sync() -> TaskQueue:
    """Get task queue (must be started separately)."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


"""
Agent Observability Module

Provides comprehensive monitoring, tracing, and analytics for AI agent operations.

Features:
- Execution traces with timing
- Tool usage statistics
- Token consumption tracking
- Error monitoring
- Performance metrics
- Cost estimation
- Real-time event streaming

Usage:
    from modules.agents.observability import agent_observer, TraceEvent
    
    # Start a trace
    trace_id = agent_observer.start_trace(agent_id="agent-1", task="Research AI")
    
    # Log events
    agent_observer.log_event(trace_id, "tool_call", {"tool": "web_search"})
    
    # End trace
    agent_observer.end_trace(trace_id, result="Success")
    
    # Get dashboard data
    dashboard = agent_observer.get_dashboard_data()
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid
import asyncio
import json


class EventType(str, Enum):
    """Types of agent events."""
    TRACE_START = "trace_start"
    TRACE_END = "trace_end"
    PLANNING = "planning"
    PLAN_CREATED = "plan_created"
    STEP_START = "step_start"
    STEP_END = "step_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    REPLAN = "replan"
    ERROR = "error"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECEIVED = "approval_received"
    CUSTOM = "custom"


class TraceStatus(str, Enum):
    """Status of a trace."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TraceEvent:
    """A single event in an agent trace."""
    id: str
    trace_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "duration_ms": self.duration_ms
        }


@dataclass
class AgentTrace:
    """Complete trace of an agent execution."""
    id: str
    agent_id: str
    task: str
    started_at: datetime
    status: TraceStatus = TraceStatus.RUNNING
    ended_at: Optional[datetime] = None
    events: List[TraceEvent] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Metrics
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    replans: int = 0
    steps_completed: int = 0
    estimated_cost: float = 0.0
    
    # Metadata
    model: Optional[str] = None
    template: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration_ms(self) -> float:
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return (datetime.now() - self.started_at).total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task": self.task[:100] + "..." if len(self.task) > 100 else self.task,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status.value,
            "duration_ms": self.duration_ms(),
            "result": self.result[:200] + "..." if self.result and len(self.result) > 200 else self.result,
            "error": self.error,
            "metrics": {
                "total_tokens": self.total_tokens,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "tool_calls": self.tool_calls,
                "llm_calls": self.llm_calls,
                "replans": self.replans,
                "steps_completed": self.steps_completed,
                "estimated_cost": round(self.estimated_cost, 6)
            },
            "model": self.model,
            "template": self.template,
            "event_count": len(self.events)
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full trace including all events."""
        result = self.to_dict()
        result["events"] = [e.to_dict() for e in self.events]
        result["metadata"] = self.metadata
        return result


class AgentObserver:
    """
    Central observer for agent operations.
    
    Tracks all agent executions, providing:
    - Real-time monitoring
    - Historical analytics
    - Performance insights
    - Cost tracking
    """
    
    # Token pricing (per 1K tokens) - approximate
    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "llama3": {"input": 0.0, "output": 0.0},  # Local
        "ollama": {"input": 0.0, "output": 0.0}   # Local
    }
    
    def __init__(self, max_traces: int = 1000):
        self.traces: Dict[str, AgentTrace] = {}
        self.max_traces = max_traces
        
        # Aggregated metrics
        self._total_executions = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._tool_usage: Dict[str, int] = defaultdict(int)
        self._model_usage: Dict[str, int] = defaultdict(int)
        self._template_usage: Dict[str, int] = defaultdict(int)
        self._hourly_stats: Dict[str, Dict[str, Any]] = {}
        self._errors: List[Dict[str, Any]] = []
        
        # Event listeners for real-time streaming
        self._listeners: List[asyncio.Queue] = []
    
    def start_trace(
        self,
        agent_id: str,
        task: str,
        model: str = None,
        template: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Start a new agent trace."""
        trace_id = str(uuid.uuid4())
        
        trace = AgentTrace(
            id=trace_id,
            agent_id=agent_id,
            task=task,
            started_at=datetime.now(),
            model=model,
            template=template,
            metadata=metadata or {}
        )
        
        self.traces[trace_id] = trace
        self._total_executions += 1
        
        if model:
            self._model_usage[model] += 1
        if template:
            self._template_usage[template] += 1
        
        # Log start event
        self._add_event(trace_id, EventType.TRACE_START, {
            "agent_id": agent_id,
            "task": task,
            "model": model,
            "template": template
        })
        
        # Cleanup old traces if needed
        self._cleanup_old_traces()
        
        return trace_id
    
    def end_trace(
        self,
        trace_id: str,
        result: str = None,
        error: str = None
    ):
        """End an agent trace."""
        trace = self.traces.get(trace_id)
        if not trace:
            return
        
        trace.ended_at = datetime.now()
        trace.result = result
        trace.error = error
        trace.status = TraceStatus.FAILED if error else TraceStatus.COMPLETED
        
        # Update hourly stats
        self._update_hourly_stats(trace)
        
        # Log end event
        self._add_event(trace_id, EventType.TRACE_END, {
            "status": trace.status.value,
            "duration_ms": trace.duration_ms(),
            "error": error
        })
        
        # Track errors
        if error:
            self._errors.append({
                "trace_id": trace_id,
                "timestamp": datetime.now().isoformat(),
                "error": error,
                "agent_id": trace.agent_id,
                "task": trace.task[:100]
            })
            # Keep only last 100 errors
            if len(self._errors) > 100:
                self._errors = self._errors[-100:]
    
    def log_event(
        self,
        trace_id: str,
        event_type: EventType,
        data: Dict[str, Any] = None,
        duration_ms: float = None
    ):
        """Log an event to a trace."""
        self._add_event(trace_id, event_type, data or {}, duration_ms)
        
        # Update trace metrics based on event type
        trace = self.traces.get(trace_id)
        if not trace:
            return
        
        if event_type == EventType.TOOL_CALL:
            trace.tool_calls += 1
            tool_name = data.get("tool", "unknown")
            self._tool_usage[tool_name] += 1
            
        elif event_type == EventType.LLM_RESPONSE:
            trace.llm_calls += 1
            tokens = data.get("tokens", {})
            trace.prompt_tokens += tokens.get("prompt", 0)
            trace.completion_tokens += tokens.get("completion", 0)
            trace.total_tokens += tokens.get("total", 0)
            self._total_tokens += tokens.get("total", 0)
            
            # Calculate cost
            model = trace.model or "gpt-4o-mini"
            cost = self._calculate_cost(
                model,
                tokens.get("prompt", 0),
                tokens.get("completion", 0)
            )
            trace.estimated_cost += cost
            self._total_cost += cost
            
        elif event_type == EventType.REPLAN:
            trace.replans += 1
            
        elif event_type == EventType.STEP_END:
            trace.steps_completed += 1
    
    def _add_event(
        self,
        trace_id: str,
        event_type: EventType,
        data: Dict[str, Any],
        duration_ms: float = None
    ):
        """Add event to trace and notify listeners."""
        trace = self.traces.get(trace_id)
        if not trace:
            return
        
        event = TraceEvent(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            duration_ms=duration_ms
        )
        
        trace.events.append(event)
        
        # Notify real-time listeners
        event_dict = event.to_dict()
        for queue in self._listeners:
            try:
                queue.put_nowait(event_dict)
            except asyncio.QueueFull:
                pass
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost for token usage."""
        # Find matching pricing
        pricing = None
        for model_key, prices in self.PRICING.items():
            if model_key in model.lower():
                pricing = prices
                break
        
        if not pricing:
            pricing = self.PRICING.get("gpt-4o-mini", {"input": 0, "output": 0})
        
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def _update_hourly_stats(self, trace: AgentTrace):
        """Update hourly statistics."""
        hour_key = trace.started_at.strftime("%Y-%m-%d-%H")
        
        if hour_key not in self._hourly_stats:
            self._hourly_stats[hour_key] = {
                "executions": 0,
                "completed": 0,
                "failed": 0,
                "tokens": 0,
                "cost": 0.0,
                "avg_duration_ms": 0
            }
        
        stats = self._hourly_stats[hour_key]
        stats["executions"] += 1
        stats["tokens"] += trace.total_tokens
        stats["cost"] += trace.estimated_cost
        
        if trace.status == TraceStatus.COMPLETED:
            stats["completed"] += 1
        elif trace.status == TraceStatus.FAILED:
            stats["failed"] += 1
        
        # Update average duration
        total = stats["executions"]
        stats["avg_duration_ms"] = (
            (stats["avg_duration_ms"] * (total - 1) + trace.duration_ms()) / total
        )
        
        # Keep only last 168 hours (1 week)
        if len(self._hourly_stats) > 168:
            oldest = min(self._hourly_stats.keys())
            del self._hourly_stats[oldest]
    
    def _cleanup_old_traces(self):
        """Remove old traces if over limit."""
        if len(self.traces) <= self.max_traces:
            return
        
        # Sort by started_at and remove oldest completed traces
        sorted_traces = sorted(
            self.traces.values(),
            key=lambda t: t.started_at
        )
        
        to_remove = len(self.traces) - self.max_traces
        removed = 0
        
        for trace in sorted_traces:
            if trace.status != TraceStatus.RUNNING and removed < to_remove:
                del self.traces[trace.id]
                removed += 1
    
    # ============================================
    # Query Methods
    # ============================================
    
    def get_trace(self, trace_id: str) -> Optional[AgentTrace]:
        """Get a specific trace."""
        return self.traces.get(trace_id)
    
    def list_traces(
        self,
        status: TraceStatus = None,
        agent_id: str = None,
        model: str = None,
        template: str = None,
        since: datetime = None,
        limit: int = 50
    ) -> List[AgentTrace]:
        """List traces with optional filters."""
        results = []
        
        for trace in self.traces.values():
            if status and trace.status != status:
                continue
            if agent_id and trace.agent_id != agent_id:
                continue
            if model and trace.model != model:
                continue
            if template and trace.template != template:
                continue
            if since and trace.started_at < since:
                continue
            results.append(trace)
        
        # Sort by started_at descending
        results.sort(key=lambda t: t.started_at, reverse=True)
        
        return results[:limit]
    
    def get_active_traces(self) -> List[AgentTrace]:
        """Get currently running traces."""
        return [t for t in self.traces.values() if t.status == TraceStatus.RUNNING]
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self._errors[-limit:]
    
    # ============================================
    # Analytics Methods
    # ============================================
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)
        
        # Recent traces
        recent_traces = self.list_traces(since=last_24h, limit=100)
        last_hour_traces = [t for t in recent_traces if t.started_at >= last_hour]
        
        # Calculate rates
        success_count = len([t for t in recent_traces if t.status == TraceStatus.COMPLETED])
        error_count = len([t for t in recent_traces if t.status == TraceStatus.FAILED])
        total_recent = len(recent_traces) or 1
        
        return {
            "summary": {
                "total_executions": self._total_executions,
                "total_tokens": self._total_tokens,
                "total_cost": round(self._total_cost, 4),
                "active_traces": len(self.get_active_traces()),
                "traces_last_24h": len(recent_traces),
                "traces_last_hour": len(last_hour_traces)
            },
            "rates": {
                "success_rate_24h": round(success_count / total_recent * 100, 1),
                "error_rate_24h": round(error_count / total_recent * 100, 1),
                "avg_duration_ms": round(
                    sum(t.duration_ms() for t in recent_traces) / total_recent, 0
                ) if recent_traces else 0
            },
            "usage": {
                "by_model": dict(self._model_usage),
                "by_template": dict(self._template_usage),
                "by_tool": dict(self._tool_usage)
            },
            "recent_traces": [t.to_dict() for t in recent_traces[:10]],
            "active_traces": [t.to_dict() for t in self.get_active_traces()],
            "recent_errors": self.get_recent_errors(5),
            "hourly_stats": self._get_hourly_stats_list()
        }
    
    def _get_hourly_stats_list(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly stats as a list for charting."""
        result = []
        now = datetime.now()
        
        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            stats = self._hourly_stats.get(hour_key, {
                "executions": 0,
                "completed": 0,
                "failed": 0,
                "tokens": 0,
                "cost": 0.0
            })
            result.append({
                "hour": hour_key,
                "display": hour.strftime("%H:00"),
                **stats
            })
        
        return list(reversed(result))
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """Get detailed tool usage statistics."""
        return {
            "total_calls": sum(self._tool_usage.values()),
            "by_tool": dict(self._tool_usage),
            "top_tools": sorted(
                self._tool_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model usage statistics."""
        return {
            "total_calls": sum(self._model_usage.values()),
            "by_model": dict(self._model_usage)
        }
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get cost breakdown by model."""
        cost_by_model = defaultdict(float)
        
        for trace in self.traces.values():
            model = trace.model or "unknown"
            cost_by_model[model] += trace.estimated_cost
        
        return {
            "total_cost": round(self._total_cost, 4),
            "by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
            "total_tokens": self._total_tokens
        }
    
    # ============================================
    # Real-time Streaming
    # ============================================
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to real-time events."""
        queue = asyncio.Queue(maxsize=100)
        self._listeners.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from real-time events."""
        if queue in self._listeners:
            self._listeners.remove(queue)
    
    async def stream_events(self, trace_id: str = None):
        """Stream events in real-time."""
        queue = self.subscribe()
        try:
            while True:
                event = await queue.get()
                if trace_id and event.get("trace_id") != trace_id:
                    continue
                yield event
        finally:
            self.unsubscribe(queue)


# Global instance
agent_observer = AgentObserver()


# ============================================
# Convenience Decorators
# ============================================

def traced(agent_id: str = "default", model: str = None, template: str = None):
    """Decorator to automatically trace function execution."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            task = kwargs.get("task", str(args[0]) if args else "unknown")
            trace_id = agent_observer.start_trace(
                agent_id=agent_id,
                task=task,
                model=model,
                template=template
            )
            
            try:
                result = await func(*args, **kwargs)
                agent_observer.end_trace(trace_id, result=str(result)[:500])
                return result
            except Exception as e:
                agent_observer.end_trace(trace_id, error=str(e))
                raise
        
        return wrapper
    return decorator


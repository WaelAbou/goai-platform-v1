"""
Metrics Collection System.
Prometheus-compatible metrics with in-memory storage.
"""

import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabel:
    """Metric labels for dimensional data."""
    name: str
    value: str


@dataclass
class MetricValue:
    """Single metric value with labels."""
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    Monotonically increasing counter.
    Use for: requests, errors, tokens used, etc.
    """
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1, **labels):
        """Increment counter."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value
    
    def get(self, **labels) -> float:
        """Get current value."""
        key = self._make_key(labels)
        return self._values.get(key, 0)
    
    def _make_key(self, labels: dict) -> tuple:
        """Create hashable key from labels."""
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[Dict[str, Any]]:
        """Collect all metric values."""
        result = []
        with self._lock:
            for key, value in self._values.items():
                result.append({
                    "name": self.name,
                    "type": "counter",
                    "value": value,
                    "labels": dict(key)
                })
        return result


class Gauge:
    """
    Value that can go up and down.
    Use for: active connections, queue size, memory usage, etc.
    """
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def set(self, value: float, **labels):
        """Set gauge value."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1, **labels):
        """Increment gauge."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def dec(self, value: float = 1, **labels):
        """Decrement gauge."""
        self.inc(-value, **labels)
    
    def get(self, **labels) -> float:
        """Get current value."""
        key = self._make_key(labels)
        return self._values.get(key, 0)
    
    def _make_key(self, labels: dict) -> tuple:
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[Dict[str, Any]]:
        result = []
        with self._lock:
            for key, value in self._values.items():
                result.append({
                    "name": self.name,
                    "type": "gauge",
                    "value": value,
                    "labels": dict(key)
                })
        return result


class Histogram:
    """
    Observe value distributions.
    Use for: request latency, response sizes, etc.
    """
    
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None,
        buckets: List[float] = None
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._observations: Dict[tuple, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def observe(self, value: float, **labels):
        """Record an observation."""
        key = self._make_key(labels)
        with self._lock:
            self._observations[key].append(value)
            # Keep only last 10000 observations per label set
            if len(self._observations[key]) > 10000:
                self._observations[key] = self._observations[key][-10000:]
    
    def get_stats(self, **labels) -> Dict[str, float]:
        """Get statistics for observations."""
        key = self._make_key(labels)
        observations = self._observations.get(key, [])
        
        if not observations:
            return {"count": 0}
        
        return {
            "count": len(observations),
            "sum": sum(observations),
            "min": min(observations),
            "max": max(observations),
            "mean": statistics.mean(observations),
            "median": statistics.median(observations),
            "p95": self._percentile(observations, 95),
            "p99": self._percentile(observations, 99)
        }
    
    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])
    
    def _make_key(self, labels: dict) -> tuple:
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[Dict[str, Any]]:
        result = []
        with self._lock:
            for key, observations in self._observations.items():
                if observations:
                    stats = self.get_stats(**dict(key))
                    result.append({
                        "name": self.name,
                        "type": "histogram",
                        "labels": dict(key),
                        **stats
                    })
        return result


class MetricsRegistry:
    """
    Central registry for all metrics.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def counter(self, name: str, description: str = "", labels: List[str] = None) -> Counter:
        """Create or get a counter."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name, description, labels)
            return self._metrics[name]
    
    def gauge(self, name: str, description: str = "", labels: List[str] = None) -> Gauge:
        """Create or get a gauge."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name, description, labels)
            return self._metrics[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None,
        buckets: List[float] = None
    ) -> Histogram:
        """Create or get a histogram."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Histogram(name, description, labels, buckets)
            return self._metrics[name]
    
    def collect_all(self) -> List[Dict[str, Any]]:
        """Collect all metrics."""
        result = []
        with self._lock:
            for metric in self._metrics.values():
                result.extend(metric.collect())
        return result
    
    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        metrics = self.collect_all()
        
        for m in metrics:
            name = m["name"].replace(".", "_")
            labels = m.get("labels", {})
            
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                metric_name = f"{name}{{{label_str}}}"
            else:
                metric_name = name
            
            if m["type"] == "histogram":
                lines.append(f"{name}_count{{{label_str if labels else ''}}} {m['count']}")
                lines.append(f"{name}_sum{{{label_str if labels else ''}}} {m.get('sum', 0)}")
            else:
                lines.append(f"{metric_name} {m['value']}")
        
        return "\n".join(lines)


# Global registry
metrics = MetricsRegistry()

# Pre-defined metrics
request_counter = metrics.counter(
    "goai_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

request_latency = metrics.histogram(
    "goai_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

llm_requests = metrics.counter(
    "goai_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"]
)

llm_tokens = metrics.counter(
    "goai_llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model", "type"]
)

llm_latency = metrics.histogram(
    "goai_llm_latency_seconds",
    "LLM request latency",
    ["provider", "model"]
)

embedding_requests = metrics.counter(
    "goai_embedding_requests_total",
    "Total embedding requests",
    ["model", "cached"]
)

cache_operations = metrics.counter(
    "goai_cache_operations_total",
    "Cache operations",
    ["namespace", "operation", "result"]
)

active_connections = metrics.gauge(
    "goai_active_connections",
    "Active HTTP connections"
)

queue_size = metrics.gauge(
    "goai_task_queue_size",
    "Background task queue size"
)

documents_total = metrics.gauge(
    "goai_documents_total",
    "Total documents in system"
)


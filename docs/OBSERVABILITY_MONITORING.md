# GoAI Sovereign Platform — Observability & Monitoring Standard

## Enterprise Monitoring Framework

> This document defines the **complete observability stack** using Prometheus, Grafana, and structured logging. All metrics and logs follow standardized formats for consistency across deployments.

---

## Observability Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          OBSERVABILITY ARCHITECTURE                                  │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                              VISUALIZATION                                   │   │
│   │                                                                              │   │
│   │   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐            │   │
│   │   │    Grafana    │     │   Alerting    │     │   Reporting   │            │   │
│   │   │  Dashboards   │     │   Dashboard   │     │   (Weekly)    │            │   │
│   │   └───────────────┘     └───────────────┘     └───────────────┘            │   │
│   │                                                                              │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      ▲                                               │
│                                      │                                               │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                              STORAGE                                         │   │
│   │                                                                              │   │
│   │   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐            │   │
│   │   │  Prometheus   │     │    Loki       │     │Elasticsearch  │            │   │
│   │   │   (Metrics)   │     │   (Logs)      │     │(Search/Audit) │            │   │
│   │   │   30 days     │     │   90 days     │     │   365 days    │            │   │
│   │   └───────────────┘     └───────────────┘     └───────────────┘            │   │
│   │                                                                              │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      ▲                                               │
│                                      │                                               │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                              COLLECTION                                      │   │
│   │                                                                              │   │
│   │   ┌─────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                         Metrics Exporters                            │   │   │
│   │   │                                                                      │   │   │
│   │   │   Gateway │ RAG │ Agents │ vLLM │ PostgreSQL │ Redis │ DCGM (GPU)   │   │   │
│   │   │                                                                      │   │   │
│   │   └─────────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                              │   │
│   │   ┌─────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                         Log Shippers                                 │   │   │
│   │   │                                                                      │   │   │
│   │   │   Promtail │ Fluentd │ Application Loggers                          │   │   │
│   │   │                                                                      │   │   │
│   │   └─────────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                              │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      ▲                                               │
│                                      │                                               │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                              SOURCES                                         │   │
│   │                                                                              │   │
│   │   Gateway │ RAG Service │ Agent Service │ vLLM │ PostgreSQL │ GPU Nodes    │   │
│   │                                                                              │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Metrics Standard

### 1.1 Metric Categories

| Category | Prefix | Description | Scrape Interval |
|----------|--------|-------------|-----------------|
| HTTP | `http_` | API request metrics | 15s |
| LLM | `llm_` | Language model metrics | 15s |
| RAG | `rag_` | Retrieval metrics | 15s |
| Agent | `agent_` | Agent execution metrics | 15s |
| Vector | `vector_` | Vector store metrics | 30s |
| Cache | `cache_` | Caching metrics | 15s |
| GPU | `dcgm_` | GPU metrics (DCGM) | 5s |
| System | `node_` | System metrics | 15s |
| Database | `pg_` | PostgreSQL metrics | 30s |

### 1.2 HTTP Metrics

```yaml
# Metric: http_requests_total
# Type: Counter
# Description: Total HTTP requests
http_requests_total:
  labels:
    - method      # GET, POST, PUT, DELETE
    - path        # /api/v1/rag/query
    - status      # 200, 400, 500
    - tenant_id   # Tenant identifier
  example: |
    http_requests_total{method="POST",path="/api/v1/rag/query",status="200",tenant_id="acme"} 1523

# Metric: http_request_duration_seconds
# Type: Histogram
# Description: Request latency distribution
http_request_duration_seconds:
  labels:
    - method
    - path
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30]
  example: |
    http_request_duration_seconds_bucket{method="POST",path="/api/v1/rag/query",le="1"} 1234
    http_request_duration_seconds_sum{method="POST",path="/api/v1/rag/query"} 567.89
    http_request_duration_seconds_count{method="POST",path="/api/v1/rag/query"} 1523

# Metric: http_requests_in_progress
# Type: Gauge
# Description: Currently active requests
http_requests_in_progress:
  labels:
    - method
  example: |
    http_requests_in_progress{method="POST"} 15
```

### 1.3 LLM Metrics

```yaml
# Metric: llm_requests_total
# Type: Counter
# Description: Total LLM inference requests
llm_requests_total:
  labels:
    - model       # llama-70b, llama-8b
    - status      # success, error, timeout
    - tenant_id
  example: |
    llm_requests_total{model="llama-70b",status="success",tenant_id="acme"} 5000

# Metric: llm_tokens_total
# Type: Counter
# Description: Total tokens processed
llm_tokens_total:
  labels:
    - model
    - direction   # input, output
    - tenant_id
  example: |
    llm_tokens_total{model="llama-70b",direction="input",tenant_id="acme"} 2500000
    llm_tokens_total{model="llama-70b",direction="output",tenant_id="acme"} 750000

# Metric: llm_request_duration_seconds
# Type: Histogram
# Description: LLM inference latency
llm_request_duration_seconds:
  labels:
    - model
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]

# Metric: llm_ttft_seconds
# Type: Histogram
# Description: Time to First Token (streaming)
llm_ttft_seconds:
  labels:
    - model
  buckets: [0.05, 0.1, 0.2, 0.5, 1, 2, 5]

# Metric: llm_queue_size
# Type: Gauge
# Description: Requests waiting in queue
llm_queue_size:
  labels:
    - model
  example: |
    llm_queue_size{model="llama-70b"} 5

# Metric: llm_batch_size
# Type: Histogram
# Description: Batch sizes for inference
llm_batch_size:
  labels:
    - model
  buckets: [1, 2, 4, 8, 16, 32, 64]
```

### 1.4 RAG Metrics

```yaml
# Metric: rag_queries_total
# Type: Counter
# Description: Total RAG queries
rag_queries_total:
  labels:
    - namespace   # global, policies
    - status      # success, no_results, error
    - tenant_id
  example: |
    rag_queries_total{namespace="policies",status="success",tenant_id="acme"} 3000

# Metric: rag_retrieval_duration_seconds
# Type: Histogram
# Description: Time to retrieve documents
rag_retrieval_duration_seconds:
  labels:
    - namespace
  buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1]
  example: |
    rag_retrieval_duration_seconds_bucket{namespace="global",le="0.1"} 2500

# Metric: rag_sources_retrieved
# Type: Histogram
# Description: Number of sources returned per query
rag_sources_retrieved:
  labels:
    - namespace
  buckets: [0, 1, 2, 3, 5, 10, 20]

# Metric: rag_context_tokens
# Type: Histogram
# Description: Tokens in retrieved context
rag_context_tokens:
  labels:
    - namespace
  buckets: [100, 500, 1000, 2000, 4000, 8000]

# Metric: rag_documents_total
# Type: Gauge
# Description: Total documents in vector store
rag_documents_total:
  labels:
    - namespace
  example: |
    rag_documents_total{namespace="global"} 50000

# Metric: rag_chunks_total
# Type: Gauge
# Description: Total chunks in vector store
rag_chunks_total:
  labels:
    - namespace
```

### 1.5 Agent Metrics

```yaml
# Metric: agent_executions_total
# Type: Counter
# Description: Total agent executions
agent_executions_total:
  labels:
    - agent_type   # single, multi-agent
    - pattern      # sequential, parallel, hierarchical
    - status       # success, error, timeout
    - tenant_id
  example: |
    agent_executions_total{agent_type="multi-agent",pattern="hierarchical",status="success"} 500

# Metric: agent_execution_duration_seconds
# Type: Histogram
# Description: Agent execution time
agent_execution_duration_seconds:
  labels:
    - agent_type
    - pattern
  buckets: [1, 5, 10, 30, 60, 120, 300, 600]

# Metric: agent_tool_calls_total
# Type: Counter
# Description: Tool invocations by agents
agent_tool_calls_total:
  labels:
    - tool         # web_search, calculator, etc.
    - status       # success, error, blocked
    - tenant_id
  example: |
    agent_tool_calls_total{tool="web_search",status="success"} 1200

# Metric: agent_tool_duration_seconds
# Type: Histogram
# Description: Tool execution time
agent_tool_duration_seconds:
  labels:
    - tool
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30]

# Metric: agent_iterations_total
# Type: Histogram
# Description: Number of iterations per agent run
agent_iterations_total:
  labels:
    - agent_type
  buckets: [1, 2, 3, 5, 10, 15, 20]
```

### 1.6 GPU Metrics (DCGM)

```yaml
# Standard DCGM metrics (auto-collected)
gpu_metrics:
  - name: DCGM_FI_DEV_GPU_UTIL
    description: GPU utilization percentage
    unit: percent
    
  - name: DCGM_FI_DEV_MEM_COPY_UTIL
    description: Memory copy utilization
    unit: percent
    
  - name: DCGM_FI_DEV_FB_FREE
    description: Free framebuffer memory
    unit: megabytes
    
  - name: DCGM_FI_DEV_FB_USED
    description: Used framebuffer memory
    unit: megabytes
    
  - name: DCGM_FI_DEV_GPU_TEMP
    description: GPU temperature
    unit: celsius
    
  - name: DCGM_FI_DEV_POWER_USAGE
    description: Power consumption
    unit: watts
    
  - name: DCGM_FI_DEV_SM_CLOCK
    description: SM clock frequency
    unit: megahertz
    
  - name: DCGM_FI_DEV_ECC_DBE_AGG_TOTAL
    description: Double-bit ECC errors (aggregate)
    unit: count

# Custom derived metrics
custom_gpu_metrics:
  - name: gpu_memory_utilization_percent
    expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100
    
  - name: gpu_power_efficiency
    expr: llm_tokens_total / DCGM_FI_DEV_POWER_USAGE
```

### 1.7 Cache Metrics

```yaml
# Metric: cache_hits_total
# Type: Counter
cache_hits_total:
  labels:
    - cache_type   # embedding, llm, session
  example: |
    cache_hits_total{cache_type="embedding"} 15000

# Metric: cache_misses_total
# Type: Counter
cache_misses_total:
  labels:
    - cache_type

# Metric: cache_size_bytes
# Type: Gauge
cache_size_bytes:
  labels:
    - cache_type

# Derived: Cache hit rate
# expr: cache_hits_total / (cache_hits_total + cache_misses_total)
```

### 1.8 Embedding Metrics

```yaml
# Metric: embedding_requests_total
# Type: Counter
embedding_requests_total:
  labels:
    - model        # bge-large
    - status

# Metric: embedding_duration_seconds
# Type: Histogram
embedding_duration_seconds:
  labels:
    - model
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1]

# Metric: embedding_batch_size
# Type: Histogram
embedding_batch_size:
  buckets: [1, 4, 8, 16, 32, 64, 128]

# Metric: embedding_cost_estimate
# Type: Counter
# Description: Estimated cost in tokens
embedding_cost_estimate:
  labels:
    - model
    - tenant_id
```

---

## 2. Logs Standard

### 2.1 Log Categories

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              LOG CATEGORIES                                          │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  AUDIT_LOG                                                                   │   │
│   │  Purpose: Compliance and security auditing                                  │   │
│   │  Retention: 7 years                                                         │   │
│   │  Events: Auth, data access, admin actions                                   │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  RETRIEVAL_LOG                                                               │   │
│   │  Purpose: RAG retrieval auditing                                            │   │
│   │  Retention: 1 year                                                          │   │
│   │  Events: Vector searches, document access                                   │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  ACTION_LOG                                                                  │   │
│   │  Purpose: Agent and tool execution tracking                                 │   │
│   │  Retention: 90 days                                                         │   │
│   │  Events: Tool calls, agent decisions                                        │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  MODEL_LOG                                                                   │   │
│   │  Purpose: LLM inference monitoring                                          │   │
│   │  Retention: 30 days                                                         │   │
│   │  Events: Inference requests, guardrail triggers                             │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  APPLICATION_LOG                                                             │   │
│   │  Purpose: General application logging                                       │   │
│   │  Retention: 30 days                                                         │   │
│   │  Events: Errors, warnings, debug (level-based)                             │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Log Format Standard

All logs MUST follow this JSON format:

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "goai.rag",
  "message": "RAG query completed",
  "request_id": "req-abc123",
  "trace_id": "trace-xyz789",
  "span_id": "span-def456",
  "service": "rag-service",
  "version": "1.0.0",
  "environment": "production",
  "tenant_id": "acme",
  "user_id": "user-123",
  "attributes": {
    "query_length": 150,
    "sources_found": 5,
    "duration_ms": 245
  }
}
```

### 2.3 Audit Log Schema

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "event_type": "data.document.read",
  "event_category": "data",
  "severity": "info",
  
  "actor": {
    "user_id": "user-123",
    "username": "john.doe@acme.com",
    "role": "power_user",
    "tenant_id": "acme",
    "ip_address": "10.0.0.50",
    "user_agent": "GoAI-Console/1.0"
  },
  
  "action": {
    "type": "read",
    "resource_type": "document",
    "resource_id": "doc-456",
    "method": "GET",
    "path": "/api/v1/rag/query"
  },
  
  "request": {
    "id": "req-abc123",
    "query_hash": "sha256:...",
    "parameters": {
      "top_k": 5,
      "namespace": "policies"
    }
  },
  
  "result": {
    "status": "success",
    "documents_accessed": ["doc-456", "doc-789"],
    "response_time_ms": 245
  },
  
  "compliance": {
    "data_classification": "internal",
    "pii_accessed": false,
    "gdpr_relevant": true
  },
  
  "integrity": {
    "hash": "sha256:...",
    "previous_hash": "sha256:..."
  }
}
```

### 2.4 Retrieval Log Schema

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "log_type": "retrieval",
  "request_id": "req-abc123",
  
  "query": {
    "text": "What is the refund policy?",
    "embedding_hash": "sha256:...",
    "namespace": "policies"
  },
  
  "user": {
    "id": "user-123",
    "tenant_id": "acme"
  },
  
  "retrieval": {
    "algorithm": "faiss_ivf",
    "top_k_requested": 5,
    "top_k_returned": 5,
    "latency_ms": 45,
    "results": [
      {
        "document_id": "doc-456",
        "chunk_id": "chunk-789",
        "score": 0.92,
        "accessed": true
      }
    ]
  },
  
  "acl_filtering": {
    "documents_filtered": 2,
    "filter_reasons": ["acl_denied"]
  },
  
  "generation": {
    "model": "llama-70b",
    "context_tokens": 2500,
    "documents_used": ["doc-456", "doc-123"]
  }
}
```

### 2.5 Action Log Schema

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "log_type": "action",
  "request_id": "req-abc123",
  
  "agent": {
    "type": "multi-agent",
    "pattern": "hierarchical",
    "team": "research"
  },
  
  "action": {
    "iteration": 3,
    "agent_role": "researcher",
    "type": "tool_call",
    "tool": "web_search",
    "input": {
      "query": "latest AI news"
    },
    "output": {
      "status": "success",
      "results_count": 5
    },
    "duration_ms": 1500
  },
  
  "decision": {
    "reasoning": "Need to gather more information",
    "next_action": "analyze_results"
  },
  
  "user": {
    "id": "user-123",
    "tenant_id": "acme"
  }
}
```

### 2.6 Model Log Schema

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "log_type": "model",
  "request_id": "req-abc123",
  
  "inference": {
    "model": "llama-70b",
    "provider": "vllm",
    "endpoint": "http://vllm-70b:8001",
    "request_type": "chat",
    "streaming": true
  },
  
  "tokens": {
    "input": 2500,
    "output": 450,
    "total": 2950
  },
  
  "timing": {
    "queue_time_ms": 50,
    "ttft_ms": 200,
    "total_time_ms": 3500,
    "tokens_per_second": 128.5
  },
  
  "guardrails": {
    "input_checks": {
      "injection_detected": false,
      "pii_detected": false,
      "topic_filtered": false
    },
    "output_checks": {
      "pii_masked": false,
      "harmful_blocked": false,
      "confidence_flagged": false
    }
  },
  
  "user": {
    "id": "user-123",
    "tenant_id": "acme"
  }
}
```

---

## 3. Grafana Dashboards

### 3.1 Dashboard Hierarchy

```
Dashboards/
├── Overview/
│   └── System Overview          # High-level system health
├── LLM/
│   ├── LLM Performance         # Latency, throughput, errors
│   ├── Token Usage             # Token consumption by tenant
│   └── Model Comparison        # Compare model performance
├── RAG/
│   ├── RAG Performance         # Retrieval metrics
│   ├── Document Analytics      # Document access patterns
│   └── Search Quality          # Search relevance metrics
├── Agents/
│   ├── Agent Execution         # Agent run statistics
│   └── Tool Usage              # Tool call analytics
├── Infrastructure/
│   ├── GPU Metrics             # GPU utilization, memory, temp
│   ├── System Resources        # CPU, memory, disk
│   └── Database Performance    # PostgreSQL metrics
├── Business/
│   ├── Usage by Tenant         # Multi-tenant usage
│   └── Cost Analysis           # Token/compute costs
└── Alerts/
    └── Alert Overview          # Active and recent alerts
```

### 3.2 System Overview Dashboard

```json
{
  "title": "GoAI System Overview",
  "refresh": "30s",
  "rows": [
    {
      "title": "Key Metrics",
      "panels": [
        {
          "title": "Request Rate",
          "type": "stat",
          "query": "sum(rate(http_requests_total[5m]))",
          "unit": "reqps"
        },
        {
          "title": "Error Rate",
          "type": "stat",
          "query": "sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) * 100",
          "unit": "percent",
          "thresholds": {"warning": 1, "critical": 5}
        },
        {
          "title": "P99 Latency",
          "type": "stat",
          "query": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
          "unit": "s",
          "thresholds": {"warning": 5, "critical": 10}
        },
        {
          "title": "Active Users",
          "type": "stat",
          "query": "count(count by (user_id) (http_requests_total[1h]))"
        }
      ]
    },
    {
      "title": "Traffic",
      "panels": [
        {
          "title": "Requests by Status",
          "type": "timeseries",
          "query": "sum by (status) (rate(http_requests_total[5m]))"
        },
        {
          "title": "Requests by Endpoint",
          "type": "timeseries",
          "query": "topk(10, sum by (path) (rate(http_requests_total[5m])))"
        }
      ]
    },
    {
      "title": "LLM",
      "panels": [
        {
          "title": "Tokens/Second",
          "type": "stat",
          "query": "sum(rate(llm_tokens_total[5m]))"
        },
        {
          "title": "Queue Depth",
          "type": "gauge",
          "query": "sum(llm_queue_size)",
          "thresholds": {"warning": 50, "critical": 100}
        }
      ]
    }
  ]
}
```

### 3.3 LLM Performance Dashboard

```json
{
  "title": "LLM Performance",
  "rows": [
    {
      "title": "Throughput",
      "panels": [
        {
          "title": "Requests/Second by Model",
          "type": "timeseries",
          "query": "sum by (model) (rate(llm_requests_total[5m]))"
        },
        {
          "title": "Tokens/Second",
          "type": "timeseries",
          "query": "sum by (model, direction) (rate(llm_tokens_total[5m]))"
        }
      ]
    },
    {
      "title": "Latency",
      "panels": [
        {
          "title": "Time to First Token (P95)",
          "type": "timeseries",
          "query": "histogram_quantile(0.95, sum by (model, le) (rate(llm_ttft_seconds_bucket[5m])))"
        },
        {
          "title": "Total Latency Distribution",
          "type": "heatmap",
          "query": "sum by (le) (rate(llm_request_duration_seconds_bucket[5m]))"
        }
      ]
    },
    {
      "title": "Errors",
      "panels": [
        {
          "title": "Error Rate by Model",
          "type": "timeseries",
          "query": "sum by (model) (rate(llm_requests_total{status='error'}[5m])) / sum by (model) (rate(llm_requests_total[5m])) * 100"
        },
        {
          "title": "Guardrail Triggers",
          "type": "timeseries",
          "query": "sum by (guardrail) (rate(llm_guardrail_triggers_total[5m]))"
        }
      ]
    }
  ]
}
```

### 3.4 GPU Metrics Dashboard

```json
{
  "title": "GPU Metrics",
  "rows": [
    {
      "title": "Utilization",
      "panels": [
        {
          "title": "GPU Utilization",
          "type": "timeseries",
          "query": "DCGM_FI_DEV_GPU_UTIL",
          "legend": "GPU {{gpu}}"
        },
        {
          "title": "Memory Utilization",
          "type": "timeseries",
          "query": "DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100"
        }
      ]
    },
    {
      "title": "Health",
      "panels": [
        {
          "title": "Temperature",
          "type": "gauge",
          "query": "DCGM_FI_DEV_GPU_TEMP",
          "thresholds": {"warning": 75, "critical": 85}
        },
        {
          "title": "Power Usage",
          "type": "timeseries",
          "query": "DCGM_FI_DEV_POWER_USAGE"
        },
        {
          "title": "ECC Errors",
          "type": "stat",
          "query": "DCGM_FI_DEV_ECC_DBE_AGG_TOTAL",
          "thresholds": {"warning": 1, "critical": 10}
        }
      ]
    }
  ]
}
```

---

## 4. Alerting Standard

### 4.1 Alert Severity Levels

| Severity | Response Time | Examples | Notification |
|----------|---------------|----------|--------------|
| **Critical** | 15 minutes | Service down, GPU OOM, Security breach | PagerDuty + Slack + Email |
| **Warning** | 1 hour | High latency, High error rate, Queue buildup | Slack + Email |
| **Info** | Next business day | Usage threshold, Scheduled maintenance | Email digest |

### 4.2 Alert Rules

```yaml
# Prometheus alert rules
groups:
  - name: goai_critical
    rules:
      # Service Health
      - alert: ServiceDown
        expr: up{job=~"goai.*"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          runbook: "https://docs.goai/runbooks/service-down"
          
      # LLM
      - alert: LLMQueueOverload
        expr: llm_queue_size > 100
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "LLM queue size > 100 for 5 minutes"
          
      - alert: LLMHighErrorRate
        expr: rate(llm_requests_total{status="error"}[5m]) / rate(llm_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          
      # GPU
      - alert: GPUMemoryExhausted
        expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
        for: 2m
        labels:
          severity: critical
          
      - alert: GPUHighTemperature
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels:
          severity: critical
          
      - alert: GPUECCErrors
        expr: increase(DCGM_FI_DEV_ECC_DBE_AGG_TOTAL[1h]) > 0
        labels:
          severity: critical

  - name: goai_warning
    rules:
      # Performance
      - alert: HighLatency
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 5
        for: 10m
        labels:
          severity: warning
          
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
          
      # RAG
      - alert: LowRetrievalQuality
        expr: avg(rag_sources_retrieved) < 1
        for: 15m
        labels:
          severity: warning
          
      # Cache
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.5
        for: 30m
        labels:
          severity: warning
```

### 4.3 Alert Routing

```yaml
# Alertmanager configuration
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  
  routes:
    - match:
        severity: critical
      receiver: 'critical'
      continue: true
      
    - match:
        severity: warning
      receiver: 'warning'
      
receivers:
  - name: 'critical'
    pagerduty_configs:
      - service_key: '{{ .PAGERDUTY_KEY }}'
    slack_configs:
      - api_url: '{{ .SLACK_WEBHOOK }}'
        channel: '#goai-critical'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
    email_configs:
      - to: 'oncall@company.com'
        
  - name: 'warning'
    slack_configs:
      - api_url: '{{ .SLACK_WEBHOOK }}'
        channel: '#goai-alerts'
        title: '⚠️ WARNING: {{ .GroupLabels.alertname }}'
    email_configs:
      - to: 'platform-team@company.com'
```

---

## 5. Prometheus Configuration

### 5.1 Scrape Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Gateway metrics
  - job_name: 'goai-gateway'
    static_configs:
      - targets: ['gateway:8000']
    metrics_path: /metrics
    
  # Service metrics
  - job_name: 'goai-services'
    static_configs:
      - targets: 
        - 'rag-service:8000'
        - 'agent-service:8000'
        - 'memory-service:8000'
        
  # vLLM metrics
  - job_name: 'vllm'
    static_configs:
      - targets:
        - 'vllm-70b:8001'
        - 'vllm-8b:8002'
    metrics_path: /metrics
    
  # GPU metrics (DCGM)
  - job_name: 'dcgm'
    static_configs:
      - targets: ['dcgm-exporter:9400']
    scrape_interval: 5s
    
  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s
    
  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
      
  # Node metrics
  - job_name: 'node'
    static_configs:
      - targets: 
        - 'node-exporter-1:9100'
        - 'node-exporter-2:9100'
```

### 5.2 Recording Rules

```yaml
# Recording rules for common queries
groups:
  - name: goai_recording_rules
    rules:
      # Request rate by service
      - record: goai:http_requests:rate5m
        expr: sum by (service) (rate(http_requests_total[5m]))
        
      # Error rate
      - record: goai:http_errors:rate5m
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
        
      # P99 latency
      - record: goai:http_latency:p99
        expr: histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
        
      # Token throughput
      - record: goai:llm_tokens:rate5m
        expr: sum by (model) (rate(llm_tokens_total[5m]))
        
      # GPU utilization avg
      - record: goai:gpu_utilization:avg
        expr: avg(DCGM_FI_DEV_GPU_UTIL)
        
      # Cache hit rate
      - record: goai:cache_hit_rate
        expr: sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
```

---

## 6. Quick Reference

### 6.1 Key Metrics to Monitor

| Metric | Query | Warning | Critical |
|--------|-------|---------|----------|
| Error Rate | `goai:http_errors:rate5m` | >1% | >5% |
| P99 Latency | `goai:http_latency:p99` | >5s | >10s |
| LLM Queue | `llm_queue_size` | >50 | >100 |
| GPU Util | `DCGM_FI_DEV_GPU_UTIL` | >85% | >95% |
| GPU Memory | `gpu_memory_utilization_percent` | >90% | >95% |
| GPU Temp | `DCGM_FI_DEV_GPU_TEMP` | >75°C | >85°C |
| Cache Hit Rate | `goai:cache_hit_rate` | <60% | <40% |

### 6.2 Log Locations

| Log Type | Path | Retention |
|----------|------|-----------|
| Audit | `/var/log/goai/audit/*.log` | 7 years |
| Retrieval | `/var/log/goai/retrieval/*.log` | 1 year |
| Action | `/var/log/goai/action/*.log` | 90 days |
| Model | `/var/log/goai/model/*.log` | 30 days |
| Application | `/var/log/goai/app/*.log` | 30 days |

### 6.3 Dashboard URLs

| Dashboard | URL |
|-----------|-----|
| System Overview | `/grafana/d/system-overview` |
| LLM Performance | `/grafana/d/llm-performance` |
| GPU Metrics | `/grafana/d/gpu-metrics` |
| RAG Performance | `/grafana/d/rag-performance` |
| Alert Overview | `/grafana/d/alert-overview` |

---

**GoAI Sovereign Platform v1** — Observability & Monitoring Standard 📊


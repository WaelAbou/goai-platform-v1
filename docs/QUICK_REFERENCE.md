# GoAI Sovereign Platform — Quick Reference

## 🏛️ Sovereign Stack Layers

| Layer | Components | Purpose |
|-------|------------|---------|
| **L5: Operations** | Prometheus, Grafana, Backups, DR | Monitor, backup, deploy |
| **L4: Applications** | RAG Chat, Policy Assistant, Custom | Use case microservices |
| **L3: Knowledge** | Ingestion, Chunking, FAISS, ACL | Document management |
| **L2: Gateway** | FastAPI, Keycloak, Rate Limits | Auth, routing, audit |
| **L1: Inference** | vLLM, GPU Cluster, Model Registry | LLM serving |

---

## 🚀 Quick Start

### Development (No GPU)

```bash
# Backend
cd goai-platform-v1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend  
cd ui/console
npm install && npm run dev

# Open http://localhost:3000
```

### Production (GPU)

```bash
# Start vLLM (requires GPU)
docker-compose -f docker-compose.vllm.yml up -d

# Start platform
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## 📊 Key Specifications

### GPU Requirements

| Model | GPUs | VRAM | TPS |
|-------|------|------|-----|
| Llama 70B | 4x L40S | 192GB | 50-100 |
| Llama 8B | 1x L40S | 48GB | 150-200 |
| Mistral 7B | 1x L40S | 48GB | 150-200 |

### Rate Limits

| Role | Requests/min | Tokens/min |
|------|--------------|------------|
| admin | ∞ | ∞ |
| power_user | 1000 | 500K |
| user | 100 | 50K |
| readonly | 20 | 10K |

### Chunking Standards

```
Chunk Size: 512 tokens
Overlap: 50 tokens
Embedding: BGE-large (1024 dim)
Index: FAISS IVF4096,PQ64
```

---

## 🔧 Building New Use Cases

### 1. Create Module

```python
# modules/my_feature/engine.py
from core.llm import llm_router

class MyEngine:
    async def process(self, data: str) -> dict:
        response = await llm_router.run(
            model_id="llama-70b",
            messages=[{"role": "user", "content": data}]
        )
        return {"result": response["content"]}

my_engine = MyEngine()
```

### 2. Create API

```python
# api/v1/my_feature.py
from fastapi import APIRouter, Depends
from core.auth import require_auth

router = APIRouter()

@router.post("/process")
async def process(data: str, user = Depends(require_auth)):
    return await my_engine.process(data)
```

### 3. Register in main.py

```python
from api.v1 import my_feature
app.include_router(my_feature.router, prefix="/api/v1/my-feature")
```

### 4. Create UI Page

```tsx
// ui/console/src/pages/MyFeaturePage.tsx
export default function MyFeaturePage() {
  return <div>My Feature UI</div>;
}
```

---

## 🔑 Authentication

### Get Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### Use Token

```bash
curl http://localhost:8000/api/v1/protected \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Default Credentials

| User | Password | Role |
|------|----------|------|
| admin | admin123 | Admin |

---

## 📡 Core API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/login` | POST | ❌ | Login |
| `/api/v1/auth/me` | GET | ✅ | Current user |
| `/api/v1/rag/ingest` | POST | ✅ | Ingest document |
| `/api/v1/rag/query` | POST | ✅ | Query with RAG |
| `/api/v1/stream/chat` | POST | ✅ | Streaming chat |
| `/api/v1/agents/run` | POST | ✅ | Run agent |
| `/api/v1/memory` | CRUD | ✅ | User memories |
| `/metrics` | GET | ❌ | Prometheus metrics |
| `/health` | GET | ❌ | Health check |

---

## 📊 Monitoring

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# P99 latency
histogram_quantile(0.99, http_request_duration_seconds_bucket)

# GPU utilization
DCGM_FI_DEV_GPU_UTIL

# Tokens/second
rate(llm_tokens_output_total[1m])
```

### Key Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | >5% for 5min | Critical |
| GPUMemoryExhausted | >95% | Critical |
| LLMServiceDown | health failing | Critical |
| HighLatency | P99 >10s | Warning |

---

## 💾 Database Quick Reference

### PostgreSQL Tables

```sql
-- Key tables
users, documents, document_acl, audit_logs, retrieval_audit, feedback
```

### FAISS Indexes

```
indexes/
├── global.faiss       # Main index
├── global.pkl         # ID mapping
├── policies.faiss     # Namespace index
└── metadata.json      # Config
```

### Redis Keys

```
session:{user_id}           # Sessions (24h TTL)
rate:{user_id}:requests     # Rate limiting (60s TTL)
cache:embed:{hash}          # Embeddings (1h TTL)
```

---

## 🔄 Operations

### Blue/Green Deployment

```bash
# Deploy new model
./scripts/deploy_model.sh llama-70b v2

# Rollback
./scripts/rollback.sh
```

### Backup

```bash
# Manual backup
./scripts/backup.sh

# Restore
./scripts/restore.sh
```

### Health Checks

```bash
# Full system check
./scripts/health_check.sh

# vLLM health
curl http://localhost:8001/health

# Gateway health
curl http://localhost:8000/health
```

---

## 🔒 Security Checklist

- [ ] Change default admin password
- [ ] Configure Keycloak
- [ ] Enable TLS
- [ ] Set up audit logging
- [ ] Configure rate limits
- [ ] Set document ACLs
- [ ] Enable backups
- [ ] Test DR procedure

---

## 📁 Project Structure

```
goai-platform-v1/
├── main.py              # Entry point
├── core/                # L2 Gateway + shared
│   ├── llm/            # LLM routing
│   ├── vector/         # Vector store
│   ├── auth/           # Authentication
│   └── telemetry/      # Metrics
├── modules/            # L4 Applications
│   ├── rag/            # RAG engine
│   ├── agents/         # AI agents
│   └── [custom]/       # Your modules
├── api/v1/             # REST endpoints
├── ui/console/         # React frontend
├── data/               # SQLite databases
├── workflows/          # YAML workflows
└── docs/               # Documentation
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| GPU OOM | Reduce `--max-model-len` or batch size |
| Slow responses | Check queue depth, add GPUs |
| Auth failing | Verify JWT_SECRET matches |
| ACL blocking | Check document_acl table |
| Rate limited | Upgrade user role |

---

**GoAI Sovereign Platform v1** — Quick Reference 🏛️

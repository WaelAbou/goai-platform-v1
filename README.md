# GoAI Sovereign AI Platform v1

## Enterprise Architecture Reference

> A complete, self-hosted AI infrastructure for sovereign deployments with full control over data, models, and operations.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Modules](#core-modules)
3. [AI Agent Framework](#ai-agent-framework)
4. [Security & Governance](#security--governance)
5. [Sovereign Stack Overview](#sovereign-stack-overview)
6. [Layer 1 — Inference Layer](#layer-1--inference-layer)
7. [Layer 2 — Gateway Layer](#layer-2--gateway-layer)
8. [Layer 3 — Knowledge Layer](#layer-3--knowledge-layer)
9. [Layer 4 — Application Layer](#layer-4--application-layer)
10. [Layer 5 — Operations Layer](#layer-5--operations-layer)
11. [Testing Use Cases](#testing-use-cases)
12. [Implementation Guide](#implementation-guide)
13. [Appendix](#appendix)

---

## Executive Summary

### What is GoAI Sovereign Platform?

GoAI is a **fully self-hosted AI infrastructure** designed for organizations requiring:

- **Data Sovereignty** — All data remains on-premises or in private cloud
- **Model Control** — Run open-source or fine-tuned models internally
- **Regulatory Compliance** — GDPR, HIPAA, PCI-DSS compatible architecture
- **Cost Optimization** — Reduce cloud AI API costs at scale
- **Customization** — Domain-specific models and workflows

### Key Capabilities

| Capability | Description |
|------------|-------------|
| 🔐 **Sovereign Inference** | GPU-accelerated LLM hosting with vLLM/TGI |
| 📚 **Enterprise RAG** | Document retrieval with ACL and audit trails |
| 🤖 **AI Agents** | Tool-using agents with controlled access |
| 👥 **Multi-Tenant** | User isolation, RBAC, and quota management |
| 📊 **Full Observability** | Prometheus metrics, Grafana dashboards, audit logs |
| 🔄 **Production Ready** | Blue/green deployments, DR, and backup automation |
| 📈 **AI Evaluations** | LLM-as-Judge quality measurement and regression detection |
| 🔌 **MCP Protocol** | Standardized tool integration via Model Context Protocol |
| 🪝 **Event-Driven** | Webhooks and triggers for automated workflows |
| 🧠 **Memory System** | Multi-tier agent memory (short/medium/long-term) |

### Deployment Options

| Environment | GPU | Recommended For |
|-------------|-----|-----------------|
| Development | None (CPU) or 1x RTX 4090 | Testing, POC |
| Production Single | 2x L40S / 2x Gaudi2 | Small-medium workloads |
| Production HA | 4-8x L40S / Gaudi2 cluster | Enterprise scale |
| Air-Gapped | Ascend 910B cluster | Highest security |

---

## Core Modules

These **non-negotiable modules** are included in every deployment and form the foundation of the sovereign stack.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          CORE MODULES (Always Deployed)                             │
│                                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│   │ ⚙️ LLM       │  │ 🧠 Orchestr- │  │ 🔍 Vector    │  │ 🔐 Auth &    │           │
│   │    Router    │  │    ator      │  │    Store     │  │    RBAC      │           │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│   │ ⛓️ Retrieval │  │ 📄 Ingestion │  │ 📨 Streaming │  │ 🧩 Multi-    │           │
│   │    Logging   │  │    Pipeline  │  │    Engine    │  │    Agent     │           │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│   │ 📊 AI Evals  │  │ 🔌 MCP       │  │ 🪝 Triggers  │  │ 🧠 Memory    │           │
│   │              │  │    Protocol  │  │    Webhooks  │  │    System    │           │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| Module | Purpose | Configurable | Standard (Not Configurable) |
|--------|---------|--------------|----------------------------|
| **⚙️ LLM Router** | Unified LLM interface across providers | Models, timeouts, fallback | Interface, response format, metrics |
| **🧠 Orchestrator** | YAML workflow execution | Workflows, actions, timeouts | Format, built-in actions, variables |
| **🔍 Vector Store** | Semantic search (FAISS) | Embedding model, index params | Dimensions (1024), cosine metric |
| **🔐 Auth & RBAC** | Authentication & authorization | Provider, expiry, MFA | 5 roles, permissions, JWT format |
| **⛓️ Retrieval Logging** | Audit trails for all retrievals | Retention, partitioning | Schema, required fields |
| **📄 Ingestion Pipeline** | Document processing | Chunk size, OCR, file limits | Supported types, embedding model |
| **📨 Streaming Engine** | Real-time SSE streaming | Timeouts, buffers | Protocol, event types |
| **🧩 Multi-Agent** | Collaborative AI agents | Custom tools/roles | Core roles, patterns, presets |
| **📊 AI Evals** | LLM-as-Judge quality evaluation | Metrics, datasets, thresholds | Scoring format, evaluation flow |
| **🔌 MCP Protocol** | Model Context Protocol integration | External servers, tool mapping | Protocol spec, message format |
| **🪝 Triggers/Webhooks** | Event-driven orchestration | Actions, filters, signatures | Event schema, retry policy |
| **🧠 Memory System** | Multi-tier agent memory | Retention, categories | Memory types, extraction |

> 📖 **Full specification**: See [docs/CORE_MODULES.md](docs/CORE_MODULES.md) for complete API definitions, configuration options, and standards.

---

## AI Agent Framework

The platform implements a complete **7-step AI Agent Framework** covering all essential components:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           7-STEP AI AGENT FRAMEWORK                                  │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                               │  │
│   │    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │  │
│   │    │ 1.      │   │ 2.      │   │ 3.      │   │ 4.      │   │ 5.      │     │  │
│   │    │ System  │──▶│  LLM    │──▶│  Tools  │──▶│ Memory  │──▶│ Orches- │     │  │
│   │    │ Prompt  │   │         │   │         │   │         │   │ tration │     │  │
│   │    └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘     │  │
│   │         │             │             │             │             │           │  │
│   │         ▼             ▼             ▼             ▼             ▼           │  │
│   │    ┌─────────────────────────────────────────────────────────────────┐     │  │
│   │    │                        6. UI Layer                              │     │  │
│   │    │          (Console, Chat, API Endpoints, Streaming)              │     │  │
│   │    └─────────────────────────────────────────────────────────────────┘     │  │
│   │         │                                                                   │  │
│   │         ▼                                                                   │  │
│   │    ┌─────────────────────────────────────────────────────────────────┐     │  │
│   │    │                      7. AI Evaluations                          │     │  │
│   │    │        (LLM-as-Judge, Datasets, Regression, Quality)            │     │  │
│   │    └─────────────────────────────────────────────────────────────────┘     │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Framework Components

| Step | Component | Implementation | Location |
|------|-----------|----------------|----------|
| **1. System Prompt** | Configurable agent personas | Prompt templates, per-agent config | `modules/agents/engine.py`, `api/v1/prompts.py` |
| **2. LLM** | Multi-provider routing | OpenAI, Anthropic, Ollama, vLLM | `core/llm/router.py` |
| **3. Tools** | Extensible tool registry | Calculator, Python, Web Search, etc. | `modules/agents/tools.py` |
| **4. Memory** | Multi-tier persistence | Short/Medium/Long-term, SQLite | `api/v1/memory.py` |
| **5. Orchestration** | Workflow engine | YAML workflows, conditional logic | `core/orchestrator/engine.py` |
| **6. UI** | Frontend interfaces | React console, API endpoints | `ui/console/`, `api/v1/` |
| **7. AI Evals** | Quality measurement | LLM-as-Judge, datasets | `modules/evals/engine.py` |

### Additional Integrations

| Module | Purpose | API Endpoints |
|--------|---------|---------------|
| **Plan-and-Execute** | Complex task decomposition | `POST /api/v1/agents/plan-execute` |
| **MCP Protocol** | Standardized tool integration | `GET /api/v1/mcp/tools`, `POST /api/v1/mcp/execute` |
| **Triggers/Webhooks** | Event-driven automation | `POST /api/v1/triggers/webhooks` |
| **Multi-Agent** | Agent collaboration patterns | `POST /api/v1/multi-agent/session` |
| **RAG Pipeline** | Document-grounded generation | `POST /api/v1/rag/query` |

### Plan-and-Execute Pattern

For complex tasks requiring strategic planning:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           PLAN-AND-EXECUTE FLOW                                      │
│                                                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│   │  TASK    │───▶│  PLAN    │───▶│ EXECUTE  │───▶│ REPLAN?  │───▶│SYNTHESIZE│    │
│   │          │    │          │    │  Steps   │    │          │    │          │    │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    │
│                         │              │               │                           │
│                         ▼              ▼               ▼                           │
│                   Create steps   Use tools      Revise if                          │
│                   with deps      per step       step fails                         │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**API Usage:**
```bash
# Full plan-and-execute
curl -X POST http://localhost:8000/api/v1/agents/plan-execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Research Python web frameworks and recommend the best one"}'

# Preview plan only (without execution)
curl -X POST "http://localhost:8000/api/v1/agents/plan-only?task=Build+a+calculator+app"
```

---

## Security & Governance

Enterprise-grade security controls for regulated industries: **Banking**, **Telecom**, **Government**, **Healthcare**.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY & GOVERNANCE FRAMEWORK                             │
│                                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│   │ 🔐 RBAC      │  │ 👤 User      │  │ 📄 Document  │  │ 🔒 Sensitive │           │
│   │    7 Roles   │  │   Isolation  │  │    ACL       │  │    Data      │           │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│   │ 🛡️ LLM       │  │ 📊 Audit     │  │ ⚡ Rate      │  │ 🏭 Model     │           │
│   │   Guardrails │  │   Logging    │  │   Control    │  │   Lifecycle  │           │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| Control | Description | Compliance |
|---------|-------------|------------|
| **🔐 RBAC** | 7-role hierarchy (super_admin → service) | SOC2, ISO 27001 |
| **👤 User Isolation** | Row-level security, tenant boundaries | GDPR Art. 25 |
| **📄 Document ACL** | Per-doc permissions, classification levels | PCI-DSS Req. 7 |
| **🔒 Sensitive Data** | PII detection, encryption, masking | GDPR, HIPAA |
| **🛡️ LLM Guardrails** | Input/output filtering, injection protection | AI Safety |
| **📊 Audit Logging** | Complete trail, 7-year retention, immutable | All regulations |
| **⚡ Rate Control** | Multi-tier limits, quota management | DDoS protection |
| **🏭 Model Lifecycle** | Evaluate → Approve → Deploy → Monitor → Retire | Model governance |

### On-Premises Isolation

```yaml
Guarantees:
  - ✅ No data egress to external services
  - ✅ GPU nodes air-gapped (optional)
  - ✅ All models run locally
  - ✅ No external API dependencies
  - ✅ Backups stored on-premises only
```

> 📖 **Full specification**: See [docs/SECURITY_GOVERNANCE.md](docs/SECURITY_GOVERNANCE.md) for complete security controls, compliance mapping, and isolation checklist.

---

## Documentation Suite

| Document | Description | Audience |
|----------|-------------|----------|
| [CORE_MODULES.md](docs/CORE_MODULES.md) | 12 core platform modules | Architects, Developers |
| [SECURITY_GOVERNANCE.md](docs/SECURITY_GOVERNANCE.md) | Security controls, RBAC, compliance | Security, Compliance |
| [DEVELOPMENT_CYCLE.md](docs/DEVELOPMENT_CYCLE.md) | 10-step development process | Developers |
| [USE_CASE_BLUEPRINT.md](docs/USE_CASE_BLUEPRINT.md) | Templates for new use cases | Product, Developers |
| [OPERATIONAL_PLAYBOOKS.md](docs/OPERATIONAL_PLAYBOOKS.md) | Maintenance procedures | Operations, SRE |
| [OBSERVABILITY_MONITORING.md](docs/OBSERVABILITY_MONITORING.md) | Metrics, logs, dashboards | Operations, SRE |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture diagrams | Architects |
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | Developer cheat sheet | Developers |

### Use Case Examples

| Use Case | Location | Description |
|----------|----------|-------------|
| Customer KYC | `use_cases/customer_kyc/` | Document verification & risk assessment |
| Document Q&A | `use_cases/document_qa/` | RAG-powered document search |

---

## Sovereign Stack Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                           GoAI SOVEREIGN AI PLATFORM v1                                  │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 5 — OPERATIONS LAYER                                  │ │
│  │                                                                                     │ │
│  │   Prometheus + Grafana │ Backups │ Blue/Green Deploy │ DR │ Alerting             │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                       LAYER 4 — APPLICATION LAYER                                  │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │ │
│  │  │ RAG Chat     │ │ Policy       │ │ CVM Insight  │ │ Document     │    ...       │ │
│  │  │ Service      │ │ Assistant    │ │ Service      │ │ Validator    │              │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                       LAYER 3 — KNOWLEDGE LAYER                                    │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │ │
│  │  │ Document     │ │ Text         │ │ Chunking     │ │ Embedding    │              │ │
│  │  │ Ingestion    │ │ Extraction   │ │ Engine       │ │ Service      │              │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                               │ │
│  │  │ FAISS        │ │ ACL          │ │ Retrieval    │                               │ │
│  │  │ Vector Store │ │ Manager      │ │ Auditor      │                               │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                               │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 2 — GATEWAY LAYER                                     │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │ │
│  │  │ FastAPI      │ │ Keycloak     │ │ Rate         │ │ Audit        │              │ │
│  │  │ Gateway      │ │ RBAC         │ │ Limiter      │ │ Logger       │              │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                               │ │
│  │  │ Prometheus   │ │ API          │ │ Request      │                               │ │
│  │  │ Metrics      │ │ Contracts    │ │ Router       │                               │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                               │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                       LAYER 1 — INFERENCE LAYER                                    │ │
│  │                                                                                     │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                         GPU INFRASTRUCTURE                                    │ │ │
│  │  │                                                                               │ │ │
│  │  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │ │ │
│  │  │   │  NVIDIA     │   │  Intel      │   │  Huawei     │   │  AMD        │     │ │ │
│  │  │   │  L40S/H100  │   │  Gaudi2/3   │   │  Ascend 910 │   │  MI300X     │     │ │ │
│  │  │   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │ │ │
│  │  │                                                                               │ │ │
│  │  └──────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │ │
│  │  │ vLLM         │ │ TGI          │ │ Ollama       │ │ Custom       │              │ │
│  │  │ Container    │ │ Container    │ │ (Dev Only)   │ │ Inference    │              │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │ │
│  │                                                                                     │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                               │ │
│  │  │ Model        │ │ Model        │ │ Model        │                               │ │
│  │  │ Registry     │ │ Router       │ │ Health       │                               │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                               │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           DATA STORES                                              │ │
│  │                                                                                     │ │
│  │   PostgreSQL │ FAISS │ Redis │ MinIO/S3 │ Elasticsearch                           │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — Inference Layer

The Inference Layer provides GPU-accelerated model serving for LLM workloads.

### 1.1 GPU Infrastructure

#### Supported Hardware

| Hardware | VRAM | Recommended Models | TPS* | Use Case |
|----------|------|-------------------|------|----------|
| **NVIDIA L40S** | 48GB | Llama 3.1 70B (4-bit), Mistral 7B | 50-100 | Production |
| **NVIDIA H100** | 80GB | Llama 3.1 70B (FP16), 405B (4-bit) | 150-300 | High throughput |
| **Intel Gaudi2** | 96GB | Llama 3.1 70B (FP16) | 80-120 | Cost-effective |
| **Intel Gaudi3** | 128GB | Llama 3.1 405B | 200+ | Latest gen |
| **Huawei Ascend 910B** | 64GB | Llama 3.1 70B | 60-100 | Air-gapped |
| **AMD MI300X** | 192GB | Llama 3.1 405B (FP16) | 180-250 | High memory |

*TPS = Tokens per second (generation)

#### GPU Cluster Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    GPU Cluster (Production)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Node 1 (Primary)                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ GPU 0   │ │ GPU 1   │ │ GPU 2   │ │ GPU 3   │       │   │
│  │  │ L40S    │ │ L40S    │ │ L40S    │ │ L40S    │       │   │
│  │  │ 48GB    │ │ 48GB    │ │ 48GB    │ │ 48GB    │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  │                                                          │   │
│  │  Model: Llama-3.1-70B-Instruct (Tensor Parallel=4)      │   │
│  │  Container: vLLM v0.5.x                                  │   │
│  │  Port: 8001                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Node 2 (Secondary)                    │   │
│  │  ┌─────────┐ ┌─────────┐                                │   │
│  │  │ GPU 0   │ │ GPU 1   │                                │   │
│  │  │ L40S    │ │ L40S    │      (Available for scaling)   │   │
│  │  │ 48GB    │ │ 48GB    │                                │   │
│  │  └─────────┘ └─────────┘                                │   │
│  │                                                          │   │
│  │  Model: Llama-3.1-8B-Instruct (Embedding + Fast)        │   │
│  │  Container: vLLM v0.5.x                                  │   │
│  │  Port: 8002                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Inference Containers

#### vLLM Configuration (Recommended)

```yaml
# docker-compose.vllm.yml
version: '3.8'
services:
  vllm-70b:
    image: vllm/vllm-openai:v0.5.4
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 4
              capabilities: [gpu]
    environment:
      - CUDA_VISIBLE_DEVICES=0,1,2,3
    command: >
      --model meta-llama/Llama-3.1-70B-Instruct
      --tensor-parallel-size 4
      --max-model-len 8192
      --gpu-memory-utilization 0.95
      --dtype bfloat16
      --port 8001
      --api-key ${VLLM_API_KEY}
    ports:
      - "8001:8001"
    volumes:
      - ./models:/root/.cache/huggingface
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  vllm-8b:
    image: vllm/vllm-openai:v0.5.4
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - CUDA_VISIBLE_DEVICES=4
    command: >
      --model meta-llama/Llama-3.1-8B-Instruct
      --max-model-len 32768
      --gpu-memory-utilization 0.90
      --dtype bfloat16
      --port 8002
      --api-key ${VLLM_API_KEY}
    ports:
      - "8002:8002"
```

#### TGI Configuration (Alternative)

```yaml
# docker-compose.tgi.yml
services:
  tgi-70b:
    image: ghcr.io/huggingface/text-generation-inference:2.0
    runtime: nvidia
    command: >
      --model-id meta-llama/Llama-3.1-70B-Instruct
      --num-shard 4
      --max-input-length 4096
      --max-total-tokens 8192
      --port 8001
    ports:
      - "8001:8001"
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
    volumes:
      - ./models:/data
```

### 1.3 Model Endpoints

#### Model Registry

| Model ID | Endpoint | Context | Use Case | Priority |
|----------|----------|---------|----------|----------|
| `llama-70b` | `http://vllm-70b:8001/v1` | 8192 | General, RAG, Agents | Primary |
| `llama-8b` | `http://vllm-8b:8002/v1` | 32768 | Embeddings, Fast queries | Secondary |
| `mistral-7b` | `http://vllm-mistral:8003/v1` | 32768 | Coding, Structured output | Fallback |

#### Model Router Configuration

```python
# config/models.yaml
models:
  llama-70b:
    endpoint: "http://vllm-70b:8001/v1"
    type: "chat"
    context_length: 8192
    max_output_tokens: 4096
    temperature_default: 0.7
    rate_limit: 100  # requests/minute
    priority: 1
    
  llama-8b:
    endpoint: "http://vllm-8b:8002/v1"
    type: "chat"
    context_length: 32768
    max_output_tokens: 8192
    temperature_default: 0.3
    rate_limit: 500
    priority: 2
    use_for:
      - embeddings
      - classification
      - fast_queries

  fallback:
    type: "external"
    provider: "openai"  # Only if sovereign not available
    model: "gpt-4o-mini"
    enabled: false  # Disabled by default
```

### 1.4 Performance Specifications

#### Token Limits

| Model | Input Limit | Output Limit | Total Context | Batch Size |
|-------|-------------|--------------|---------------|------------|
| Llama 70B | 6144 | 2048 | 8192 | 32 |
| Llama 8B | 28672 | 4096 | 32768 | 64 |
| Mistral 7B | 28672 | 4096 | 32768 | 64 |

#### Performance Benchmarks

| Metric | Llama 70B (4x L40S) | Llama 8B (1x L40S) |
|--------|---------------------|-------------------|
| Time to First Token | 200-400ms | 50-100ms |
| Tokens/Second (Gen) | 40-60 | 150-200 |
| Concurrent Requests | 8-16 | 32-64 |
| P99 Latency | <2s | <500ms |
| Throughput (tokens/min) | 50,000 | 200,000 |

#### GPU Memory Layout

```
┌──────────────────────────────────────────────────────────────┐
│                   L40S 48GB Memory Layout                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Model Weights (70B/4 = 17.5B)            │ │
│  │                ~35GB (BF16)                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                KV Cache                                  │ │
│  │                ~10GB (dynamic)                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Activations + Overhead                    │ │
│  │                ~3GB                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  Total: 48GB | Utilization: 95%                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Layer 2 — Gateway Layer

The Gateway Layer handles authentication, authorization, rate limiting, and API routing.

### 2.1 FastAPI Gateway

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Gateway                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Request Flow:                                                   │
│                                                                  │
│  Client ──▶ NGINX ──▶ FastAPI ──▶ Middleware Stack ──▶ Routes   │
│                          │                                       │
│                          ▼                                       │
│               ┌─────────────────────────┐                       │
│               │    Middleware Stack     │                       │
│               ├─────────────────────────┤                       │
│               │ 1. CORS                 │                       │
│               │ 2. Request ID           │                       │
│               │ 3. Keycloak Auth        │                       │
│               │ 4. Rate Limiter         │                       │
│               │ 5. Audit Logger         │                       │
│               │ 6. Metrics Collector    │                       │
│               │ 7. Error Handler        │                       │
│               └─────────────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Gateway Configuration

```python
# main.py - Gateway Setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(
    title="GoAI Sovereign Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware Stack (order matters!)
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(KeycloakAuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
```

### 2.2 Keycloak RBAC

#### Role Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                     Keycloak Realm: goai                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Roles:                                                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                                              ││
│  │  ┌──────────────┐                                           ││
│  │  │    admin     │ ◄── Full access, user management          ││
│  │  └──────┬───────┘                                           ││
│  │         │                                                    ││
│  │         ▼                                                    ││
│  │  ┌──────────────┐                                           ││
│  │  │   operator   │ ◄── Model deployment, monitoring          ││
│  │  └──────┬───────┘                                           ││
│  │         │                                                    ││
│  │         ▼                                                    ││
│  │  ┌──────────────┐                                           ││
│  │  │  power_user  │ ◄── All AI features, high limits          ││
│  │  └──────┬───────┘                                           ││
│  │         │                                                    ││
│  │         ▼                                                    ││
│  │  ┌──────────────┐                                           ││
│  │  │     user     │ ◄── Standard AI features                  ││
│  │  └──────┬───────┘                                           ││
│  │         │                                                    ││
│  │         ▼                                                    ││
│  │  ┌──────────────┐                                           ││
│  │  │   readonly   │ ◄── View only, no generation              ││
│  │  └──────────────┘                                           ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Permission Matrix

| Permission | admin | operator | power_user | user | readonly |
|------------|-------|----------|------------|------|----------|
| `llm:generate` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `llm:generate:70b` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `rag:query` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `rag:ingest` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `rag:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `agents:run` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `agents:tools:all` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `admin:users` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `admin:models` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `audit:view` | ✅ | ✅ | ❌ | ❌ | ❌ |

#### Keycloak Integration

```python
# core/auth/keycloak.py
from keycloak import KeycloakOpenID

class KeycloakAuth:
    def __init__(self):
        self.keycloak = KeycloakOpenID(
            server_url=os.getenv("KEYCLOAK_URL"),
            client_id="goai-platform",
            realm_name="goai",
            client_secret_key=os.getenv("KEYCLOAK_SECRET")
        )
    
    async def validate_token(self, token: str) -> dict:
        """Validate JWT and return user info with roles."""
        try:
            token_info = self.keycloak.decode_token(token)
            return {
                "user_id": token_info["sub"],
                "username": token_info["preferred_username"],
                "email": token_info["email"],
                "roles": token_info.get("realm_access", {}).get("roles", []),
                "groups": token_info.get("groups", [])
            }
        except Exception:
            raise HTTPException(401, "Invalid token")
    
    def has_permission(self, user: dict, permission: str) -> bool:
        """Check if user has required permission."""
        role_permissions = ROLE_PERMISSIONS.get(user["roles"][0], [])
        return permission in role_permissions
```

### 2.3 Rate Limiting

#### Rate Limit Tiers

| Tier | Requests/Min | Tokens/Min | Concurrent | Assigned To |
|------|--------------|------------|------------|-------------|
| **Unlimited** | ∞ | ∞ | 100 | admin, operator |
| **Enterprise** | 1000 | 500,000 | 50 | power_user |
| **Standard** | 100 | 50,000 | 10 | user |
| **Basic** | 20 | 10,000 | 3 | readonly |

#### Rate Limiter Implementation

```python
# core/gateway/rate_limiter.py
from redis import Redis
from fastapi import Request, HTTPException

class RateLimiter:
    def __init__(self):
        self.redis = Redis(host=os.getenv("REDIS_HOST"))
    
    async def check_limit(self, request: Request, user: dict):
        """Check and enforce rate limits."""
        tier = self.get_tier(user["roles"])
        limits = RATE_LIMITS[tier]
        
        # Request count
        key = f"rate:{user['user_id']}:requests"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 60)
        
        if count > limits["requests_per_minute"]:
            raise HTTPException(
                429, 
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limits["requests_per_minute"],
                    "reset_in": self.redis.ttl(key)
                }
            )
        
        # Add rate limit headers
        request.state.rate_limit_remaining = limits["requests_per_minute"] - count
```

### 2.4 Audit Logging

#### Audit Log Schema

```sql
-- PostgreSQL audit_logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(255),
    username VARCHAR(255),
    client_ip INET,
    user_agent TEXT,
    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    query_params JSONB,
    request_body JSONB,
    response_status INT,
    response_time_ms INT,
    tokens_used INT,
    model_used VARCHAR(100),
    error_message TEXT,
    metadata JSONB,
    
    -- Indexes
    INDEX idx_timestamp (timestamp),
    INDEX idx_user_id (user_id),
    INDEX idx_path (path),
    INDEX idx_status (response_status)
);

-- Partition by month for performance
CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

#### Audit Logger Middleware

```python
# core/gateway/audit.py
class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Capture request
        body = await request.body()
        
        # Process request
        response = await call_next(request)
        
        # Log to PostgreSQL (async)
        asyncio.create_task(self.log_request(
            request_id=request_id,
            user_id=getattr(request.state, "user_id", None),
            method=request.method,
            path=request.url.path,
            request_body=self.sanitize_body(body),
            response_status=response.status_code,
            response_time_ms=int((time.time() - start_time) * 1000),
            tokens_used=getattr(request.state, "tokens_used", 0)
        ))
        
        return response
    
    def sanitize_body(self, body: bytes) -> dict:
        """Remove sensitive fields from logged body."""
        try:
            data = json.loads(body)
            for field in ["password", "api_key", "token"]:
                if field in data:
                    data[field] = "[REDACTED]"
            return data
        except:
            return {}
```

### 2.5 Prometheus Metrics

#### Exposed Metrics

```python
# Metrics exported at /metrics

# Request metrics
http_requests_total{method, path, status}
http_request_duration_seconds{method, path}
http_requests_in_progress{method}

# LLM metrics
llm_requests_total{model, status}
llm_tokens_input_total{model}
llm_tokens_output_total{model}
llm_request_duration_seconds{model}
llm_queue_size{model}

# RAG metrics
rag_queries_total{status}
rag_retrieval_duration_seconds
rag_documents_total
rag_chunks_total

# System metrics
system_cpu_usage_percent
system_memory_usage_bytes
gpu_memory_usage_bytes{gpu_id}
gpu_utilization_percent{gpu_id}
```

### 2.6 API Contracts

#### OpenAPI Specification

```yaml
# All endpoints follow this contract
openapi: 3.1.0
info:
  title: GoAI Sovereign Platform API
  version: 1.0.0

paths:
  /api/v1/llm/generate:
    post:
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenerateRequest'
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenerateResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'
        '500':
          $ref: '#/components/responses/InternalError'

components:
  schemas:
    GenerateRequest:
      type: object
      required: [messages]
      properties:
        model:
          type: string
          default: "llama-70b"
        messages:
          type: array
          items:
            $ref: '#/components/schemas/Message'
        temperature:
          type: number
          minimum: 0
          maximum: 2
          default: 0.7
        max_tokens:
          type: integer
          minimum: 1
          maximum: 4096
        stream:
          type: boolean
          default: false
    
    GenerateResponse:
      type: object
      properties:
        id:
          type: string
        content:
          type: string
        model:
          type: string
        usage:
          $ref: '#/components/schemas/Usage'
        
    Usage:
      type: object
      properties:
        prompt_tokens:
          type: integer
        completion_tokens:
          type: integer
        total_tokens:
          type: integer
```

---

## Layer 3 — Knowledge Layer

The Knowledge Layer handles document ingestion, processing, storage, and retrieval with access control.

### 3.1 Document Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   Document Ingestion Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Upload  │───▶│  Extract │───▶│  Chunk   │───▶│  Embed   │  │
│  │          │    │  Text    │    │          │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Validate │    │ Metadata │    │ Overlap  │    │ Batch    │  │
│  │ Format   │    │ Extract  │    │ Strategy │    │ Process  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                       │         │
│                                                       ▼         │
│                                              ┌──────────────┐   │
│                                              │    FAISS     │   │
│                                              │    Index     │   │
│                                              └──────────────┘   │
│                                                       │         │
│                                                       ▼         │
│                                              ┌──────────────┐   │
│                                              │  PostgreSQL  │   │
│                                              │  Metadata    │   │
│                                              └──────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Text Extraction Standards

#### Supported Formats

| Format | Extractor | Page Support | Metadata |
|--------|-----------|--------------|----------|
| PDF | PyMuPDF + pdfplumber | ✅ Yes | Title, Author, Pages |
| DOCX | python-docx | ✅ Yes (sections) | Title, Author |
| XLSX | openpyxl | ✅ Yes (sheets) | Sheet names |
| PPTX | python-pptx | ✅ Yes (slides) | Slide titles |
| TXT/MD | Native | ❌ No | Filename |
| HTML | BeautifulSoup | ❌ No | Title, Links |
| CSV | pandas | ❌ No | Headers |

#### Extraction Configuration

```python
# config/extraction.yaml
extraction:
  pdf:
    ocr_enabled: true
    ocr_language: "eng"
    extract_tables: true
    extract_images: false
    max_pages: 500
    
  docx:
    extract_headers: true
    extract_footnotes: true
    preserve_formatting: false
    
  xlsx:
    max_rows_per_sheet: 10000
    include_formulas: false
    sheet_separator: "\n---SHEET: {name}---\n"
    
  html:
    remove_scripts: true
    remove_styles: true
    extract_links: true
    
  general:
    max_file_size_mb: 50
    encoding: "utf-8"
    fallback_encoding: "latin-1"
```

### 3.3 Chunking Standards

#### Chunking Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Chunking Strategy                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Document                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Page 1                                                       ││
│  │ ═══════════════════════════════════════════════════════════ ││
│  │ Introduction to Machine Learning                             ││
│  │                                                               ││
│  │ Machine learning is a subset of artificial intelligence...   ││
│  │ [continues for 2000 characters]                              ││
│  │                                                               ││
│  │ ─────────────────────────────────────────────────────────── ││
│  │                                                               ││
│  │ Supervised Learning                                          ││
│  │                                                               ││
│  │ In supervised learning, the algorithm learns from labeled... ││
│  │ [continues for 1500 characters]                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│                          ▼                                       │
│  Chunks (with overlap)                                           │
│  ┌──────────────────────┐ ┌──────────────────────┐              │
│  │ Chunk 1              │ │ Chunk 2              │              │
│  │ ──────────────────── │ │ ──────────────────── │              │
│  │ [Intro section]      │ │ [End of intro +      │              │
│  │ 512 tokens           │ │  Supervised section] │              │
│  │ Page: 1              │ │ 512 tokens           │              │
│  │ Section: Intro       │ │ Page: 1              │              │
│  └──────────────────────┘ └──────────────────────┘              │
│         │                         │                              │
│         └────────┬────────────────┘                              │
│                  │                                               │
│           50 token overlap                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Chunking Configuration

```python
# config/chunking.yaml
chunking:
  default:
    strategy: "semantic"  # semantic, fixed, sentence
    chunk_size: 512       # tokens
    chunk_overlap: 50     # tokens
    min_chunk_size: 100   # tokens
    
  by_document_type:
    pdf:
      respect_pages: true
      respect_sections: true
      
    code:
      strategy: "ast"     # Parse code structure
      chunk_by: "function"
      
    table:
      strategy: "row"
      rows_per_chunk: 50
      include_headers: true
      
  metadata_to_include:
    - page_number
    - section_title
    - document_id
    - filename
    - created_at
```

### 3.4 Embedding Standards

#### Embedding Models

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| `bge-large-en-v1.5` | 1024 | Medium | High | Default |
| `bge-base-en-v1.5` | 768 | Fast | Good | High volume |
| `e5-large-v2` | 1024 | Medium | High | Alternative |
| `multilingual-e5-large` | 1024 | Slow | High | Multi-language |

#### Embedding Service

```python
# core/embedding/service.py
class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        self.batch_size = 32
        self.normalize = True
        
    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Embed documents with batching."""
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(
                batch,
                normalize_embeddings=self.normalize,
                show_progress_bar=False
            )
            embeddings.extend(batch_embeddings)
        return np.array(embeddings)
    
    async def embed_query(self, query: str) -> np.ndarray:
        """Embed query with instruction prefix."""
        # BGE requires instruction prefix for queries
        prefixed_query = f"Represent this sentence for retrieval: {query}"
        return self.model.encode(
            prefixed_query,
            normalize_embeddings=self.normalize
        )
```

### 3.5 FAISS Index Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                     FAISS Index Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Index Structure: IVF + PQ (for large scale)                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Master Index                              ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      ││
│  │  │  Namespace:  │  │  Namespace:  │  │  Namespace:  │      ││
│  │  │   global     │  │  dept_legal  │  │  dept_hr     │      ││
│  │  │              │  │              │  │              │      ││
│  │  │  Vectors:    │  │  Vectors:    │  │  Vectors:    │      ││
│  │  │  500,000     │  │  50,000      │  │  30,000      │      ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘      ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Index Files:                                                    │
│  ├── indexes/                                                    │
│  │   ├── global.faiss          (Main index)                     │
│  │   ├── global.pkl            (ID mapping)                     │
│  │   ├── dept_legal.faiss      (Department index)               │
│  │   ├── dept_hr.faiss                                          │
│  │   └── metadata.json         (Index configuration)            │
│                                                                  │
│  Configuration:                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  index_type: "IVF4096,PQ64"                                 ││
│  │  dimensions: 1024                                            ││
│  │  metric: "cosine"                                            ││
│  │  nprobe: 128  (search clusters)                             ││
│  │  training_size: 100000                                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 ACL Per Document

#### Access Control Model

```sql
-- PostgreSQL document ACL tables
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    visibility VARCHAR(20) DEFAULT 'private',  -- private, group, public
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE document_acl (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    principal_type VARCHAR(20) NOT NULL,  -- user, group, role
    principal_id VARCHAR(255) NOT NULL,
    permission VARCHAR(20) NOT NULL,       -- read, write, admin
    granted_by VARCHAR(255) NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    UNIQUE(document_id, principal_type, principal_id)
);

CREATE TABLE document_groups (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example: Grant legal department access to contract documents
INSERT INTO document_acl (document_id, principal_type, principal_id, permission, granted_by)
VALUES 
    ('doc-uuid', 'group', 'legal-department', 'read', 'admin'),
    ('doc-uuid', 'role', 'power_user', 'read', 'admin');
```

#### ACL Enforcement

```python
# core/knowledge/acl.py
class DocumentACL:
    async def check_access(self, user: dict, document_id: str, permission: str = "read") -> bool:
        """Check if user has permission to access document."""
        
        # Admin bypass
        if "admin" in user.get("roles", []):
            return True
        
        # Check direct user permission
        if await self._check_user_permission(user["user_id"], document_id, permission):
            return True
        
        # Check group permissions
        for group in user.get("groups", []):
            if await self._check_group_permission(group, document_id, permission):
                return True
        
        # Check role permissions
        for role in user.get("roles", []):
            if await self._check_role_permission(role, document_id, permission):
                return True
        
        return False
    
    async def filter_search_results(self, user: dict, results: List[dict]) -> List[dict]:
        """Filter search results based on user's document access."""
        accessible = []
        for result in results:
            if await self.check_access(user, result["document_id"]):
                accessible.append(result)
        return accessible
```

### 3.7 Retrieval Auditing

#### Audit Trail

```sql
-- Retrieval audit log
CREATE TABLE retrieval_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(255) NOT NULL,
    query_text TEXT NOT NULL,
    query_embedding_hash VARCHAR(64),
    documents_retrieved JSONB,  -- [{doc_id, score, accessed}]
    documents_used_in_response JSONB,
    response_generated BOOLEAN,
    retrieval_time_ms INT,
    total_tokens_used INT,
    session_id VARCHAR(36),
    ip_address INET,
    
    INDEX idx_retrieval_user (user_id),
    INDEX idx_retrieval_timestamp (timestamp)
);

-- Document access frequency
CREATE MATERIALIZED VIEW document_access_stats AS
SELECT 
    doc->>'doc_id' as document_id,
    COUNT(*) as access_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG((doc->>'score')::float) as avg_relevance_score
FROM retrieval_audit,
     jsonb_array_elements(documents_retrieved) as doc
GROUP BY doc->>'doc_id';
```

---

## Layer 4 — Application Layer

The Application Layer provides microservices for specific use cases, each following established patterns.

### 4.1 Microservices Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Application Microservices                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Service Registry                         ││
│  │                                                              ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     ││
│  │  │ rag-chat      │ │ policy-assist │ │ cvm-insight   │     ││
│  │  │ :8010         │ │ :8011         │ │ :8012         │     ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘     ││
│  │                                                              ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     ││
│  │  │ doc-validator │ │ ticket-anlyz  │ │ custom-svc    │     ││
│  │  │ :8013         │ │ :8014         │ │ :801X         │     ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘     ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Shared Services                           ││
│  │                                                              ││
│  │  Gateway │ Auth │ Knowledge │ Inference │ Audit │ Metrics   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 RAG Chat Pattern

Standard pattern for document-grounded Q&A.

```python
# Pattern: RAG Chat Service
class RAGChatService:
    """
    RAG Chat Pattern Implementation
    
    Flow:
    1. Receive query
    2. Retrieve relevant documents (with ACL)
    3. Build context with retrieved chunks
    4. Generate response with citations
    5. Log retrieval audit
    """
    
    async def chat(self, query: str, user: dict, conversation_id: str) -> dict:
        # 1. Embed query
        query_embedding = await self.embedder.embed_query(query)
        
        # 2. Retrieve with ACL filtering
        raw_results = await self.vector_store.search(query_embedding, top_k=10)
        results = await self.acl.filter_search_results(user, raw_results)
        
        # 3. Build context
        context = self.build_context(results)
        
        # 4. Get conversation history
        history = await self.get_history(conversation_id)
        
        # 5. Generate response
        response = await self.llm.generate(
            system_prompt=RAG_SYSTEM_PROMPT,
            context=context,
            history=history,
            query=query
        )
        
        # 6. Extract citations
        citations = self.extract_citations(response, results)
        
        # 7. Audit log
        await self.audit.log_retrieval(user, query, results, response)
        
        return {
            "response": response,
            "citations": citations,
            "sources": [r["metadata"] for r in results[:5]]
        }
```

### 4.3 Policy Assistant Pattern

Pattern for policy/compliance Q&A with strict citation requirements.

```python
# Pattern: Policy Assistant Service
class PolicyAssistantService:
    """
    Policy Assistant Pattern Implementation
    
    Characteristics:
    - Strict citation required for every claim
    - Confidence scoring
    - Escalation for uncertain answers
    - Audit trail for compliance
    """
    
    SYSTEM_PROMPT = """You are a policy assistant. 
    CRITICAL RULES:
    1. ONLY answer from provided policy documents
    2. ALWAYS cite specific policy section numbers
    3. If information is not in policies, say "I cannot find this in current policies"
    4. Rate your confidence: HIGH (direct quote), MEDIUM (inference), LOW (uncertain)
    """
    
    async def query(self, question: str, user: dict) -> dict:
        # Retrieve from policy namespace only
        results = await self.retrieve(
            question, 
            namespace="policies",
            user=user
        )
        
        if not results:
            return {
                "answer": "I cannot find relevant policies for this question.",
                "confidence": "N/A",
                "action": "escalate_to_compliance",
                "sources": []
            }
        
        # Generate with strict citation prompt
        response = await self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            context=self.format_policy_context(results),
            question=question
        )
        
        # Parse confidence and citations
        parsed = self.parse_response(response)
        
        # Auto-escalate low confidence
        if parsed["confidence"] == "LOW":
            await self.escalate(question, user, parsed)
        
        return parsed
```

### 4.4 CVM Insight Pattern

Pattern for data analysis and insights from structured data.

```python
# Pattern: CVM Insight Service
class CVMInsightService:
    """
    CVM (Customer Value Management) Insight Pattern
    
    Characteristics:
    - SQL generation for data queries
    - Chart/visualization recommendations
    - Trend analysis
    - Anomaly detection
    """
    
    async def analyze(self, question: str, user: dict) -> dict:
        # 1. Determine if SQL is needed
        intent = await self.classify_intent(question)
        
        if intent == "data_query":
            # Generate and execute SQL
            sql = await self.generate_sql(question, user)
            results = await self.execute_sql(sql, user)
            
            # Generate insight from data
            insight = await self.generate_insight(question, results)
            
            return {
                "type": "data_insight",
                "sql_query": sql,
                "data": results,
                "insight": insight,
                "visualization": self.recommend_chart(results)
            }
        
        elif intent == "trend_analysis":
            return await self.analyze_trends(question, user)
        
        else:
            # Fall back to RAG
            return await self.rag_fallback(question, user)
```

### 4.5 Document Validator Pattern

Pattern for content validation and quality assurance.

```python
# Pattern: Document Validator Service
class DocumentValidatorService:
    """
    Document Validator Pattern
    
    Characteristics:
    - Multi-stage validation pipeline
    - Rule-based + LLM validation
    - Severity classification
    - Remediation suggestions
    """
    
    async def validate(self, document: str, doc_type: str) -> dict:
        issues = []
        
        # Stage 1: Format validation
        format_issues = await self.validate_format(document, doc_type)
        issues.extend(format_issues)
        
        # Stage 2: Rule-based checks
        rule_issues = await self.apply_rules(document, doc_type)
        issues.extend(rule_issues)
        
        # Stage 3: LLM quality check
        if doc_type in ["policy", "legal", "technical"]:
            quality_issues = await self.llm_quality_check(document, doc_type)
            issues.extend(quality_issues)
        
        # Stage 4: Fact-check against knowledge base
        if self.fact_check_enabled:
            fact_issues = await self.fact_check(document)
            issues.extend(fact_issues)
        
        return {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "score": self.calculate_score(issues),
            "issues": issues,
            "suggestions": self.generate_suggestions(issues)
        }
```

### 4.6 Service Template

```python
# Template for new application services
# services/my_service/service.py

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from shared.auth import get_current_user
from shared.llm import LLMClient
from shared.knowledge import KnowledgeService
from shared.audit import AuditLogger

app = FastAPI(title="My Service", version="1.0.0")

class MyService:
    def __init__(self):
        self.llm = LLMClient()
        self.knowledge = KnowledgeService()
        self.audit = AuditLogger()
    
    async def process(self, request: dict, user: dict) -> dict:
        """Main processing logic."""
        # 1. Retrieve context (if needed)
        # 2. Process with LLM
        # 3. Post-process results
        # 4. Audit log
        pass

service = MyService()

class ProcessRequest(BaseModel):
    query: str
    options: dict = {}

@app.post("/process")
async def process(request: ProcessRequest, user = Depends(get_current_user)):
    return await service.process(request.dict(), user)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}
```

---

## Layer 5 — Operations Layer

The Operations Layer ensures production reliability, monitoring, and disaster recovery.

### 5.1 Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Grafana Dashboards                      ││
│  │                                                              ││
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        ││
│  │  │ Overview     │ │ GPU Metrics  │ │ LLM Perf     │        ││
│  │  │ Dashboard    │ │ Dashboard    │ │ Dashboard    │        ││
│  │  └──────────────┘ └──────────────┘ └──────────────┘        ││
│  │                                                              ││
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        ││
│  │  │ RAG Metrics  │ │ User Activity│ │ Alerts       │        ││
│  │  │ Dashboard    │ │ Dashboard    │ │ Dashboard    │        ││
│  │  └──────────────┘ └──────────────┘ └──────────────┘        ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                              ▲                                   │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                       Prometheus                             ││
│  │                                                              ││
│  │  Scrape Targets:                                            ││
│  │  • FastAPI Gateway (/metrics)                               ││
│  │  • vLLM Servers (/metrics)                                  ││
│  │  • Node Exporter (system metrics)                           ││
│  │  • DCGM Exporter (GPU metrics)                              ││
│  │  • PostgreSQL Exporter                                      ││
│  │                                                              ││
│  │  Retention: 30 days                                         ││
│  │  Storage: 100GB SSD                                         ││
│  └─────────────────────────────────────────────────────────────┘│
│                              ▲                                   │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Alertmanager                             ││
│  │                                                              ││
│  │  Routes:                                                     ││
│  │  • Critical → PagerDuty + Slack                             ││
│  │  • Warning → Slack                                          ││
│  │  • Info → Email digest                                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Dashboards

**1. System Overview Dashboard**
```yaml
panels:
  - title: "Request Rate"
    query: rate(http_requests_total[5m])
  - title: "Error Rate"
    query: rate(http_requests_total{status=~"5.."}[5m])
  - title: "P99 Latency"
    query: histogram_quantile(0.99, http_request_duration_seconds_bucket)
  - title: "Active Users"
    query: count(count by (user_id) (http_requests_total[1h]))
```

**2. GPU Performance Dashboard**
```yaml
panels:
  - title: "GPU Utilization"
    query: DCGM_FI_DEV_GPU_UTIL
  - title: "GPU Memory Used"
    query: DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100
  - title: "GPU Temperature"
    query: DCGM_FI_DEV_GPU_TEMP
  - title: "Power Usage"
    query: DCGM_FI_DEV_POWER_USAGE
```

**3. LLM Performance Dashboard**
```yaml
panels:
  - title: "Tokens/Second"
    query: rate(llm_tokens_output_total[1m])
  - title: "Queue Depth"
    query: llm_queue_size
  - title: "Time to First Token"
    query: histogram_quantile(0.95, llm_ttft_seconds_bucket)
  - title: "Request Success Rate"
    query: rate(llm_requests_total{status="success"}[5m]) / rate(llm_requests_total[5m])
```

#### Alert Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: critical
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: GPUMemoryExhausted
        expr: DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL > 0.95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "GPU memory nearly exhausted"
          
      - alert: LLMServiceDown
        expr: up{job="vllm"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "LLM service is down"

  - name: warning
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 5
        for: 10m
        labels:
          severity: warning
          
      - alert: QueueBacklog
        expr: llm_queue_size > 100
        for: 5m
        labels:
          severity: warning
```

### 5.2 Backup & Recovery

#### Backup Schedule

| Data | Frequency | Retention | Storage |
|------|-----------|-----------|---------|
| PostgreSQL | Hourly | 7 days | S3/MinIO |
| FAISS Indexes | Daily | 30 days | S3/MinIO |
| Model Weights | On change | Forever | S3/MinIO |
| Audit Logs | Daily | 1 year | S3/Glacier |
| Config Files | On change | 90 days | Git + S3 |

#### Backup Scripts

```bash
#!/bin/bash
# scripts/backup.sh

# PostgreSQL backup
pg_dump -Fc goai_db > /backup/postgres/goai_$(date +%Y%m%d_%H%M).dump

# FAISS index backup
tar -czf /backup/faiss/indexes_$(date +%Y%m%d).tar.gz /data/indexes/

# Upload to S3
aws s3 sync /backup/ s3://goai-backups/$(hostname)/

# Cleanup old local backups
find /backup -mtime +7 -delete
```

#### Restore Procedure

```bash
#!/bin/bash
# scripts/restore.sh

# 1. Stop services
docker-compose down

# 2. Download backup
aws s3 cp s3://goai-backups/latest/postgres.dump /restore/
aws s3 cp s3://goai-backups/latest/indexes.tar.gz /restore/

# 3. Restore PostgreSQL
pg_restore -d goai_db /restore/postgres.dump

# 4. Restore FAISS indexes
tar -xzf /restore/indexes.tar.gz -C /data/

# 5. Restart services
docker-compose up -d

# 6. Verify
curl http://localhost:8000/health
```

### 5.3 Blue/Green Model Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                  Blue/Green Model Deployment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current State: BLUE active                                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Load Balancer                           ││
│  │                                                              ││
│  │           Traffic: 100% ──▶ BLUE                            ││
│  │                    0% ──▶ GREEN                             ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                      │                   │                       │
│                      ▼                   ▼                       │
│  ┌────────────────────────┐  ┌────────────────────────┐        │
│  │      BLUE (Active)     │  │     GREEN (Standby)    │        │
│  │                        │  │                        │        │
│  │  Model: Llama-70B v1   │  │  Model: Llama-70B v2   │        │
│  │  Status: Serving       │  │  Status: Ready         │        │
│  │  Port: 8001            │  │  Port: 8002            │        │
│  │                        │  │                        │        │
│  └────────────────────────┘  └────────────────────────┘        │
│                                                                  │
│  Deployment Steps:                                               │
│  1. Deploy new model to GREEN                                   │
│  2. Health check GREEN                                          │
│  3. Canary: Route 10% to GREEN                                 │
│  4. Monitor metrics for 30min                                   │
│  5. If OK: Route 100% to GREEN                                 │
│  6. Keep BLUE for 24h (rollback ready)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Deployment Script

```bash
#!/bin/bash
# scripts/deploy_model.sh

MODEL_NAME=$1
NEW_VERSION=$2
CANARY_PERCENT=${3:-10}

echo "Deploying $MODEL_NAME version $NEW_VERSION"

# 1. Deploy to GREEN
docker-compose -f docker-compose.green.yml up -d

# 2. Wait for health
echo "Waiting for GREEN to be healthy..."
until curl -s http://green:8002/health | grep -q "ok"; do
    sleep 5
done

# 3. Run smoke tests
python scripts/smoke_test.py --endpoint http://green:8002

# 4. Canary deployment
echo "Starting canary with $CANARY_PERCENT% traffic"
update_load_balancer --green-weight $CANARY_PERCENT

# 5. Monitor
echo "Monitoring for 30 minutes..."
python scripts/monitor_canary.py --duration 30m --threshold 0.01

# 6. Full cutover
if [ $? -eq 0 ]; then
    echo "Canary successful, switching to GREEN"
    update_load_balancer --green-weight 100
    echo "Deployment complete!"
else
    echo "Canary failed, rolling back"
    update_load_balancer --green-weight 0
    exit 1
fi
```

### 5.4 Rollback Process

```yaml
# Rollback Runbook
rollback:
  triggers:
    - error_rate > 5% for 5 minutes
    - p99_latency > 10s for 5 minutes
    - model_health_check failing
    
  automatic:
    enabled: true
    max_errors: 100
    window: 5m
    
  manual_steps:
    1: "Verify issue is model-related (not infrastructure)"
    2: "Execute: ./scripts/rollback.sh"
    3: "Verify BLUE is healthy"
    4: "Update load balancer to 100% BLUE"
    5: "Notify team in #incidents"
    6: "Create post-mortem ticket"
    
  rollback_script: |
    #!/bin/bash
    echo "Rolling back to BLUE"
    update_load_balancer --blue-weight 100 --green-weight 0
    docker-compose -f docker-compose.green.yml down
    echo "Rollback complete"
```

### 5.5 Disaster Recovery

#### DR Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Disaster Recovery Setup                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────┐  ┌───────────────────────────┐  │
│  │     PRIMARY (DC1)         │  │     DR SITE (DC2)         │  │
│  │                           │  │                           │  │
│  │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │  │
│  │  │ GPU Cluster         │  │  │  │ GPU Cluster         │  │  │
│  │  │ (Active)            │──┼──┼─▶│ (Warm Standby)      │  │  │
│  │  └─────────────────────┘  │  │  └─────────────────────┘  │  │
│  │                           │  │                           │  │
│  │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │  │
│  │  │ PostgreSQL          │  │  │  │ PostgreSQL          │  │  │
│  │  │ (Primary)           │──┼──┼─▶│ (Replica)           │  │  │
│  │  └─────────────────────┘  │  │  └─────────────────────┘  │  │
│  │                           │  │         Streaming         │  │
│  │  ┌─────────────────────┐  │  │        Replication       │  │
│  │  │ FAISS Indexes       │──┼──┼─▶  (Daily Sync)          │  │
│  │  └─────────────────────┘  │  │                           │  │
│  │                           │  │                           │  │
│  └───────────────────────────┘  └───────────────────────────┘  │
│                                                                  │
│  RTO: 4 hours | RPO: 1 hour                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### DR Runbook

```yaml
# DR Failover Procedure
dr_failover:
  pre_requisites:
    - Confirm primary is unrecoverable
    - Get approval from DR lead
    - Notify stakeholders
    
  steps:
    1:
      action: "Promote PostgreSQL replica"
      command: "pg_ctl promote -D /var/lib/postgresql/data"
      verify: "SELECT pg_is_in_recovery();" # Should return false
      
    2:
      action: "Start GPU services"
      command: "docker-compose -f docker-compose.dr.yml up -d"
      verify: "curl http://localhost:8001/health"
      
    3:
      action: "Load latest FAISS index"
      command: "./scripts/restore_faiss.sh"
      verify: "curl http://localhost:8000/api/v1/rag/stats"
      
    4:
      action: "Update DNS"
      command: "aws route53 change-resource-record-sets..."
      verify: "dig goai.company.com"
      
    5:
      action: "Verify all services"
      command: "./scripts/dr_smoke_test.sh"
      verify: "All endpoints returning 200"
      
    6:
      action: "Notify users"
      command: "Send status page update"
      
  rollback:
    - "If DR fails, engage vendor support"
    - "Document all issues for post-mortem"
```

---

## Testing Use Cases

The platform provides multiple ways to test and validate new use cases.

### Quick API Testing

Test features immediately without additional setup:

```bash
# 1. Health Check
curl http://localhost:8000/health

# 2. Test Agent Tools
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculator", "arguments": {"expression": "100 + 200"}}'

# 3. Ingest a Document
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content": "Your document content here", "filename": "doc.txt"}'

# 4. Query with RAG
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the document say?", "top_k": 5}'
```

### Create Evaluation Datasets

Define test cases for systematic quality validation:

```bash
curl -X POST http://localhost:8000/api/v1/evals/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Use Case Tests",
    "description": "Test cases for my new use case",
    "test_cases": [
      {"query": "Question 1?", "expected": "Expected answer 1", "tags": ["category1"]},
      {"query": "Question 2?", "expected": "Expected answer 2", "tags": ["category2"]}
    ]
  }'
```

### Create Webhook Triggers

Set up event-driven automation for your use case:

```bash
curl -X POST http://localhost:8000/api/v1/triggers/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Use Case Handler",
    "description": "Trigger actions for my use case",
    "action": "rag_query",
    "action_params": {"top_k": 5}
  }'
```

### Structured Use Case Development

For production use cases, follow this folder structure:

```
use_cases/
└── my_use_case/
    ├── intent.yaml        # Business requirements & scope
    ├── workflow.yaml      # Technical workflow definition
    ├── test_use_case.py   # Automated test script
    └── README.md          # Documentation
```

**Example: `intent.yaml`**
```yaml
use_case:
  name: "Document Q&A"
  id: "document-qa"
  version: "1.0.0"
  
  problem: |
    Users need quick answers from company documents.
    
  solution: |
    RAG-powered Q&A with document ingestion and retrieval.
    
  success_metrics:
    - metric: "Response time"
      target: "< 3 seconds"
    - metric: "Accuracy"
      target: "90%+"
      
  test_scenarios:
    - name: "Basic Q&A"
      input: "What is the vacation policy?"
      expected_behavior: "Return relevant policy with citation"
```

**Example: `test_use_case.py`**
```python
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_use_case():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Ingest test documents
        response = await client.post(f"{BASE_URL}/ingest/text", json={
            "content": "Your test document content",
            "filename": "test.txt"
        })
        print(f"Ingested: {response.json()}")
        
        # 2. Test retrieval
        response = await client.post(f"{BASE_URL}/retrieve/", json={
            "query": "Your test query",
            "top_k": 3
        })
        print(f"Retrieved: {len(response.json().get('documents', []))} documents")
        
        # 3. Test RAG query
        response = await client.post(f"{BASE_URL}/rag/query", json={
            "query": "Your test question?"
        })
        print(f"Answer: {response.json().get('answer', 'No answer')}")

if __name__ == "__main__":
    asyncio.run(test_use_case())
```

### Run Tests

```bash
# Run a specific use case test
python use_cases/document_qa/test_use_case.py

# Run all tests with pytest
pytest tests/ -v
```

### Available Built-in Tools

| Tool | Description | Example |
|------|-------------|---------|
| `calculator` | Math expressions | `{"expression": "100 * 2.5"}` |
| `get_datetime` | Current date/time | `{}` |
| `web_search` | Web search via DuckDuckGo | `{"query": "Python FastAPI", "num_results": 5}` |
| `execute_python` | Run Python code (sandboxed) | `{"code": "print(2+2)"}` |
| `fetch_url` | Fetch URL content | `{"url": "https://example.com"}` |
| `parse_json` | Parse JSON string | `{"json_string": "{\"key\": \"value\"}"}` |

### Pre-built Evaluation Datasets

| Dataset | Description | Test Cases |
|---------|-------------|------------|
| `qa_general` | Basic Q&A scenarios | 3 |
| `rag_eval` | RAG with context | 2 |
| `safety` | Safety evaluation | 2 |

---

## Implementation Guide

### Quick Start (Development)

```bash
# Clone repository
git clone https://github.com/org/goai-platform.git
cd goai-platform

# Setup environment
cp .env.example .env
# Edit .env with your API keys (see below)

# Install dependencies
pip install -r requirements.txt

# Start backend
uvicorn main:app --reload --port 8000

# Start frontend (in another terminal)
cd ui/console && npm install && npm run dev

# Test the installation
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agents/tools
```

### Environment Variables (Required)

```bash
# .env file - minimum required
OPENAI_API_KEY=sk-...            # For LLM features
JWT_SECRET=your-256-bit-secret   # For authentication

# Optional providers
ANTHROPIC_API_KEY=...            # For Claude models
OLLAMA_HOST=http://localhost:11434  # For local models
```

### Verify Installation

```bash
# Test agent tools (no API key needed)
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculator", "arguments": {"expression": "2+2"}}'

# Test RAG system
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content": "Test document content", "filename": "test.txt"}'
```

### Production Deployment

```bash
# 1. Setup infrastructure (Terraform)
cd infrastructure/
terraform init
terraform apply

# 2. Deploy Keycloak
kubectl apply -f k8s/keycloak/

# 3. Deploy GPU nodes
kubectl apply -f k8s/gpu-nodes/

# 4. Deploy vLLM
kubectl apply -f k8s/vllm/

# 5. Deploy platform
kubectl apply -f k8s/platform/

# 6. Configure monitoring
kubectl apply -f k8s/monitoring/

# 7. Run health checks
./scripts/health_check.sh
```

---

## Appendix

### A. Environment Variables

```bash
# Core
OPENAI_API_KEY=sk-...          # Fallback only
JWT_SECRET=...                  # 256-bit random

# Keycloak
KEYCLOAK_URL=https://auth.company.com
KEYCLOAK_REALM=goai
KEYCLOAK_CLIENT_ID=goai-platform
KEYCLOAK_SECRET=...

# Database
POSTGRES_HOST=postgres.internal
POSTGRES_DB=goai
POSTGRES_USER=goai
POSTGRES_PASSWORD=...

# Redis
REDIS_HOST=redis.internal
REDIS_PASSWORD=...

# vLLM
VLLM_70B_ENDPOINT=http://vllm-70b:8001
VLLM_8B_ENDPOINT=http://vllm-8b:8002
VLLM_API_KEY=...

# Storage
S3_BUCKET=goai-storage
S3_ENDPOINT=https://s3.company.com
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### B. API Endpoints Summary

#### Core Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | ❌ | Health check |
| `/config` | GET | ❌ | Configuration status |
| `/metrics` | GET | ❌ | Prometheus metrics |

#### LLM Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/llm/complete` | POST | ✅ | Text completion |
| `/api/v1/llm/chat` | POST | ✅ | Chat completion |
| `/api/v1/llm/stream` | POST | ✅ | Streaming generation |
| `/api/v1/llm/providers` | GET | ✅ | List LLM providers |

#### RAG Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/rag/query` | POST | ✅ | Query with RAG |
| `/api/v1/rag/ask` | POST | ✅ | Quick Q&A |
| `/api/v1/rag/chat` | POST | ✅ | Conversational RAG |
| `/api/v1/rag/documents` | GET | ✅ | List documents |
| `/api/v1/rag/stats` | GET | ✅ | RAG statistics |
| `/api/v1/rag/conversation` | POST | ✅ | Create conversation |
| `/api/v1/ingest/text` | POST | ✅ | Ingest text |
| `/api/v1/ingest/document` | POST | ✅ | Ingest document |

#### Agent Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/agents/run` | POST | ✅ | Run agent |
| `/api/v1/agents/plan-execute` | POST | ✅ | Plan-and-Execute agent |
| `/api/v1/agents/plan-only` | POST | ✅ | Create plan without executing |
| `/api/v1/agents/tools` | GET | ✅ | List available tools |
| `/api/v1/agents/tools/execute` | POST | ✅ | Execute tool directly |
| `/api/v1/agents/ask` | POST | ✅ | Quick agent query |

#### Memory Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/memory` | GET | ✅ | List memories |
| `/api/v1/memory` | POST | ✅ | Create memory |
| `/api/v1/memory/{id}` | GET | ✅ | Get memory |
| `/api/v1/memory/{id}` | PUT | ✅ | Update memory |
| `/api/v1/memory/{id}` | DELETE | ✅ | Delete memory |

#### AI Evaluations Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/evals/datasets` | GET | ✅ | List evaluation datasets |
| `/api/v1/evals/datasets` | POST | ✅ | Create dataset |
| `/api/v1/evals/metrics` | GET | ✅ | List evaluation metrics |
| `/api/v1/evals/run` | POST | ✅ | Run evaluation |

#### MCP Protocol Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/mcp/info` | GET | ✅ | Server info |
| `/api/v1/mcp/tools` | GET | ✅ | List MCP tools |
| `/api/v1/mcp/execute` | POST | ✅ | Execute via MCP |
| `/api/v1/mcp/stats` | GET | ✅ | Execution stats |

#### Triggers/Webhooks Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/triggers/webhooks` | GET | ✅ | List webhooks |
| `/api/v1/triggers/webhooks` | POST | ✅ | Create webhook |
| `/api/v1/triggers/event-types` | GET | ✅ | List event types |
| `/api/v1/triggers/webhook/{id}/trigger` | POST | ✅ | Trigger webhook |

#### Orchestrator Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/orchestrator/workflows` | GET | ✅ | List workflows |
| `/api/v1/orchestrator/workflows/execute` | POST | ✅ | Execute workflow |
| `/api/v1/orchestrator/actions` | GET | ✅ | List available actions |

#### Other Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/prompts` | CRUD | ✅ | Prompt library |
| `/api/v1/feedback` | CRUD | ✅ | User feedback |
| `/api/v1/telemetry/overview` | GET | ✅ | Telemetry data |
| `/api/v1/performance/stats` | GET | ✅ | Performance stats |
| `/api/v1/auth/login` | POST | ❌ | Login |
| `/api/v1/admin/users` | CRUD | 🔒 | User management |

### C. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | Dec 2025 | Added AI Evaluations, MCP Protocol, Triggers/Webhooks |
| 1.1.0 | Dec 2025 | Enhanced agent tools, memory system, prompt library |
| 1.0.0 | Nov 2025 | Initial sovereign release |

---

## Contact & Support

- **Documentation**: https://docs.goai.company.com
- **Issues**: https://github.com/org/goai-platform/issues
- **Security**: security@company.com

---

**GoAI Sovereign AI Platform v1** — Enterprise AI Under Your Control 🏛️

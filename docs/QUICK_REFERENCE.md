<![CDATA[# 🚀 GoAI Platform — Quick Reference

> **Your go-to cheat sheet for building with GoAI**

---

## ⚡ 60-Second Start

```bash
# Start backend
cd goai-platform-v1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Test it works
curl http://localhost:8000/health
```

**Done!** Open http://localhost:8000/docs for interactive API.

---

## 🏛️ Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  L5  │  📊 Operations   │  Monitoring • Backups • Deployment   │
├─────────────────────────────────────────────────────────────────┤
│  L4  │  🎯 Applications │  RAG Chat • Agents • Custom Services │
├─────────────────────────────────────────────────────────────────┤
│  L3  │  📚 Knowledge    │  Ingestion • Chunking • Vector Store │
├─────────────────────────────────────────────────────────────────┤
│  L2  │  🛡️ Gateway      │  Auth • Rate Limits • Audit Logs    │
├─────────────────────────────────────────────────────────────────┤
│  L1  │  ⚡ Inference    │  LLM Router • OpenAI • Ollama • vLLM │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Copy-Paste API Examples

### Agent Tools (No API Key Needed)

```bash
# 🧮 Calculator
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculator", "arguments": {"expression": "(100 * 25) + 500"}}'

# 📅 Current DateTime
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_datetime", "arguments": {}}'

# 🔍 Web Search
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "web_search", "arguments": {"query": "FastAPI tutorial", "num_results": 3}}'

# 📜 List All Tools
curl http://localhost:8000/api/v1/agents/tools
```

### RAG Pipeline

```bash
# 📄 Ingest Document
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content": "Your document text here", "filename": "doc.txt"}'

# 🔍 Query Documents
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is in the document?", "top_k": 5}'

# 📊 Check Stats
curl http://localhost:8000/api/v1/rag/stats
```

### Plan-and-Execute Agent (Requires API Key)

```bash
# Full execution
curl -X POST http://localhost:8000/api/v1/agents/plan-execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Calculate total cost of 15 items at $24.99 with 8% tax"}'

# Preview plan only
curl -X POST "http://localhost:8000/api/v1/agents/plan-only?task=Build+a+web+scraper"
```

### 🎭 Agent Templates

```bash
# List all templates
curl http://localhost:8000/api/v1/agents/templates

# Run the writer template
curl -X POST http://localhost:8000/api/v1/agents/templates/writer/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a tagline for a coffee shop", "template_id": "writer"}'

# Run the researcher template
curl -X POST http://localhost:8000/api/v1/agents/templates/researcher/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Research AI trends in 2025", "template_id": "researcher"}'
```

**Available Templates:** `researcher`, `data_analyst`, `code_reviewer`, `code_generator`, `writer`, `summarizer`, `customer_support`, `sql_expert`, `planner`, `research_team`, `code_review_team`

### 🛡️ Human-in-the-Loop Approvals

```bash
# Create approval request
curl -X POST http://localhost:8000/api/v1/approvals/requests \
  -H "Content-Type: application/json" \
  -d '{"action": "Send email to customers", "category": "send_email", "agent_id": "marketing-agent"}'

# List pending approvals
curl http://localhost:8000/api/v1/approvals/pending

# Approve request
curl -X POST http://localhost:8000/api/v1/approvals/requests/{id}/approve \
  -H "Content-Type: application/json" \
  -d '{"reason": "Approved", "responded_by": "admin"}'

# Check if approval required
curl -X POST http://localhost:8000/api/v1/approvals/check \
  -H "Content-Type: application/json" \
  -d '{"category": "payment"}'
```

### 👁️ Observability Dashboard

```bash
# Open visual dashboard
open http://localhost:8000/api/v1/observability/dashboard/html

# Get dashboard data
curl http://localhost:8000/api/v1/observability/dashboard

# List traces
curl http://localhost:8000/api/v1/observability/traces

# Cost breakdown
curl http://localhost:8000/api/v1/observability/stats/cost

# Tool usage stats
curl http://localhost:8000/api/v1/observability/stats/tools
```

### 🛡️ AI Guardrails

```bash
# Check user input for safety (prompt injection, harmful content)
curl -X POST http://localhost:8000/api/v1/guardrails/check/input \
  -H "Content-Type: application/json" \
  -d '{"content": "User message here"}'

# Check AI output (PII redaction, profanity filter)
curl -X POST http://localhost:8000/api/v1/guardrails/check/output \
  -H "Content-Type: application/json" \
  -d '{"content": "Response with SSN 123-45-6789"}'

# Check tool permissions
curl -X POST http://localhost:8000/api/v1/guardrails/check/tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "execute_python", "arguments": {}}'

# List guardrail rules
curl http://localhost:8000/api/v1/guardrails/rules

# Get guardrail stats
curl http://localhost:8000/api/v1/guardrails/stats
```

### Webhooks

```bash
# Create webhook
curl -X POST http://localhost:8000/api/v1/triggers/webhooks \
  -H "Content-Type: application/json" \
  -d '{"name": "My Hook", "action": "rag_query", "action_params": {"top_k": 5}}'

# List webhooks
curl http://localhost:8000/api/v1/triggers/webhooks
```

### AI Evaluations

```bash
# List metrics
curl http://localhost:8000/api/v1/evals/metrics

# Create dataset
curl -X POST http://localhost:8000/api/v1/evals/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Tests",
    "test_cases": [{"query": "Q?", "expected": "A", "tags": ["test"]}]
  }'
```

---

## 🔧 Building New Features

### 1️⃣ Create Engine Module

```python
# modules/my_feature/engine.py
from core.llm import llm_router

class MyEngine:
    async def process(self, data: str) -> dict:
        response = await llm_router.run(
            model_id="gpt-4o-mini",
            messages=[{"role": "user", "content": data}]
        )
        return {"result": response["content"]}

my_engine = MyEngine()
```

### 2️⃣ Create API Endpoint

```python
# api/v1/my_feature.py
from fastapi import APIRouter
from modules.my_feature import my_engine

router = APIRouter()

@router.post("/process")
async def process(data: str):
    return await my_engine.process(data)
```

### 3️⃣ Register in main.py

```python
from api.v1 import my_feature
app.include_router(my_feature.router, prefix="/api/v1/my-feature", tags=["My Feature"])
```

### 4️⃣ Create UI Page (Optional)

```tsx
// ui/console/src/pages/MyFeaturePage.tsx
export default function MyFeaturePage() {
  return <div className="p-8">My Feature UI</div>;
}
```

---

## 📡 All 32 API Modules

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Core** | `/health`, `/docs` | Health & documentation |
| **LLM** | `/api/v1/llm/*` | Chat, completion, providers |
| **Stream** | `/api/v1/stream/*` | SSE streaming |
| **RAG** | `/api/v1/rag/*` | Query, chat, documents |
| **Ingest** | `/api/v1/ingest/*` | Text & file ingestion |
| **Retrieve** | `/api/v1/retrieve/*` | Semantic search |
| **Agents** | `/api/v1/agents/*` | Run, tools, plan-execute, **templates** |
| **Multi-Agent** | `/api/v1/multi-agent/*` | Collaboration patterns |
| **Memory** | `/api/v1/memory/*` | User memories |
| **Sentiment** | `/api/v1/sentiment/*` | Text sentiment analysis |
| **SQL Agent** | `/api/v1/sql/*` | Natural language to SQL |
| **Validator** | `/api/v1/validator/*` | Document validation |
| **Orchestrator** | `/api/v1/orchestrator/*` | YAML workflows |
| **Evals** | `/api/v1/evals/*` | AI quality evaluation |
| **MCP** | `/api/v1/mcp/*` | Model Context Protocol |
| **Triggers** | `/api/v1/triggers/*` | Webhooks & events |
| **Guardrails** | `/api/v1/guardrails/*` | **AI safety guardrails** |
| **Approvals** | `/api/v1/approvals/*` | **Human-in-the-Loop** |
| **Observability** | `/api/v1/observability/*` | **Agent monitoring** |
| **Prompts** | `/api/v1/prompts/*` | Prompt library |
| **Feedback** | `/api/v1/feedback/*` | User feedback |
| **Auth** | `/api/v1/auth/*` | Authentication |
| **Upload** | `/api/v1/upload/*` | File uploads |
| **Export** | `/api/v1/export/*` | Data export |
| **Telemetry** | `/api/v1/telemetry/*` | Metrics & traces |
| **Performance** | `/api/v1/performance/*` | Cache & stats |
| **EBC Tickets** | `/api/v1/ebc-tickets/*` | Ticket management |
| **Customer KYC** | `/api/v1/kyc/*` | KYC verification |
| **OCR** | `/api/v1/ocr/*` | Document scanning |
| **Activity** | `/api/v1/activity/*` | Activity logging |
| **Meeting Notes** | `/api/v1/meeting-notes/*` | **Meeting summarization** |

---

## 🔑 Environment Variables

```bash
# Required for LLM features
OPENAI_API_KEY=sk-...

# Optional providers
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://localhost:11434

# Auth
JWT_SECRET=your-256-bit-secret
```

---

## 📊 Available Tools

| Tool | Arguments | Example |
|------|-----------|---------|
| `calculator` | `expression` | `{"expression": "sqrt(144) * 2"}` |
| `get_datetime` | (none) | `{}` |
| `web_search` | `query`, `num_results` | `{"query": "Python", "num_results": 5}` |
| `execute_python` | `code` | `{"code": "print(2+2)"}` |
| `fetch_url` | `url` | `{"url": "https://example.com"}` |
| `parse_json` | `json_string` | `{"json_string": "{\"a\": 1}"}` |

---

## 🎭 Agent Templates

| Template | Pattern | Best For |
|----------|---------|----------|
| `researcher` | Plan-Execute | Research with web search |
| `data_analyst` | Plan-Execute | Data analysis & statistics |
| `code_reviewer` | Simple | Code review & security |
| `code_generator` | Simple | Writing clean code |
| `writer` | Simple | Content creation |
| `summarizer` | Simple | Document summarization |
| `customer_support` | Simple | Customer service |
| `sql_expert` | Simple | SQL queries |
| `planner` | Plan-Execute | Project planning |
| `research_team` | Multi-Agent | Team research |
| `code_review_team` | Multi-Agent | Multi-perspective review |

---

## 🔄 RAG Modes

| Mode | Use Case | Description |
|------|----------|-------------|
| `simple` | Basic Q&A | Direct query → retrieve → generate |
| `conversational` | Multi-turn | Includes chat history |
| `multi_query` | Complex questions | Generates multiple queries |
| `step_back` | Abstract reasoning | Asks broader questions first |
| `hyde` | Semantic search | Hypothetical answer generation |

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare policies", "mode": "multi_query"}'
```

---

## 📁 Project Structure

```
goai-platform-v1/
├── main.py              # Entry point
├── api/v1/              # REST endpoints
├── core/                # Infrastructure (LLM, Vector, Auth)
├── modules/             # Feature modules (Agents, RAG, Evals)
├── ui/console/          # React frontend
├── use_cases/           # Example implementations
├── data/                # SQLite databases
└── docs/                # Documentation
```

---

## 🆘 Quick Fixes

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not set` | Add to `.env` file |
| Rate limited | Check user role limits |
| Ollama not detected | Restart server after starting Ollama |
| RAG returns no results | Check vector index with `/api/v1/rag/stats` |
| Auth failing | Verify `JWT_SECRET` matches |

---

## 🔗 Useful Links

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Observability Dashboard**: http://localhost:8000/api/v1/observability/dashboard/html
- **RAG Stats**: http://localhost:8000/api/v1/rag/stats
- **Approval Queue**: http://localhost:8000/api/v1/approvals/pending

---

<div align="center">

**GoAI Platform v1** — Quick Reference 🚀

</div>
]]>
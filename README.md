<![CDATA[<div align="center">

```
   ██████╗  ██████╗  █████╗ ██╗    ██████╗ ██╗      █████╗ ████████╗███████╗ ██████╗ ██████╗ ███╗   ███╗
  ██╔════╝ ██╔═══██╗██╔══██╗██║    ██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔════╝██╔═══██╗██╔══██╗████╗ ████║
  ██║  ███╗██║   ██║███████║██║    ██████╔╝██║     ███████║   ██║   █████╗  ██║   ██║██████╔╝██╔████╔██║
  ██║   ██║██║   ██║██╔══██║██║    ██╔═══╝ ██║     ██╔══██║   ██║   ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║
  ╚██████╔╝╚██████╔╝██║  ██║██║    ██║     ███████╗██║  ██║   ██║   ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║
   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝
```

# 🏛️ Sovereign AI Platform v1

### *Enterprise AI Under Your Complete Control*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![License](https://img.shields.io/badge/License-Enterprise-gold?style=for-the-badge)](LICENSE)

---

**A fully self-hosted AI infrastructure for organizations that demand data sovereignty, model control, and regulatory compliance.**

[🚀 Quick Start](#-quick-start-5-minutes) • [📖 Documentation](#-documentation) • [🧪 Try It Now](#-try-it-now) • [🔧 API Reference](#-api-reference)

</div>

---

## ⚡ What Makes GoAI Different?

<table>
<tr>
<td width="50%">

### 🔐 **Complete Data Sovereignty**
Your data never leaves your infrastructure. Run LLMs on-premises with full audit trails.

</td>
<td width="50%">

### 🤖 **Production-Ready AI Agents**
Tool-calling agents, multi-agent collaboration, and Plan-and-Execute patterns out of the box.

</td>
</tr>
<tr>
<td width="50%">

### 📚 **Enterprise RAG**
Document ingestion, vector search, ACL per document, and multi-mode retrieval strategies.

</td>
<td width="50%">

### 📊 **Built-in AI Evaluations**
LLM-as-Judge quality metrics, regression detection, and systematic testing frameworks.

</td>
</tr>
<tr>
<td width="50%">

### 🎭 **11 Pre-Built Agent Templates**
Ready-to-use agents for research, code review, data analysis, writing, and more.

</td>
<td width="50%">

### 👁️ **Agent Observability Dashboard**
Real-time monitoring, cost tracking, execution traces, and visual analytics.

</td>
</tr>
</table>

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites

- Python 3.10+
- Node.js 18+ (for UI)
- Optional: OpenAI API key for cloud LLM features

### 1️⃣ Clone & Install

```bash
git clone https://github.com/your-org/goai-platform-v1.git
cd goai-platform-v1

# Install Python dependencies
pip install -r requirements.txt

# Configure environment (optional - enables LLM features)
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key
```

### 2️⃣ Start the Server

```bash
uvicorn main:app --reload --port 8000
```

### 3️⃣ Verify It's Running

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status": "healthy", "timestamp": "2025-12-07T..."}
```

### ✅ You're Ready!

Open the interactive API docs: **http://localhost:8000/docs**

---

## 🧪 Try It Now

### Test Agent Tools (No API Key Required)

```bash
# 🧮 Calculator
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculator", "arguments": {"expression": "(100 * 25) + 500"}}'
```
**Response:** `{"result": {"result": 3000}}`

```bash
# 📅 Get Current Date/Time
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_datetime", "arguments": {}}'
```

```bash
# 🔍 Web Search
curl -X POST http://localhost:8000/api/v1/agents/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "web_search", "arguments": {"query": "FastAPI best practices", "num_results": 3}}'
```

### Test RAG Pipeline

```bash
# 📄 Step 1: Ingest a Document
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Our company vacation policy: All employees receive 20 days paid time off per year. Unused days can carry over up to 5 days maximum. Requests must be submitted 2 weeks in advance.",
    "filename": "vacation_policy.txt"
  }'
```

```bash
# 🔍 Step 2: Query the Document
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many vacation days do employees get?", "top_k": 3}'
```

### Test Plan-and-Execute Agent (Requires API Key)

```bash
curl -X POST http://localhost:8000/api/v1/agents/plan-execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Calculate the total cost of 15 items at $24.99 each with 8% tax"}'
```

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│                          GoAI SOVEREIGN AI PLATFORM                              │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         🖥️  USER INTERFACES                                  │ │
│  │                                                                              │ │
│  │      React Console  •  REST API  •  Streaming (SSE)  •  Webhooks           │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         🛡️  GATEWAY LAYER                                    │ │
│  │                                                                              │ │
│  │      FastAPI  •  Auth/RBAC  •  Rate Limiting  •  Audit Logging            │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         🧠  INTELLIGENCE LAYER                               │ │
│  │                                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ 🤖 Agents    │  │ 📚 RAG       │  │ 🔄 Multi-    │  │ 📊 AI Evals  │   │ │
│  │  │              │  │    Engine    │  │    Agent     │  │              │   │ │
│  │  │ • Tools      │  │              │  │              │  │ • LLM Judge  │   │ │
│  │  │ • Planner    │  │ • Ingest     │  │ • Sequential │  │ • Metrics    │   │ │
│  │  │ • Memory     │  │ • Retrieve   │  │ • Parallel   │  │ • Datasets   │   │ │
│  │  │ • Streaming  │  │ • Generate   │  │ • Debate     │  │ • Regression │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │                                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ 🔌 MCP      │  │ 🪝 Triggers  │  │ 🧠 Memory   │  │ 💬 Prompts   │   │ │
│  │  │   Protocol   │  │   Webhooks   │  │   System     │  │   Library    │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         ⚡  INFERENCE LAYER                                   │ │
│  │                                                                              │ │
│  │      LLM Router  •  OpenAI  •  Anthropic  •  Ollama  •  vLLM              │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         💾  DATA LAYER                                       │ │
│  │                                                                              │ │
│  │      FAISS Vector Store  •  SQLite  •  PostgreSQL  •  Redis Cache         │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 AI Agent Framework

GoAI implements a complete **7-step AI Agent Framework**:

| Step | Component | What It Does | Location |
|:----:|-----------|--------------|----------|
| **1** | 📝 System Prompt | Defines agent behavior and personality | `modules/agents/engine.py` |
| **2** | 🧠 LLM | Multi-provider routing (OpenAI, Anthropic, Ollama) | `core/llm/router.py` |
| **3** | 🔧 Tools | Calculator, web search, Python execution, etc. | `modules/agents/tools.py` |
| **4** | 💾 Memory | Short/medium/long-term persistence | `api/v1/memory.py` |
| **5** | 🔄 Orchestration | YAML workflows with conditional logic | `core/orchestrator/engine.py` |
| **6** | 🖥️ UI | React console + REST APIs | `ui/console/` |
| **7** | 📊 AI Evals | LLM-as-Judge quality measurement | `modules/evals/engine.py` |

### Available Agent Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `calculator` | Math expressions | `{"expression": "sqrt(144) * 2"}` |
| `get_datetime` | Current date/time | `{}` |
| `web_search` | DuckDuckGo search | `{"query": "Python FastAPI", "num_results": 5}` |
| `execute_python` | Run Python code (sandboxed) | `{"code": "print(sum(range(10)))"}` |
| `fetch_url` | Fetch webpage content | `{"url": "https://example.com"}` |
| `parse_json` | Parse JSON strings | `{"json_string": "{\"key\": \"value\"}"}` |

### Plan-and-Execute Pattern

For complex multi-step tasks:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  TASK   │───▶│  PLAN   │───▶│ EXECUTE │───▶│ REPLAN? │───▶│ RESULT  │
│         │    │         │    │  Steps  │    │         │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                    │              │              │
                    ▼              ▼              ▼
              Break into      Use tools      Revise if
              steps w/deps    per step       step fails
```

```bash
# Execute with planning
curl -X POST http://localhost:8000/api/v1/agents/plan-execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Research Python web frameworks and recommend the best one for a startup"}'

# Preview plan only (without execution)
curl -X POST "http://localhost:8000/api/v1/agents/plan-only?task=Build+a+web+scraper"
```

### 🎭 Agent Templates

Pre-built agents optimized for specific use cases:

| Template | Pattern | Best For |
|----------|---------|----------|
| `researcher` | Plan-Execute | Deep research with web search |
| `data_analyst` | Plan-Execute | Data analysis & statistics |
| `code_reviewer` | Simple | Code reviews & security analysis |
| `code_generator` | Simple | Writing clean, documented code |
| `writer` | Simple | Content creation & editing |
| `summarizer` | Simple | Document summarization |
| `customer_support` | Simple | Customer service responses |
| `sql_expert` | Simple | SQL queries & optimization |
| `planner` | Plan-Execute | Project planning & breakdown |
| `research_team` | Multi-Agent | Team-based research |
| `code_review_team` | Multi-Agent | Multi-perspective code review |

```bash
# List all templates
curl http://localhost:8000/api/v1/agents/templates

# Get template details
curl http://localhost:8000/api/v1/agents/templates/researcher

# Run a template
curl -X POST http://localhost:8000/api/v1/agents/templates/writer/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a tagline for a coffee shop called Bean There", "template_id": "writer"}'
```

---

## 🛡️ Human-in-the-Loop (HITL) Approvals

Pause agent workflows for human review of sensitive actions:

### Built-in Approval Policies

| Policy | Categories | Default Timeout |
|--------|------------|-----------------|
| **High Risk** | payment, delete, sensitive_data | 2 hours |
| **External** | send_email, external_api, publish | 1 hour |
| **Data Modification** | database_modify, file_write | 30 min |
| **Cost Control** | high_cost | 1 hour |

### HITL API Examples

```bash
# Create an approval request
curl -X POST http://localhost:8000/api/v1/approvals/requests \
  -H "Content-Type: application/json" \
  -d '{
    "action": "Send promotional email to 10,000 customers",
    "category": "send_email",
    "agent_id": "marketing-agent"
  }'

# List pending approvals
curl http://localhost:8000/api/v1/approvals/pending

# Approve a request
curl -X POST http://localhost:8000/api/v1/approvals/requests/{id}/approve \
  -H "Content-Type: application/json" \
  -d '{"reason": "Approved for December campaign", "responded_by": "admin@example.com"}'

# Reject a request
curl -X POST http://localhost:8000/api/v1/approvals/requests/{id}/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "Needs legal review first"}'

# Check if approval is required
curl -X POST http://localhost:8000/api/v1/approvals/check \
  -H "Content-Type: application/json" \
  -d '{"category": "payment", "context": {"amount": 500}}'
```

---

## 🛡️ AI Guardrails

Comprehensive safety guardrails for AI agent operations:

### Guardrail Types

| Type | Description | Action |
|------|-------------|--------|
| **Prompt Injection** | Detects manipulation attempts | Block |
| **Harmful Content** | Blocks dangerous requests | Block |
| **PII Detection** | Detects SSN, credit cards, emails | Redact |
| **Profanity Filter** | Filters inappropriate language | Modify |
| **Tool Restrictions** | Controls dangerous tool usage | Require Approval |
| **Cost Limits** | Token/request limits | Block |
| **Rate Limiting** | Prevents abuse | Block |

### Guardrails API Examples

```bash
# Check user input for safety
curl -X POST http://localhost:8000/api/v1/guardrails/check/input \
  -H "Content-Type: application/json" \
  -d '{"content": "User message here", "user_id": "user-123"}'

# Check AI output (with PII redaction)
curl -X POST http://localhost:8000/api/v1/guardrails/check/output \
  -H "Content-Type: application/json" \
  -d '{"content": "The SSN is 123-45-6789"}'
# Returns: {"content": "The SSN is [REDACTED]", "modified": true}

# Check if tool call is allowed
curl -X POST http://localhost:8000/api/v1/guardrails/check/tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "execute_python", "arguments": {}}'

# List all rules
curl http://localhost:8000/api/v1/guardrails/rules

# Get guardrail statistics
curl http://localhost:8000/api/v1/guardrails/stats

# View recent violations
curl http://localhost:8000/api/v1/guardrails/violations
```

---

## 👁️ Agent Observability Dashboard

Real-time monitoring and analytics for all agent operations:

### Features

- 📊 **Execution Traces** - Track every step of agent execution
- 💰 **Cost Tracking** - Automatic cost estimation per model
- 🔧 **Tool Analytics** - Usage statistics for all tools
- ⚠️ **Error Monitoring** - Real-time error tracking
- 📈 **Hourly Statistics** - Activity trends and patterns
- 🔴 **Live Streaming** - SSE events for real-time updates

### Dashboard Access

```bash
# Visual HTML Dashboard
open http://localhost:8000/api/v1/observability/dashboard/html

# Dashboard API data
curl http://localhost:8000/api/v1/observability/dashboard

# List traces
curl http://localhost:8000/api/v1/observability/traces

# Active traces
curl http://localhost:8000/api/v1/observability/traces/active

# Tool usage stats
curl http://localhost:8000/api/v1/observability/stats/tools

# Cost breakdown
curl http://localhost:8000/api/v1/observability/stats/cost

# Real-time event stream (SSE)
curl http://localhost:8000/api/v1/observability/stream
```

---

## 📚 RAG (Retrieval-Augmented Generation)

### Retrieval Modes

| Mode | Best For | How It Works |
|------|----------|--------------|
| **Simple** | Basic Q&A | Direct query → retrieve → generate |
| **Conversational** | Multi-turn chat | Includes conversation history |
| **Multi-Query** | Complex questions | Generates multiple search queries |
| **Step-Back** | Abstract reasoning | Asks broader questions first |
| **HyDE** | Semantic matching | Generates hypothetical answer to search |

### RAG API Examples

```bash
# Simple query
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our refund policy?", "mode": "simple"}'

# Conversational RAG with history
curl -X POST http://localhost:8000/api/v1/rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about for digital products?",
    "conversation_id": "conv-123",
    "mode": "conversational"
  }'

# Multi-query for complex questions
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare our vacation and remote work policies", "mode": "multi_query"}'
```

---

## 🔌 MCP Protocol (Model Context Protocol)

Standardized tool integration for AI interoperability:

```bash
# List available MCP tools
curl http://localhost:8000/api/v1/mcp/tools

# Execute via MCP protocol
curl -X POST http://localhost:8000/api/v1/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"name": "calculator", "arguments": {"expression": "2 + 2"}}'

# Get execution statistics
curl http://localhost:8000/api/v1/mcp/stats
```

---

## 🪝 Webhooks & Triggers

Event-driven automation:

```bash
# Create a webhook
curl -X POST http://localhost:8000/api/v1/triggers/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Document Processor",
    "description": "Process documents on upload",
    "action": "rag_query",
    "action_params": {"top_k": 5},
    "secret": "my-webhook-secret"
  }'

# List webhooks
curl http://localhost:8000/api/v1/triggers/webhooks

# Trigger a webhook
curl -X POST http://localhost:8000/api/v1/triggers/webhooks/{webhook_id}/trigger \
  -H "X-Signature: sha256=..." \
  -H "Content-Type: application/json" \
  -d '{"query": "Process this document"}'
```

---

## 📊 AI Evaluations

Systematic quality measurement:

```bash
# List available metrics
curl http://localhost:8000/api/v1/evals/metrics

# Create an evaluation dataset
curl -X POST http://localhost:8000/api/v1/evals/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support QA",
    "description": "Test cases for support bot",
    "test_cases": [
      {
        "query": "How do I reset my password?",
        "expected": "Go to Settings > Security > Reset Password",
        "tags": ["account", "security"]
      },
      {
        "query": "What are your business hours?",
        "expected": "Monday-Friday 9AM-5PM EST",
        "tags": ["general"]
      }
    ]
  }'

# Run evaluation
curl -X POST http://localhost:8000/api/v1/evals/run \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "dataset-123", "model": "gpt-4o-mini"}'
```

---

## 🔧 Complete API Reference

> **32 API modules** covering all platform capabilities

### Quick Overview: All Services

| Category | Services | Count |
|----------|----------|:-----:|
| **🧠 Intelligence** | LLM, Streaming, Agents, Multi-Agent, Plan-Execute, Templates | 6 |
| **📚 Knowledge** | RAG, Ingest, Retrieve, Memory | 4 |
| **📊 Analysis** | Sentiment, SQL Agent, Validator, OCR | 4 |
| **🔄 Automation** | Orchestrator, Triggers, MCP Protocol | 3 |
| **📈 Quality** | AI Evaluations, Feedback, Activity | 3 |
| **🛡️ Governance** | Guardrails, Approvals (HITL), Observability | 3 |
| **🔐 Platform** | Auth, Upload, Export, Prompts, Performance, Telemetry | 6 |
| **🎯 Domain** | EBC Tickets, Customer KYC, Meeting Notes | 3 |

---

### 🏥 Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/config` | GET | Configuration status |
| `/docs` | GET | Interactive Swagger docs |
| `/redoc` | GET | ReDoc API docs |

---

### 🧠 LLM & Streaming

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/llm/chat` | POST | Chat completion |
| `/api/v1/llm/complete` | POST | Text completion |
| `/api/v1/llm/providers` | GET | List LLM providers |
| `/api/v1/stream/chat` | POST | Streaming chat (SSE) |
| `/api/v1/stream/complete` | POST | Streaming completion |

---

### 📚 RAG & Knowledge

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag/query` | POST | Query with RAG |
| `/api/v1/rag/chat` | POST | Conversational RAG |
| `/api/v1/rag/ask` | POST | Quick Q&A |
| `/api/v1/rag/stats` | GET | RAG statistics |
| `/api/v1/rag/documents` | GET | List documents |
| `/api/v1/rag/conversation` | POST | Create conversation |
| `/api/v1/ingest/text` | POST | Ingest text content |
| `/api/v1/ingest/document` | POST | Upload file document |
| `/api/v1/retrieve/` | POST | Semantic search |
| `/api/v1/retrieve/hybrid` | POST | Hybrid search |

---

### 🤖 AI Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/run` | POST | Run agent |
| `/api/v1/agents/stream` | POST | Stream agent (SSE) |
| `/api/v1/agents/plan-execute` | POST | Plan-and-Execute agent |
| `/api/v1/agents/plan-only` | POST | Create plan without executing |
| `/api/v1/agents/tools` | GET | List available tools |
| `/api/v1/agents/tools/execute` | POST | Execute tool directly |
| `/api/v1/agents/ask` | GET | Quick question |
| `/api/v1/agents/templates` | GET | List agent templates |
| `/api/v1/agents/templates/categories` | GET | List template categories |
| `/api/v1/agents/templates/{id}` | GET | Get template details |
| `/api/v1/agents/templates/{id}/run` | POST | Run agent from template |
| `/api/v1/agents/templates/{id}/examples` | GET | Get example prompts |

---

### 👥 Multi-Agent Collaboration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/multi-agent/session` | POST | Create multi-agent session |
| `/api/v1/multi-agent/run` | POST | Run multi-agent task |
| `/api/v1/multi-agent/patterns` | GET | List collaboration patterns |

---

### 💾 Memory System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/memory` | GET | List user memories |
| `/api/v1/memory` | POST | Create memory |
| `/api/v1/memory/{id}` | GET | Get memory by ID |
| `/api/v1/memory/{id}` | PUT | Update memory |
| `/api/v1/memory/{id}` | DELETE | Delete memory |
| `/api/v1/memory/search` | POST | Search memories |

---

### 📊 Sentiment Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sentiment/analyze` | POST | Analyze text sentiment |
| `/api/v1/sentiment/batch` | POST | Batch sentiment analysis |
| `/api/v1/sentiment/aspects` | POST | Aspect-based sentiment |

---

### 🗄️ SQL Agent

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sql/query` | POST | Natural language to SQL |
| `/api/v1/sql/execute` | POST | Execute SQL query |
| `/api/v1/sql/schema` | GET | Get database schema |
| `/api/v1/sql/tables` | GET | List tables |

---

### ✅ Document Validator

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/validator/validate` | POST | Validate document |
| `/api/v1/validator/rules` | GET | List validation rules |
| `/api/v1/validator/compare` | POST | Compare documents |

---

### 🔄 Orchestrator (Workflows)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/orchestrator/workflows` | GET | List workflows |
| `/api/v1/orchestrator/workflows/execute` | POST | Execute workflow |
| `/api/v1/orchestrator/actions` | GET | List available actions |

---

### 📈 AI Evaluations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/evals/datasets` | GET/POST | Manage datasets |
| `/api/v1/evals/datasets/{id}` | GET/DELETE | Dataset by ID |
| `/api/v1/evals/metrics` | GET | List evaluation metrics |
| `/api/v1/evals/run` | POST | Run evaluation |
| `/api/v1/evals/runs` | GET | List evaluation runs |

---

### 🔌 MCP Protocol

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcp/info` | GET | Server info |
| `/api/v1/mcp/tools` | GET | List MCP tools |
| `/api/v1/mcp/execute` | POST | Execute via MCP |
| `/api/v1/mcp/stats` | GET | Execution statistics |
| `/api/v1/mcp/client/servers` | GET/POST | Manage remote servers |
| `/api/v1/mcp/client/tools` | GET | List remote tools |

---

### 🪝 Triggers & Webhooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/triggers/webhooks` | GET/POST | Manage webhooks |
| `/api/v1/triggers/webhooks/{id}` | GET/PUT/DELETE | Webhook by ID |
| `/api/v1/triggers/webhooks/{id}/trigger` | POST | Fire webhook |
| `/api/v1/triggers/event-types` | GET | List event types |
| `/api/v1/triggers/quick-trigger` | POST | Quick action trigger |

---

### 🛡️ AI Guardrails

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/guardrails/` | GET | System info |
| `/api/v1/guardrails/check/input` | POST | Check user input safety |
| `/api/v1/guardrails/check/output` | POST | Check AI output safety |
| `/api/v1/guardrails/check/tool` | POST | Check tool call permission |
| `/api/v1/guardrails/check/cost` | POST | Check cost limits |
| `/api/v1/guardrails/rules` | GET | List all rules |
| `/api/v1/guardrails/rules/{name}` | GET | Get rule details |
| `/api/v1/guardrails/rules/{name}/enable` | PUT | Enable a rule |
| `/api/v1/guardrails/rules/{name}/disable` | PUT | Disable a rule |
| `/api/v1/guardrails/config` | GET/PUT | Get/update configuration |
| `/api/v1/guardrails/stats` | GET | Get statistics |
| `/api/v1/guardrails/violations` | GET | Get recent violations |

---

### 👤 Human-in-the-Loop Approvals

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/approvals/` | GET | System info |
| `/api/v1/approvals/pending` | GET | List pending approvals |
| `/api/v1/approvals/requests` | GET/POST | Manage requests |
| `/api/v1/approvals/requests/{id}` | GET | Get request details |
| `/api/v1/approvals/requests/{id}/approve` | POST | Approve request |
| `/api/v1/approvals/requests/{id}/reject` | POST | Reject request |
| `/api/v1/approvals/requests/{id}/cancel` | POST | Cancel request |
| `/api/v1/approvals/check` | POST | Check if approval required |
| `/api/v1/approvals/policies` | GET/POST | Manage policies |
| `/api/v1/approvals/policies/{id}` | GET/DELETE | Policy by ID |
| `/api/v1/approvals/stats` | GET | Approval statistics |
| `/api/v1/approvals/audit` | GET | Audit log |

---

### 👁️ Agent Observability

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/observability/` | GET | System info |
| `/api/v1/observability/dashboard` | GET | Dashboard data (JSON) |
| `/api/v1/observability/dashboard/html` | GET | Visual dashboard (HTML) |
| `/api/v1/observability/traces` | GET | List traces |
| `/api/v1/observability/traces/active` | GET | Active traces |
| `/api/v1/observability/traces/{id}` | GET | Trace details with events |
| `/api/v1/observability/stats` | GET | Aggregated statistics |
| `/api/v1/observability/stats/tools` | GET | Tool usage stats |
| `/api/v1/observability/stats/models` | GET | Model usage stats |
| `/api/v1/observability/stats/cost` | GET | Cost breakdown |
| `/api/v1/observability/errors` | GET | Recent errors |
| `/api/v1/observability/stream` | GET | Real-time SSE stream |

---

### 💬 Prompt Library

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/prompts` | GET | List prompts |
| `/api/v1/prompts` | POST | Create prompt |
| `/api/v1/prompts/{id}` | GET/PUT/DELETE | Manage prompt |
| `/api/v1/prompts/{id}/execute` | POST | Execute prompt |
| `/api/v1/prompts/{id}/preview` | POST | Preview with variables |

---

### 📝 Feedback Collection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/feedback` | GET/POST | Manage feedback |
| `/api/v1/feedback/{id}` | GET/PUT/DELETE | Feedback by ID |
| `/api/v1/feedback/stats` | GET | Feedback statistics |
| `/api/v1/feedback/export` | GET | Export feedback data |

---

### 🔐 Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/logout` | POST | User logout |
| `/api/v1/auth/me` | GET | Current user info |
| `/api/v1/auth/refresh` | POST | Refresh token |

---

### 📤 File Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/upload/file` | POST | Upload file |
| `/api/v1/upload/batch` | POST | Batch upload |
| `/api/v1/export/documents` | GET | Export documents |
| `/api/v1/export/data` | POST | Export data |

---

### 📊 Telemetry & Performance

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/telemetry/overview` | GET | System overview |
| `/api/v1/telemetry/metrics` | GET | Detailed metrics |
| `/api/v1/telemetry/traces` | GET | Request traces |
| `/api/v1/performance/stats` | GET | Performance stats |
| `/api/v1/performance/cache` | GET/DELETE | Cache management |

---

### 🎫 Domain: EBC Tickets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ebc-tickets/` | GET/POST | Manage tickets |
| `/api/v1/ebc-tickets/{id}` | GET/PUT | Ticket by ID |
| `/api/v1/ebc-tickets/analyze` | POST | Analyze ticket |
| `/api/v1/ebc-tickets/stats` | GET | Ticket statistics |

---

### 🪪 Domain: Customer KYC

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/kyc/verify` | POST | Verify customer |
| `/api/v1/kyc/documents` | POST | Submit KYC documents |
| `/api/v1/kyc/status/{id}` | GET | Check KYC status |
| `/api/v1/kyc/risk-score` | POST | Calculate risk score |

---

### 📝 Domain: Meeting Notes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/meeting-notes/` | GET | Service info |
| `/api/v1/meeting-notes/summarize` | POST | Summarize meeting notes |
| `/api/v1/meeting-notes/action-items` | POST | Extract action items |
| `/api/v1/meeting-notes/format/markdown` | POST | Format as markdown |
| `/api/v1/meeting-notes/meetings` | GET | List meetings |
| `/api/v1/meeting-notes/meetings/{id}` | GET | Get meeting by ID |
| `/api/v1/meeting-notes/search` | GET | Search meetings |

---

### 📷 OCR (Document Scanning)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ocr/extract` | POST | Extract text from image |
| `/api/v1/ocr/batch` | POST | Batch OCR processing |
| `/api/v1/ocr/structured` | POST | Extract structured data |

---

### 📋 Activity Logging

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/activity` | GET | List activities |
| `/api/v1/activity/user/{user_id}` | GET | User activities |
| `/api/v1/activity/stats` | GET | Activity statistics |

---

## 📁 Project Structure

```
goai-platform-v1/
│
├── 📄 main.py                    # FastAPI application entry point
├── 📄 requirements.txt           # Python dependencies
├── 📄 .env.example               # Environment template
│
├── 📂 api/v1/                    # REST API endpoints
│   ├── agents.py                 # Agent operations
│   ├── rag.py                    # RAG operations
│   ├── memory.py                 # Memory system
│   ├── evals.py                  # AI evaluations
│   ├── mcp.py                    # MCP protocol
│   ├── triggers.py               # Webhooks/triggers
│   └── ...
│
├── 📂 core/                      # Core infrastructure
│   ├── llm/                      # LLM routing
│   ├── vector/                   # Vector store
│   ├── auth/                     # Authentication
│   ├── orchestrator/             # Workflow engine
│   └── telemetry/                # Metrics & logging
│
├── 📂 modules/                   # Feature modules
│   ├── agents/                   # Agent engine & tools
│   │   ├── engine.py             # Main agent logic
│   │   ├── tools.py              # Tool registry
│   │   ├── planner.py            # Plan-and-Execute
│   │   ├── templates.py          # 11 pre-built agent templates
│   │   ├── hitl.py               # Human-in-the-Loop approvals
│   │   ├── observability.py      # Agent monitoring & tracing
│   │   ├── guardrails.py         # AI safety guardrails
│   │   └── multi_agent.py        # Multi-agent collaboration
│   ├── rag/                      # RAG pipeline
│   ├── evals/                    # Evaluation engine
│   ├── mcp/                      # MCP server/client
│   ├── meeting_notes/            # Meeting summarization
│   └── ...
│
├── 📂 ui/console/                # React frontend
│   ├── src/pages/                # Page components
│   └── src/components/           # Shared components
│
├── 📂 use_cases/                 # Example use cases
│   ├── customer_kyc/             # KYC verification
│   └── document_qa/              # Document Q&A
│
├── 📂 docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   ├── CORE_MODULES.md
│   ├── QUICK_REFERENCE.md
│   └── ...
│
└── 📂 tests/                     # Test suite
    ├── test_agents.py
    ├── test_rag.py
    └── ...
```

---

## 📖 Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | Developer cheat sheet | Developers |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture | Architects |
| [CORE_MODULES.md](docs/CORE_MODULES.md) | Module specifications | Developers |
| [SECURITY_GOVERNANCE.md](docs/SECURITY_GOVERNANCE.md) | Security controls | Security team |
| [DEVELOPMENT_CYCLE.md](docs/DEVELOPMENT_CYCLE.md) | Development process | Developers |
| [USE_CASE_BLUEPRINT.md](docs/USE_CASE_BLUEPRINT.md) | Building use cases | Product/Dev |
| [OPERATIONAL_PLAYBOOKS.md](docs/OPERATIONAL_PLAYBOOKS.md) | Operations guides | SRE/Ops |
| [OBSERVABILITY_MONITORING.md](docs/OBSERVABILITY_MONITORING.md) | Monitoring setup | SRE/Ops |

---

## 🔧 Configuration

### Environment Variables

```bash
# Required for LLM features
OPENAI_API_KEY=sk-your-openai-key

# Optional: Alternative LLM providers
ANTHROPIC_API_KEY=sk-ant-your-key
OLLAMA_HOST=http://localhost:11434

# Authentication
JWT_SECRET=your-256-bit-secret-key

# Database (defaults to SQLite in ./data/)
DATABASE_URL=sqlite:///./data/goai_platform.db

# Production: PostgreSQL
# DATABASE_URL=postgresql://user:pass@host:5432/goai
```

### Using Local Models with Ollama

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull llama3.2

# 3. Start Ollama
ollama serve

# 4. Set environment variable
export OLLAMA_HOST=http://localhost:11434

# 5. Restart GoAI server
uvicorn main:app --reload --port 8000
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_agents.py -v

# With coverage
pytest tests/ --cov=modules --cov-report=html
```

### Test a Use Case

```bash
# Run the document Q&A use case test
python use_cases/document_qa/test_use_case.py
```

---

## 🚢 Deployment

### Docker

```bash
# Build
docker build -t goai-platform:latest -f docker/Dockerfile .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e JWT_SECRET=your-secret \
  goai-platform:latest
```

### Docker Compose

```bash
docker-compose up -d
```

### Production with GPU

```bash
# Start vLLM with GPU
docker-compose -f docker-compose.vllm.yml up -d

# Start platform
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## 🔒 Security

### Key Security Features

- ✅ JWT-based authentication
- ✅ Role-based access control (RBAC)
- ✅ Document-level ACL
- ✅ Audit logging for all operations
- ✅ Rate limiting per user/role
- ✅ Input validation & sanitization
- ✅ Webhook signature verification (HMAC-SHA256)

### Security Checklist

- [ ] Change default credentials
- [ ] Set strong `JWT_SECRET`
- [ ] Configure HTTPS in production
- [ ] Enable audit logging
- [ ] Set appropriate rate limits
- [ ] Configure document ACLs
- [ ] Test DR procedures

---

## 📈 Version History

| Version | Date | Highlights |
|---------|------|------------|
| **1.5.0** | Dec 2025 | **AI Guardrails** (input/output/tool/PII safety) |
| **1.4.0** | Dec 2025 | Agent Templates (11 pre-built), HITL Approvals, Observability Dashboard, Meeting Notes |
| **1.3.0** | Dec 2025 | Bug fixes, singleton patterns, improved webhook security |
| **1.2.0** | Dec 2025 | AI Evaluations, MCP Protocol, Triggers/Webhooks |
| **1.1.0** | Dec 2025 | Enhanced agent tools, memory system, prompt library |
| **1.0.0** | Nov 2025 | Initial sovereign release |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/goai-platform-v1/issues)
- **Security**: security@yourcompany.com

---

<div align="center">

### 🏛️ GoAI Sovereign AI Platform v1

**Enterprise AI Under Your Complete Control**

*Built with ❤️ for organizations that value data sovereignty*

</div>
]]>
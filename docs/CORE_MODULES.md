# GoAI Sovereign Platform — Core Modules Specification

## Non-Negotiable Components

These modules are **included in every deployment** and form the foundation of the sovereign stack. They cannot be removed or replaced with external alternatives.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
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
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. ⚙️ LLM Router

### Purpose

The LLM Router provides a **unified interface** for all LLM interactions across the platform. It abstracts away provider-specific implementations, handles model selection, load balancing, and fallback logic.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  LLM Router                                          │
│                                                                                      │
│   Application Request                                                                │
│          │                                                                           │
│          ▼                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           Unified Interface                                   │  │
│   │                                                                               │  │
│   │   llm_router.run(model_id, messages, temperature, max_tokens)                │  │
│   │   llm_router.stream(model_id, messages, ...)                                 │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                           │
│          ▼                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                            Model Router                                       │  │
│   │                                                                               │  │
│   │   Priority Queue → Health Check → Load Balance → Select Provider             │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                           │
│          ├──────────────────┬──────────────────┬──────────────────┐                 │
│          ▼                  ▼                  ▼                  ▼                 │
│   ┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐          │
│   │   vLLM     │     │    TGI     │     │  Ollama    │     │  Fallback  │          │
│   │ (Primary)  │     │ (Alt)      │     │  (Dev)     │     │ (External) │          │
│   └────────────┘     └────────────┘     └────────────┘     └────────────┘          │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/llm/router.py

class LLMRouter:
    async def run(
        self,
        model_id: str,              # Model identifier (e.g., "llama-70b")
        messages: List[dict],       # [{"role": "user", "content": "..."}]
        temperature: float = 0.7,   # Sampling temperature
        max_tokens: int = 2048,     # Max output tokens
        stop: List[str] = None,     # Stop sequences
        user_id: str = None         # For quota tracking
    ) -> dict:
        """Synchronous LLM call. Returns complete response."""
        
    async def stream(
        self,
        model_id: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: List[str] = None,
        user_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """Streaming LLM call. Yields tokens as generated."""
        
    def list_models(self) -> List[dict]:
        """List available models with their specs."""
        
    def get_model_info(self, model_id: str) -> dict:
        """Get detailed info about a specific model."""
        
    async def health_check(self, model_id: str = None) -> dict:
        """Check health of model endpoints."""
```

### Response Format (Standard)

```python
# Synchronous response
{
    "id": "gen-abc123",
    "model": "llama-70b",
    "content": "Generated response text...",
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 200,
        "total_tokens": 350
    },
    "finish_reason": "stop",  # or "length", "tool_call"
    "latency_ms": 1250
}

# Streaming chunk
{
    "id": "gen-abc123",
    "model": "llama-70b",
    "chunk": "Generated",  # Incremental token
    "finish_reason": None   # null until final chunk
}
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `models` | Registered model endpoints | - | Any valid endpoint |
| `default_model` | Fallback model ID | `llama-70b` | Any registered |
| `timeout_seconds` | Request timeout | `120` | 10-600 |
| `retry_count` | Retries on failure | `3` | 0-10 |
| `fallback_enabled` | Enable external fallback | `false` | true/false |
| `fallback_provider` | External provider | `openai` | openai/anthropic |
| `load_balance_strategy` | How to distribute | `round_robin` | round_robin/least_conn/random |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Interface** | `run()` / `stream()` | All modules depend on this interface |
| **Response format** | See above | Consistent parsing across platform |
| **Token counting** | tiktoken-compatible | Accurate billing/limits |
| **Error codes** | HTTP standard | Consistent error handling |
| **Metrics emitted** | `llm_*` prefix | Dashboards expect this |
| **Health endpoint** | `/health` on all models | Monitoring integration |

---

## 2. 🧠 Orchestrator Engine

### Purpose

The Orchestrator Engine executes **multi-step workflows** defined in YAML. It handles step sequencing, variable passing, error handling, and integrates with all other core modules.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                Orchestrator Engine                                   │
│                                                                                      │
│   Workflow YAML                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │  name: document-analysis                                                      │  │
│   │  steps:                                                                       │  │
│   │    - action: ingest                                                          │  │
│   │      input: ${document}                                                      │  │
│   │    - action: llm_call                                                        │  │
│   │      model: llama-70b                                                        │  │
│   │      prompt: "Summarize: ${previous_output}"                                 │  │
│   │    - action: store_result                                                    │  │
│   │      destination: memory                                                     │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                           │
│          ▼                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                            Execution Engine                                   │  │
│   │                                                                               │  │
│   │   Parse YAML → Validate Steps → Execute Sequentially → Handle Errors         │  │
│   │                                                                               │  │
│   │   Built-in Actions:                                                          │  │
│   │   • llm_call     - Call LLM via Router                                       │  │
│   │   • rag_query    - Query knowledge base                                      │  │
│   │   • ingest       - Add document to knowledge                                 │  │
│   │   • agent_run    - Execute AI agent                                          │  │
│   │   • http_call    - External API call                                         │  │
│   │   • transform    - Data transformation                                       │  │
│   │   • conditional  - If/else branching                                         │  │
│   │   • loop         - Iterate over items                                        │  │
│   │   • parallel     - Execute steps concurrently                                │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/orchestrator/engine.py

class OrchestratorEngine:
    async def execute(
        self,
        workflow_name: str,         # Name of workflow YAML
        payload: dict,              # Input variables
        user_id: str = None,        # For auth context
        timeout: int = 3600         # Max execution time
    ) -> dict:
        """Execute a complete workflow."""
        
    async def execute_step(
        self,
        action: str,                # Action type
        params: dict,               # Action parameters
        context: dict               # Execution context
    ) -> dict:
        """Execute a single step (internal use)."""
        
    def register_action(
        self,
        name: str,
        handler: Callable
    ) -> None:
        """Register custom action handler."""
        
    def list_workflows(self) -> List[str]:
        """List available workflow definitions."""
        
    def validate_workflow(self, workflow: dict) -> dict:
        """Validate workflow YAML structure."""
```

### Workflow Result Format (Standard)

```python
{
    "workflow_id": "wf-abc123",
    "workflow_name": "document-analysis",
    "status": "completed",  # or "failed", "running", "cancelled"
    "started_at": "2025-01-01T10:00:00Z",
    "completed_at": "2025-01-01T10:00:15Z",
    "duration_ms": 15000,
    "steps": [
        {
            "step_index": 0,
            "action": "ingest",
            "status": "completed",
            "duration_ms": 2000,
            "output": {...}
        },
        {
            "step_index": 1,
            "action": "llm_call",
            "status": "completed",
            "duration_ms": 10000,
            "output": {...}
        }
    ],
    "final_output": {...},
    "error": null
}
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `workflow_directory` | Path to YAML files | `./workflows` | Any path |
| `max_steps` | Max steps per workflow | `100` | 1-1000 |
| `step_timeout` | Timeout per step | `300s` | 10-3600 |
| `parallel_limit` | Max parallel steps | `10` | 1-50 |
| `retry_on_failure` | Auto-retry failed steps | `true` | true/false |
| `custom_actions` | Additional action handlers | `[]` | Callable list |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **YAML format** | See spec | Consistent workflow definition |
| **Built-in actions** | 9 core actions | Platform integration |
| **Variable syntax** | `${variable}` | Standard templating |
| **Result format** | See above | Logging/debugging consistency |
| **Error handling** | try/catch/finally | Predictable behavior |
| **Audit logging** | All steps logged | Compliance requirement |

---

## 3. 🔍 Vector Store

### Purpose

The Vector Store provides **semantic search** capabilities for the knowledge layer. It manages document embeddings, similarity search, and namespace isolation for multi-tenant deployments.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  Vector Store                                        │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                            Embedding Service                                  │  │
│   │                                                                               │  │
│   │   Text → Tokenize → BGE-large-en-v1.5 → 1024-dim Vector → Normalize          │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                           │
│          ▼                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                              FAISS Index                                      │  │
│   │                                                                               │  │
│   │   Index Type: IVF4096,PQ64                                                   │  │
│   │   Metric: Cosine Similarity (Inner Product on normalized)                    │  │
│   │                                                                               │  │
│   │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                │  │
│   │   │   Namespace:   │  │   Namespace:   │  │   Namespace:   │                │  │
│   │   │    global      │  │   policies     │  │   dept_legal   │                │  │
│   │   │   (500K vec)   │  │   (50K vec)    │  │   (30K vec)    │                │  │
│   │   └────────────────┘  └────────────────┘  └────────────────┘                │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                           │
│          ▼                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           Metadata Store (PostgreSQL)                         │  │
│   │                                                                               │  │
│   │   vector_id │ document_id │ chunk_index │ content │ metadata │ created_at    │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/vector/retriever.py

class VectorStore:
    async def add_documents(
        self,
        documents: List[dict],      # [{"id", "content", "metadata"}]
        namespace: str = "global"   # Namespace for isolation
    ) -> dict:
        """Add documents to vector store."""
        
    async def search(
        self,
        query: str,                 # Natural language query
        top_k: int = 10,            # Number of results
        namespace: str = "global",  # Search namespace
        filter: dict = None,        # Metadata filters
        min_score: float = 0.0      # Minimum similarity
    ) -> List[dict]:
        """Semantic search."""
        
    async def delete(
        self,
        document_ids: List[str],    # IDs to delete
        namespace: str = "global"
    ) -> dict:
        """Remove documents from store."""
        
    async def get_document(
        self,
        document_id: str,
        namespace: str = "global"
    ) -> dict:
        """Retrieve specific document."""
        
    def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        
    def get_stats(self, namespace: str = None) -> dict:
        """Get index statistics."""
```

### Search Result Format (Standard)

```python
[
    {
        "id": "chunk-abc123",
        "document_id": "doc-xyz789",
        "content": "Retrieved text content...",
        "score": 0.89,  # Cosine similarity 0-1
        "metadata": {
            "filename": "policy.pdf",
            "page_number": 5,
            "section": "3.2 Security",
            "chunk_index": 12,
            "created_at": "2025-01-01T10:00:00Z"
        }
    },
    ...
]
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `embedding_model` | Model for embeddings | `bge-large-en-v1.5` | Any sentence-transformer |
| `embedding_batch_size` | Batch size for embedding | `32` | 1-128 |
| `index_type` | FAISS index type | `IVF4096,PQ64` | See FAISS docs |
| `nprobe` | Search clusters | `128` | 1-index_size |
| `default_top_k` | Default results | `10` | 1-100 |
| `persistence_path` | Index storage location | `./data/indexes` | Any path |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Dimensions** | `1024` | BGE-large output |
| **Normalization** | Always on | Required for cosine similarity |
| **Metric** | Cosine similarity | Semantic search standard |
| **Result format** | See above | Consistent across platform |
| **Metadata schema** | Standard fields | ACL and audit integration |
| **Query prefix** | BGE instruction | Model requirement |

---

## 4. 🔐 Auth & RBAC

### Purpose

The Auth & RBAC module handles **authentication and authorization** for all platform access. It integrates with Keycloak for enterprise deployments and provides a standalone mode for simpler setups.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  Auth & RBAC                                         │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           Authentication Flow                                 │  │
│   │                                                                               │  │
│   │   Login Request                                                              │  │
│   │        │                                                                     │  │
│   │        ▼                                                                     │  │
│   │   ┌─────────────────────────────────────────────────────────────────────┐   │  │
│   │   │                    Auth Provider                                     │   │  │
│   │   │                                                                      │   │  │
│   │   │   ┌─────────────┐      OR      ┌─────────────┐                     │   │  │
│   │   │   │  Keycloak   │              │  Standalone │                     │   │  │
│   │   │   │  (Prod)     │              │  (Dev/Test) │                     │   │  │
│   │   │   └─────────────┘              └─────────────┘                     │   │  │
│   │   │                                                                      │   │  │
│   │   └─────────────────────────────────────────────────────────────────────┘   │  │
│   │        │                                                                     │  │
│   │        ▼                                                                     │  │
│   │   JWT Token (24h expiry)                                                    │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                              RBAC Model                                       │  │
│   │                                                                               │  │
│   │   ┌─────────────┐                                                            │  │
│   │   │    admin    │ ── Full access, user management, model deployment         │  │
│   │   └──────┬──────┘                                                            │  │
│   │          │                                                                    │  │
│   │   ┌──────┴──────┐                                                            │  │
│   │   │  operator   │ ── Model management, monitoring, no user data             │  │
│   │   └──────┬──────┘                                                            │  │
│   │          │                                                                    │  │
│   │   ┌──────┴──────┐                                                            │  │
│   │   │ power_user  │ ── All AI features, high limits, document management      │  │
│   │   └──────┬──────┘                                                            │  │
│   │          │                                                                    │  │
│   │   ┌──────┴──────┐                                                            │  │
│   │   │    user     │ ── Standard AI features, normal limits                    │  │
│   │   └──────┬──────┘                                                            │  │
│   │          │                                                                    │  │
│   │   ┌──────┴──────┐                                                            │  │
│   │   │  readonly   │ ── View only, no generation                               │  │
│   │   └─────────────┘                                                            │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/auth/service.py

class AuthService:
    async def register(
        self,
        email: str,
        username: str,
        password: str,
        role: str = "user"
    ) -> dict:
        """Register new user."""
        
    async def login(
        self,
        username: str,
        password: str
    ) -> dict:
        """Authenticate and return JWT token."""
        
    async def validate_token(
        self,
        token: str
    ) -> dict:
        """Validate JWT and return user info."""
        
    def has_permission(
        self,
        user: dict,
        permission: str
    ) -> bool:
        """Check if user has specific permission."""
        
    async def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: List[str]
    ) -> dict:
        """Create API key for programmatic access."""
        
    async def revoke_api_key(
        self,
        key_id: str
    ) -> bool:
        """Revoke an API key."""

# Location: core/auth/dependencies.py

async def get_current_user(token: str) -> dict:
    """FastAPI dependency - extracts user from token."""
    
async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency - requires authenticated user."""
    
async def require_role(role: str):
    """FastAPI dependency factory - requires specific role."""
    
async def get_user_id_flexible(token: Optional[str]) -> str:
    """Returns user_id or 'default' for anonymous."""
```

### Permission Matrix (Standard)

| Permission | admin | operator | power_user | user | readonly |
|------------|-------|----------|------------|------|----------|
| `llm:generate` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `llm:generate:70b` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `rag:query` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `rag:ingest` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `rag:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `agents:run` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `agents:tools:all` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `memory:read` | ✅ | ❌ | ✅ | ✅ | ✅ |
| `memory:write` | ✅ | ❌ | ✅ | ✅ | ❌ |
| `admin:users` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `admin:models` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `audit:view` | ✅ | ✅ | ❌ | ❌ | ❌ |

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `auth_provider` | Auth backend | `standalone` | standalone/keycloak |
| `keycloak_url` | Keycloak server URL | - | Valid URL |
| `keycloak_realm` | Keycloak realm | `goai` | Any string |
| `jwt_expiry_hours` | Token lifetime | `24` | 1-720 |
| `password_min_length` | Min password length | `8` | 6-32 |
| `mfa_enabled` | Require MFA | `false` | true/false |
| `api_key_prefix` | API key prefix | `goai_` | Any string |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Roles** | 5 fixed roles | Platform-wide consistency |
| **Permission names** | Standard set | All modules check these |
| **JWT algorithm** | HS256 | Security standard |
| **Password hashing** | bcrypt | Security standard |
| **Token format** | Bearer JWT | Industry standard |
| **User ID field** | `user_id` | All modules expect this |

---

## 5. ⛓️ Retrieval Logging

### Purpose

The Retrieval Logging module provides **complete audit trails** for all document retrieval operations. It captures what was searched, what was retrieved, and what was used in responses for compliance and debugging.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               Retrieval Logging                                      │
│                                                                                      │
│   RAG Query                                                                          │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           Capture Point                                       │  │
│   │                                                                               │  │
│   │   • Query text                                                               │  │
│   │   • Query embedding hash                                                     │  │
│   │   • User ID                                                                  │  │
│   │   • Session ID                                                               │  │
│   │   • Timestamp                                                                │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           Vector Search                                       │  │
│   │                                                                               │  │
│   │   Captured:                                                                  │  │
│   │   • All retrieved documents (IDs, scores)                                    │  │
│   │   • Retrieval latency                                                        │  │
│   │   • Namespace searched                                                       │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           ACL Filter                                          │  │
│   │                                                                               │  │
│   │   Captured:                                                                  │  │
│   │   • Documents filtered out                                                   │  │
│   │   • Filter reason (ACL denied)                                               │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                           Response Generation                                 │  │
│   │                                                                               │  │
│   │   Captured:                                                                  │  │
│   │   • Documents used in context                                                │  │
│   │   • Citations generated                                                      │  │
│   │   • Response generated (hash)                                                │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                        PostgreSQL (retrieval_audit)                          │  │
│   │                                                                               │  │
│   │   Partitioned by month for query performance                                 │  │
│   │   Retention: 1 year (configurable)                                           │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/audit/retrieval.py

class RetrievalLogger:
    async def log_retrieval(
        self,
        user_id: str,
        query: str,
        query_embedding_hash: str,
        documents_retrieved: List[dict],
        documents_used: List[dict],
        response_generated: bool,
        retrieval_time_ms: int,
        session_id: str = None,
        metadata: dict = None
    ) -> str:
        """Log a retrieval event. Returns log ID."""
        
    async def get_retrieval_log(
        self,
        log_id: str
    ) -> dict:
        """Get specific retrieval log entry."""
        
    async def query_logs(
        self,
        user_id: str = None,
        document_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[dict]:
        """Query retrieval logs with filters."""
        
    async def get_document_access_stats(
        self,
        document_id: str
    ) -> dict:
        """Get access statistics for a document."""
        
    async def export_audit_trail(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> bytes:
        """Export audit trail for compliance."""
```

### Log Entry Format (Standard)

```python
{
    "id": "ral-abc123",
    "timestamp": "2025-01-01T10:00:00.000Z",
    "user_id": "user-xyz789",
    "session_id": "sess-def456",
    "query": {
        "text": "What is the refund policy?",
        "embedding_hash": "sha256:abc..."
    },
    "retrieval": {
        "namespace": "policies",
        "documents_retrieved": [
            {"id": "doc-1", "score": 0.92, "accessed": true},
            {"id": "doc-2", "score": 0.85, "accessed": true},
            {"id": "doc-3", "score": 0.78, "accessed": false, "reason": "acl_denied"}
        ],
        "latency_ms": 45
    },
    "response": {
        "generated": true,
        "documents_used": ["doc-1", "doc-2"],
        "citations": 3
    },
    "metadata": {
        "ip_address": "10.0.0.1",
        "user_agent": "GoAI-Console/1.0"
    }
}
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `retention_days` | How long to keep logs | `365` | 30-3650 |
| `log_query_text` | Store full query text | `true` | true/false |
| `log_response_hash` | Store response hash | `true` | true/false |
| `partition_by` | Table partitioning | `month` | day/week/month |
| `async_logging` | Non-blocking logging | `true` | true/false |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Schema** | Standard fields | Compliance requirements |
| **Storage** | PostgreSQL | Query/export capability |
| **Timestamp format** | ISO 8601 UTC | Consistency |
| **User ID tracking** | Always captured | Audit requirement |
| **Document access** | Always captured | Compliance requirement |
| **Embedding hash** | SHA256 | Query deduplication |

---

## 6. 📄 Ingestion Pipeline

### Purpose

The Ingestion Pipeline handles **document processing** from upload to vector storage. It standardizes text extraction, chunking, and metadata management across all document types.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               Ingestion Pipeline                                     │
│                                                                                      │
│   Document Upload                                                                    │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                          1. Validation                                        │  │
│   │                                                                               │  │
│   │   • File size check (max 50MB)                                               │  │
│   │   • File type validation                                                     │  │
│   │   • Virus scan (if enabled)                                                  │  │
│   │   • Duplicate detection (content hash)                                       │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                          2. Text Extraction                                   │  │
│   │                                                                               │  │
│   │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │  │
│   │   │   PDF   │ │  DOCX   │ │  XLSX   │ │  PPTX   │ │  HTML   │              │  │
│   │   │ PyMuPDF │ │ docx    │ │openpyxl │ │ pptx    │ │   BS4   │              │  │
│   │   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘              │  │
│   │                                                                               │  │
│   │   Output: Raw text with page/section markers                                 │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                          3. Chunking                                          │  │
│   │                                                                               │  │
│   │   Strategy: Semantic (sentence boundaries)                                   │  │
│   │   Chunk size: 512 tokens                                                     │  │
│   │   Overlap: 50 tokens                                                         │  │
│   │                                                                               │  │
│   │   Each chunk includes:                                                       │  │
│   │   • chunk_index                                                              │  │
│   │   • page_number (if available)                                               │  │
│   │   • section_title (if available)                                             │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                          4. Embedding                                         │  │
│   │                                                                               │  │
│   │   Model: BGE-large-en-v1.5                                                   │  │
│   │   Dimensions: 1024                                                           │  │
│   │   Batch size: 32                                                             │  │
│   │   Normalization: L2                                                          │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                          5. Storage                                           │  │
│   │                                                                               │  │
│   │   • Vectors → FAISS index                                                    │  │
│   │   • Metadata → PostgreSQL                                                    │  │
│   │   • Original file → MinIO/S3                                                 │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/ingestion/pipeline.py

class IngestionPipeline:
    async def ingest_file(
        self,
        file: UploadFile,
        metadata: dict = None,
        namespace: str = "global",
        owner_id: str = None
    ) -> dict:
        """Ingest uploaded file."""
        
    async def ingest_text(
        self,
        content: str,
        filename: str,
        metadata: dict = None,
        namespace: str = "global",
        owner_id: str = None
    ) -> dict:
        """Ingest raw text content."""
        
    async def ingest_url(
        self,
        url: str,
        metadata: dict = None,
        namespace: str = "global",
        owner_id: str = None
    ) -> dict:
        """Ingest content from URL."""
        
    async def get_ingestion_status(
        self,
        job_id: str
    ) -> dict:
        """Check status of async ingestion."""
        
    def list_supported_types(self) -> List[str]:
        """List supported file types."""
```

### Ingestion Result Format (Standard)

```python
{
    "job_id": "ingest-abc123",
    "status": "completed",  # or "processing", "failed"
    "document_id": "doc-xyz789",
    "filename": "policy.pdf",
    "file_type": "application/pdf",
    "file_size_bytes": 1024000,
    "content_hash": "sha256:def...",
    "chunks_created": 25,
    "total_tokens": 12500,
    "processing_time_ms": 3500,
    "metadata": {
        "pages": 10,
        "title": "Company Policy",
        "author": "HR Department"
    },
    "namespace": "policies",
    "owner_id": "user-abc"
}
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `max_file_size_mb` | Maximum file size | `50` | 1-500 |
| `chunk_size` | Tokens per chunk | `512` | 128-2048 |
| `chunk_overlap` | Overlap tokens | `50` | 0-256 |
| `ocr_enabled` | OCR for scanned PDFs | `true` | true/false |
| `ocr_language` | OCR language | `eng` | ISO 639-2 |
| `extract_tables` | Extract tables from docs | `true` | true/false |
| `async_processing` | Background processing | `true` | true/false |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Supported types** | PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, CSV | Tested parsers |
| **Chunking strategy** | Semantic (sentence) | Best retrieval quality |
| **Embedding model** | BGE-large-en-v1.5 | Consistency with vector store |
| **Metadata fields** | Standard set | ACL and audit integration |
| **Content hash** | SHA256 | Duplicate detection |
| **Result format** | See above | Consistent across platform |

---

## 7. 📨 Streaming Engine

### Purpose

The Streaming Engine provides **real-time token streaming** for LLM responses using Server-Sent Events (SSE). It handles connection management, backpressure, and error recovery.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               Streaming Engine                                       │
│                                                                                      │
│   Client Request (POST /stream/chat)                                                │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                        Connection Setup                                       │  │
│   │                                                                               │  │
│   │   • Validate auth token                                                      │  │
│   │   • Check rate limits                                                        │  │
│   │   • Allocate stream ID                                                       │  │
│   │   • Set headers: Content-Type: text/event-stream                             │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                        Event Generator                                        │  │
│   │                                                                               │  │
│   │   1. sources       ──▶  Retrieved documents                                  │  │
│   │   2. context       ──▶  Memory/history context                               │  │
│   │   3. thinking      ──▶  Agent reasoning (optional)                           │  │
│   │   4. token         ──▶  Generated tokens (many)                              │  │
│   │   5. tool_call     ──▶  Agent tool usage                                     │  │
│   │   6. tool_result   ──▶  Tool execution result                                │  │
│   │   7. done          ──▶  Completion with metadata                             │  │
│   │   8. error         ──▶  Error if occurred                                    │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│        │                                                                             │
│        ▼                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                        SSE Transport                                          │  │
│   │                                                                               │  │
│   │   data: {"type": "sources", "data": [...]}                                   │  │
│   │                                                                               │  │
│   │   data: {"type": "token", "data": "Hello"}                                   │  │
│   │                                                                               │  │
│   │   data: {"type": "token", "data": " World"}                                  │  │
│   │                                                                               │  │
│   │   data: {"type": "done", "data": {"model": "llama-70b", "tokens": 150}}      │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│   Features:                                                                          │
│   • Automatic reconnection hints                                                    │
│   • Heartbeat every 15s (keep-alive)                                               │
│   • Graceful cancellation on client disconnect                                      │
│   • Token counting and quota tracking                                               │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/streaming/engine.py

class StreamingEngine:
    async def stream_chat(
        self,
        query: str,
        model: str = "llama-70b",
        conversation_id: str = None,
        rag_mode: str = "all",
        document_ids: List[str] = None,
        user_id: str = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[dict, None]:
        """Stream RAG chat response."""
        
    async def stream_agent(
        self,
        task: str,
        tools: List[str],
        model: str = "llama-70b",
        user_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """Stream agent execution."""
        
    async def stream_completion(
        self,
        prompt: str,
        model: str = "llama-70b",
        max_tokens: int = 2048,
        user_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """Stream raw completion."""

# FastAPI endpoint
@router.post("/stream/chat")
async def stream_chat(request: StreamChatRequest):
    return StreamingResponse(
        streaming_engine.stream_chat(**request.dict()),
        media_type="text/event-stream"
    )
```

### Event Types (Standard)

```python
# 1. Sources event (first)
{"type": "sources", "data": [
    {"id": "doc-1", "filename": "policy.pdf", "page": 5, "score": 0.92}
]}

# 2. Context event (optional)
{"type": "context", "data": {
    "memories": ["User prefers Python"],
    "history_length": 5
}}

# 3. Thinking event (agents only)
{"type": "thinking", "data": "I need to search for recent news..."}

# 4. Token events (many)
{"type": "token", "data": "The"}
{"type": "token", "data": " refund"}
{"type": "token", "data": " policy"}

# 5. Tool call event (agents only)
{"type": "tool_call", "data": {
    "tool": "web_search",
    "input": "latest AI news"
}}

# 6. Tool result event (agents only)
{"type": "tool_result", "data": {
    "tool": "web_search",
    "output": "Results: ..."
}}

# 7. Done event (last)
{"type": "done", "data": {
    "model": "llama-70b",
    "usage": {"prompt_tokens": 500, "completion_tokens": 150},
    "finish_reason": "stop",
    "latency_ms": 2500
}}

# 8. Error event (if error)
{"type": "error", "data": {
    "code": "rate_limited",
    "message": "Rate limit exceeded"
}}
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `heartbeat_interval` | Keep-alive interval | `15s` | 5-60 |
| `timeout_seconds` | Stream timeout | `300` | 30-3600 |
| `buffer_size` | Token buffer size | `100` | 10-1000 |
| `include_sources` | Include RAG sources | `true` | true/false |
| `include_context` | Include memory context | `true` | true/false |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Protocol** | SSE (text/event-stream) | Browser compatibility |
| **Event format** | `{"type", "data"}` | Client parsing |
| **Event types** | 8 standard types | UI expects these |
| **Done event** | Always last | Stream termination |
| **Error format** | `{code, message}` | Error handling |
| **Token counting** | Always included | Quota tracking |

---

## 8. 🧩 Multi-Agent Engine

### Purpose

The Multi-Agent Engine enables **collaborative AI agents** to work together on complex tasks. It handles agent orchestration, communication, and tool delegation.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               Multi-Agent Engine                                     │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                            Agent Roles                                        │  │
│   │                                                                               │  │
│   │   ┌──────────────┐                                                           │  │
│   │   │ Coordinator  │ ── Plans tasks, delegates, synthesizes results           │  │
│   │   └──────────────┘                                                           │  │
│   │          │                                                                    │  │
│   │   ┌──────┴──────┬──────────────┬──────────────┬──────────────┐              │  │
│   │   │             │              │              │              │              │  │
│   │   ▼             ▼              ▼              ▼              ▼              │  │
│   │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                   │  │
│   │   │Research│ │ Coder  │ │Analyst │ │ Writer │ │ Critic │                   │  │
│   │   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘                   │  │
│   │                                                                               │  │
│   │   Each agent has:                                                            │  │
│   │   • Specialized system prompt                                                │  │
│   │   • Allowed tools                                                            │  │
│   │   • Output format                                                            │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                        Collaboration Patterns                                 │  │
│   │                                                                               │  │
│   │   Sequential     ──▶  A → B → C → D                                          │  │
│   │   Parallel       ──▶  A,B,C → Merge → D                                      │  │
│   │   Debate         ──▶  A ↔ B (back and forth) → Synthesis                     │  │
│   │   Hierarchical   ──▶  Coordinator delegates to specialists                   │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                         Available Tools                                       │  │
│   │                                                                               │  │
│   │   • web_search      - Search the internet                                    │  │
│   │   • calculator      - Math computations                                      │  │
│   │   • execute_python  - Run Python code                                        │  │
│   │   • rag_query       - Search knowledge base                                  │  │
│   │   • url_fetcher     - Fetch web page content                                 │  │
│   │   • datetime        - Get current date/time                                  │  │
│   │   • json_parser     - Parse/format JSON                                      │  │
│   │                                                                               │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API

```python
# Location: core/agents/multi_agent.py

class MultiAgentEngine:
    async def run_team(
        self,
        task: str,
        team: str = "research",      # Team preset
        pattern: str = "hierarchical", # Collaboration pattern
        model: str = "llama-70b",
        user_id: str = None,
        max_iterations: int = 10
    ) -> AsyncGenerator[dict, None]:
        """Run multi-agent team on task (streaming)."""
        
    async def run_agent(
        self,
        task: str,
        role: str = "researcher",    # Single agent role
        tools: List[str] = None,
        model: str = "llama-70b",
        user_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """Run single agent on task (streaming)."""
        
    def list_roles(self) -> List[dict]:
        """List available agent roles."""
        
    def list_teams(self) -> List[dict]:
        """List available team presets."""
        
    def list_tools(self) -> List[dict]:
        """List available tools."""
        
    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: dict
    ) -> None:
        """Register custom tool."""
```

### Agent Roles (Standard)

| Role | Purpose | Default Tools | Output Format |
|------|---------|---------------|---------------|
| **Coordinator** | Plans, delegates, synthesizes | None (delegates) | Plan + Summary |
| **Researcher** | Gathers information | web_search, url_fetcher, rag_query | Findings report |
| **Coder** | Writes and reviews code | execute_python, json_parser | Code + explanation |
| **Analyst** | Analyzes data | calculator, json_parser | Analysis report |
| **Writer** | Creates content | None | Formatted content |
| **Critic** | Reviews and critiques | None | Critique + suggestions |

### Team Presets (Standard)

| Team | Roles | Pattern | Use Case |
|------|-------|---------|----------|
| **research** | Coordinator, 2x Researcher, Writer | Parallel | Information gathering |
| **development** | Coordinator, Coder, Critic | Sequential | Code generation |
| **analysis** | Coordinator, Researcher, Analyst, Writer | Hierarchical | Data analysis |
| **content** | Coordinator, Researcher, Writer, Critic | Debate | Content creation |

### Streaming Events (Standard)

```python
# Agent thinking
{"type": "thinking", "agent": "researcher", "data": "Searching for..."}

# Tool usage
{"type": "tool_call", "agent": "researcher", "data": {
    "tool": "web_search", "input": "query"
}}

# Tool result
{"type": "tool_result", "agent": "researcher", "data": {
    "tool": "web_search", "output": "Results..."
}}

# Agent message (to other agents)
{"type": "message", "from": "researcher", "to": "coordinator", "data": "Found..."}

# Agent output
{"type": "output", "agent": "researcher", "data": "Final findings..."}

# Team complete
{"type": "done", "data": {
    "final_output": "...",
    "agents_used": ["coordinator", "researcher", "writer"],
    "tools_called": 5,
    "total_tokens": 5000
}}
```

### ✅ Configurable

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `max_iterations` | Max agent iterations | `10` | 1-50 |
| `tool_timeout` | Tool execution timeout | `30s` | 5-300 |
| `allow_external_tools` | Enable external API tools | `false` | true/false |
| `custom_tools` | Additional tool definitions | `[]` | Tool list |
| `custom_roles` | Additional role definitions | `[]` | Role list |

### ❌ NOT Configurable (Standard)

| Standard | Value | Reason |
|----------|-------|--------|
| **Core roles** | 6 standard roles | Platform-wide patterns |
| **Core tools** | 7 built-in tools | Security & reliability |
| **Team presets** | 4 standard teams | Tested configurations |
| **Patterns** | 4 collaboration types | Orchestration logic |
| **Event format** | See above | UI expects these |
| **Tool interface** | `run(input) -> output` | Consistency |

---

## Summary Matrix

| Module | Configurable | NOT Configurable |
|--------|--------------|------------------|
| **LLM Router** | Models, timeouts, fallback | Interface, response format, metrics |
| **Orchestrator** | Workflows, timeouts, actions | YAML format, built-in actions, result format |
| **Vector Store** | Embedding model, index params | Dimensions, metric, result format |
| **Auth & RBAC** | Provider, expiry, password rules | Roles, permissions, token format |
| **Retrieval Logging** | Retention, partitioning | Schema, storage, required fields |
| **Ingestion Pipeline** | File limits, chunking params | Supported types, chunk strategy, metadata |
| **Streaming Engine** | Timeouts, buffers | Protocol, event types, done event |
| **Multi-Agent** | Iterations, custom tools/roles | Core roles, core tools, team presets |

---

**GoAI Sovereign Platform v1** — Core Modules Specification 🏛️


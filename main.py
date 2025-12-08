import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1 import ingest, retrieve, sql_agent, orchestrator, validator, sentiment, rag, performance, telemetry, llm, stream, upload, agents, auth, export, prompts, feedback, multi_agent, memory, ebc_tickets, customer_kyc, ocr, activity, evals, mcp, triggers, meeting_notes, approvals, observability, guardrails


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    from core.telemetry import logger
    logger.info("🚀 Starting GoAI Platform...")
    
    # Initialize task queue
    from core.performance import get_task_queue
    task_queue = await get_task_queue()
    logger.info("✅ Task queue ready", workers=4)
    
    # Initialize cache
    from core.cache import cache
    logger.info("✅ Cache ready", backend=cache.config.backend)
    
    # Initialize telemetry
    logger.info("✅ Telemetry enabled", features=["metrics", "tracing", "logging"])
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await task_queue.stop()
    logger.info("✅ Cleanup complete")


app = FastAPI(
    title="GoAI Sovereign Platform v1",
    description="Sovereign AI Platform with LLM routing, vector retrieval, and orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Telemetry middleware (must be added first)
from core.telemetry import add_telemetry
add_telemetry(app)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Ingestion"])
app.include_router(retrieve.router, prefix="/api/v1/retrieve", tags=["Retrieval"])
app.include_router(sql_agent.router, prefix="/api/v1/sql", tags=["SQL Agent"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
app.include_router(validator.router, prefix="/api/v1/validator", tags=["Validator"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["Sentiment"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(performance.router, prefix="/api/v1/performance", tags=["Performance"])
app.include_router(telemetry.router, prefix="/api/v1/telemetry", tags=["Telemetry"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["LLM"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["Streaming"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["File Upload"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["AI Agents"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["Prompt Library"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(multi_agent.router, prefix="/api/v1/multi-agent", tags=["Multi-Agent"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["User Memory"])
app.include_router(ebc_tickets.router, prefix="/api/v1/ebc-tickets", tags=["EBC Tickets"])
app.include_router(customer_kyc.router, prefix="/api/v1", tags=["Customer KYC"])
app.include_router(ocr.router, prefix="/api/v1", tags=["OCR"])
app.include_router(activity.router, prefix="/api/v1", tags=["Activity"])
app.include_router(evals.router, prefix="/api/v1/evals", tags=["AI Evaluations"])
app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["MCP Protocol"])
app.include_router(triggers.router, prefix="/api/v1/triggers", tags=["Triggers & Webhooks"])
app.include_router(meeting_notes.router, prefix="/api/v1/meeting-notes", tags=["Meeting Notes"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Human-in-the-Loop"])
app.include_router(observability.router, prefix="/api/v1/observability", tags=["Agent Observability"])
app.include_router(guardrails.router, prefix="/api/v1/guardrails", tags=["AI Guardrails"])


@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": "GoAI Sovereign Platform v1",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/config")
def config_status():
    """Check configuration status"""
    return {
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "environment": os.getenv("ENV", "dev")
    }

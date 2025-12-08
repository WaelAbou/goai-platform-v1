"""
Meeting Notes API - Summarize and analyze meeting notes.

PLATFORM INTEGRATION EXAMPLE:
This module demonstrates how to integrate with multiple platform layers:
- LLM Router: AI-powered extraction
- RAG Engine: Store/search meetings
- Memory Service: Track action items per user
- Sentiment Engine: Analyze meeting tone

Endpoints:
- POST /summarize - Generate full meeting summary (with optional integrations)
- POST /action-items - Extract only action items
- POST /format/markdown - Format summary as Markdown
- GET /search - Search past meetings (via RAG)
- GET /my-tasks - Get user's action items (via Memory)
- POST /workflow - Run complete meeting workflow (via Orchestrator)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Core platform imports
from core.llm import llm_router

# Module imports
from modules.meeting_notes import meeting_notes_engine, Priority, MeetingSummary, ActionItem
from modules.rag import rag_engine
from modules.sentiment import sentiment_engine

router = APIRouter()


# ============================================
# Wire Up Platform Integrations
# ============================================

# 1. LLM Router - Required for AI features
meeting_notes_engine.set_llm_router(llm_router)

# 2. RAG Engine - For storing and searching meetings
meeting_notes_engine.set_rag_engine(rag_engine)

# 3. Sentiment Engine - For meeting tone analysis
meeting_notes_engine.set_sentiment_engine(sentiment_engine)

# Note: Memory service requires HTTP client or direct import
# We'll use the memory API endpoints instead for this example


# ============================================
# Request/Response Models
# ============================================

class SummarizeRequest(BaseModel):
    """Request to summarize meeting notes with platform integrations."""
    content: str = Field(..., description="Raw meeting notes text", min_length=10)
    model: Optional[str] = Field("gpt-4o-mini", description="LLM model to use")
    include_priorities: bool = Field(True, description="Auto-prioritize action items")
    
    # Platform integration options
    analyze_sentiment: bool = Field(False, description="Analyze meeting tone (uses Sentiment module)")
    store_in_rag: bool = Field(False, description="Store in RAG for future search")
    save_action_items: bool = Field(False, description="Save action items to user memory")
    user_id: Optional[str] = Field(None, description="User ID for memory storage")


class ActionItemResponse(BaseModel):
    """Action item in response."""
    id: str
    task: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"


class SentimentResponse(BaseModel):
    """Sentiment analysis result."""
    overall: str
    score: float = 0
    emotions: List[str] = []


class SummaryResponse(BaseModel):
    """Meeting summary response."""
    id: str
    title: str
    date: str
    participants: List[str]
    summary: str
    action_items: List[ActionItemResponse]
    key_decisions: List[str]
    next_steps: List[str]
    sentiment: Optional[SentimentResponse] = None
    metadata: Dict[str, Any] = {}
    
    # Integration status
    stored_in_rag: bool = False
    action_items_saved: bool = False


class ActionItemsRequest(BaseModel):
    """Request to extract action items only."""
    content: str = Field(..., min_length=10)
    model: Optional[str] = "gpt-4o-mini"


class FormatRequest(BaseModel):
    """Request to format summary as Markdown."""
    summary: SummaryResponse


class SearchRequest(BaseModel):
    """Request to search past meetings."""
    query: str = Field(..., min_length=2)
    top_k: int = Field(5, ge=1, le=20)


# ============================================
# API Endpoints
# ============================================

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_meeting(request: SummarizeRequest):
    """
    Generate a comprehensive meeting summary with platform integrations.
    
    INTEGRATIONS:
    - `analyze_sentiment=true`: Uses Sentiment module to analyze meeting tone
    - `store_in_rag=true`: Stores meeting in RAG for future search
    - `save_action_items=true`: Saves action items to user's memory (requires user_id)
    
    Example:
    ```
    POST /api/v1/meeting-notes/summarize
    {
        "content": "Meeting with John and Sarah about Q4 goals...",
        "analyze_sentiment": true,
        "store_in_rag": true,
        "save_action_items": true,
        "user_id": "user123"
    }
    ```
    """
    try:
        summary = await meeting_notes_engine.summarize(
            notes=request.content,
            model=request.model,
            include_priorities=request.include_priorities,
            analyze_sentiment=request.analyze_sentiment,
            store_in_rag=request.store_in_rag,
            save_action_items=request.save_action_items,
            user_id=request.user_id
        )
        
        # Build response
        sentiment_data = None
        if summary.sentiment:
            sentiment_data = SentimentResponse(
                overall=summary.sentiment.get("overall", "unknown"),
                score=summary.sentiment.get("score", 0),
                emotions=summary.sentiment.get("emotions", [])
            )
        
        return SummaryResponse(
            id=summary.id,
            title=summary.title,
            date=summary.date,
            participants=summary.participants,
            summary=summary.summary,
            action_items=[
                ActionItemResponse(
                    id=item.id,
                    task=item.task,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    priority=item.priority.value,
                    status=item.status
                )
                for item in summary.action_items
            ],
            key_decisions=summary.key_decisions,
            next_steps=summary.next_steps,
            sentiment=sentiment_data,
            metadata=summary.metadata,
            stored_in_rag=request.store_in_rag,
            action_items_saved=request.save_action_items and request.user_id is not None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/action-items")
async def extract_action_items(request: ActionItemsRequest):
    """
    Quick extraction of just action items.
    
    Example:
    ```
    POST /api/v1/meeting-notes/action-items
    {
        "content": "TODO: John to review the proposal by Friday..."
    }
    ```
    """
    try:
        items = await meeting_notes_engine.extract_action_items_only(
            notes=request.content,
            model=request.model
        )
        
        return {
            "count": len(items),
            "action_items": [
                {
                    "id": item.id,
                    "task": item.task,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "priority": item.priority.value
                }
                for item in items
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/format/markdown")
async def format_as_markdown(request: FormatRequest):
    """
    Format a summary as Markdown.
    """
    # Reconstruct the summary object
    summary = MeetingSummary(
        id=request.summary.id,
        title=request.summary.title,
        date=request.summary.date,
        participants=request.summary.participants,
        summary=request.summary.summary,
        action_items=[
            ActionItem(
                id=item.id,
                task=item.task,
                assignee=item.assignee,
                due_date=item.due_date,
                priority=Priority(item.priority)
            )
            for item in request.summary.action_items
        ],
        key_decisions=request.summary.key_decisions,
        next_steps=request.summary.next_steps,
        sentiment=request.summary.sentiment.dict() if request.summary.sentiment else None
    )
    
    markdown = meeting_notes_engine.format_summary_markdown(summary)
    
    return {
        "markdown": markdown,
        "character_count": len(markdown)
    }


@router.get("/search")
async def search_meetings(
    query: str = Query(..., min_length=2, description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results")
):
    """
    Search past meetings using RAG.
    
    INTEGRATION: Uses RAG module for semantic search across stored meetings.
    
    Example:
    ```
    GET /api/v1/meeting-notes/search?query=kubernetes migration&top_k=5
    ```
    """
    try:
        results = await meeting_notes_engine.search_meetings(
            query=query,
            top_k=top_k
        )
        
        return {
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings")
async def list_meetings(limit: int = Query(10, ge=1, le=50)):
    """
    List recent meetings (from memory).
    """
    meetings = meeting_notes_engine.list_meetings(limit=limit)
    return {
        "count": len(meetings),
        "meetings": [m.to_dict() for m in meetings]
    }


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    """
    Get a specific meeting by ID.
    """
    meeting = meeting_notes_engine.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.to_dict()


@router.get("/")
async def get_info():
    """
    Get information about the Meeting Notes API and its integrations.
    """
    return {
        "name": "Meeting Notes Summarizer",
        "version": "2.0.0",
        "description": "Extract action items and summaries from meeting notes",
        
        "endpoints": [
            {"path": "/summarize", "method": "POST", "description": "Full meeting summary with integrations"},
            {"path": "/action-items", "method": "POST", "description": "Extract action items only"},
            {"path": "/format/markdown", "method": "POST", "description": "Format as Markdown"},
            {"path": "/search", "method": "GET", "description": "Search past meetings (via RAG)"},
            {"path": "/meetings", "method": "GET", "description": "List recent meetings"},
            {"path": "/meetings/{id}", "method": "GET", "description": "Get specific meeting"}
        ],
        
        "platform_integrations": {
            "llm_router": {
                "status": "connected" if meeting_notes_engine.llm_router else "not configured",
                "description": "AI-powered extraction and summarization"
            },
            "rag_engine": {
                "status": "connected" if meeting_notes_engine.rag_engine else "not configured",
                "description": "Store and search meetings semantically"
            },
            "sentiment_engine": {
                "status": "connected" if meeting_notes_engine.sentiment_engine else "not configured",
                "description": "Analyze meeting tone and emotions"
            },
            "memory_service": {
                "status": "connected" if meeting_notes_engine.memory_service else "not configured",
                "description": "Persist action items per user"
            }
        },
        
        "features": [
            "Action item extraction with priorities",
            "Participant identification",
            "Executive summaries",
            "Sentiment analysis (optional)",
            "RAG storage for search (optional)",
            "User memory integration (optional)",
            "Markdown export"
        ],
        
        "supported_models": ["gpt-4o-mini", "gpt-4o", "gpt-4", "llama3.2", "mistral"]
    }

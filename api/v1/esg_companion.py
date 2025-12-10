"""
ESG Companion API

Chat interface for the ESG Companion AI assistant.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from modules.sustainability.esg_companion import esg_companion, ESGContext
from core.llm.router import LLMRouter

router = APIRouter()

# Initialize LLM Router
llm_router = LLMRouter()
llm_router.initialize()
esg_companion.set_llm_router(llm_router)

# Try to set RAG engine if available
try:
    from modules.rag.engine import rag_engine
    esg_companion.set_rag_engine(rag_engine)
except:
    pass


class ChatRequest(BaseModel):
    """Request to chat with ESG Companion."""
    message: str = Field(..., description="User's message")
    company_id: Optional[str] = Field(default="xyz-corp-001", description="Company ID")
    user_email: Optional[str] = Field(default="user@company.com", description="User email")
    include_context: Optional[bool] = Field(default=True, description="Include data context")
    model: Optional[str] = Field(default="gpt-4o-mini", description="LLM model to use")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation ID to continue")


class ChatResponse(BaseModel):
    """Response from ESG Companion."""
    response: str
    status: str
    tool_results: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    suggestions: Optional[List[str]] = None
    conversation_id: Optional[str] = None


class QueryRequest(BaseModel):
    """Request for direct data queries."""
    query_type: str = Field(..., description="Type: emissions, documents, stats, calculate")
    params: Optional[Dict[str, Any]] = Field(default={}, description="Query parameters")


# ==================== ENDPOINTS ====================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_companion(request: ChatRequest):
    """
    💬 Chat with the ESG Companion.
    
    The companion can:
    - Answer questions about your emissions data
    - Search the sustainability knowledge base
    - Calculate CO2e for various activities
    - Provide ESG recommendations
    
    Pass conversation_id to continue an existing conversation.
    
    Example messages:
    - "What's my total carbon footprint?"
    - "Show me emissions by category"
    - "How can I reduce Scope 3 emissions?"
    - "Calculate emissions for 500 miles of driving"
    """
    context = ESGContext(
        company_id=request.company_id,
        user_email=request.user_email,
        role="admin"
    )
    
    result = await esg_companion.chat(
        message=request.message,
        context=context,
        model=request.model,
        include_data_context=request.include_context,
        conversation_id=request.conversation_id
    )
    
    # Add suggestions for follow-up
    result['suggestions'] = esg_companion.get_suggestions()[:4]
    
    return result


# ==================== CONVERSATION MANAGEMENT ====================

@router.get("/conversations")
async def get_conversations(
    user_id: str = "user@company.com",
    limit: int = 20
):
    """
    📜 Get user's conversation history.
    
    Returns list of past conversations with titles and last messages.
    """
    conversations = esg_companion.get_conversations(user_id, limit)
    return {
        "conversations": conversations,
        "count": len(conversations)
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    💬 Get messages from a specific conversation.
    """
    messages = esg_companion.get_conversation_messages(conversation_id)
    if not messages:
        raise HTTPException(404, "Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "count": len(messages)
    }


@router.post("/conversations")
async def create_conversation(
    user_id: str = "user@company.com",
    company_id: str = "xyz-corp-001",
    title: Optional[str] = None
):
    """
    ➕ Create a new conversation.
    """
    conv_id = esg_companion.create_conversation(user_id, company_id, title)
    return {
        "conversation_id": conv_id,
        "message": "New conversation created"
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    🗑️ Delete a conversation and all its messages.
    """
    deleted = esg_companion.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(404, "Conversation not found")
    
    return {
        "message": "Conversation deleted",
        "conversation_id": conversation_id
    }


@router.get("/suggestions")
async def get_suggestions():
    """
    💡 Get conversation starter suggestions.
    """
    return {
        "suggestions": esg_companion.get_suggestions(),
        "categories": {
            "emissions": [
                "What's my total carbon footprint?",
                "Show emissions by category",
                "Compare Scope 1, 2, and 3 emissions"
            ],
            "documents": [
                "What documents are pending review?",
                "Show my recent uploads",
                "What's my document approval rate?"
            ],
            "knowledge": [
                "What are the GRI 305 requirements?",
                "Explain TCFD recommendations",
                "What are Science Based Targets?"
            ],
            "actions": [
                "How can I reduce my emissions?",
                "What should I prioritize?",
                "Calculate emissions for an activity"
            ]
        }
    }


@router.post("/query")
async def direct_query(request: QueryRequest):
    """
    🔍 Execute a direct data query.
    
    Query types:
    - emissions: Get emissions data
    - documents: Search documents
    - stats: Get company statistics
    - calculate: Calculate CO2e
    """
    query_type = request.query_type.lower()
    params = request.params or {}
    
    if query_type == "emissions":
        return esg_companion.query_emissions(**params)
    elif query_type == "documents":
        return esg_companion.query_documents(**params)
    elif query_type == "stats":
        return esg_companion.get_company_stats(**params)
    elif query_type == "calculate":
        if 'activity_type' not in params or 'value' not in params or 'unit' not in params:
            raise HTTPException(400, "Calculate requires: activity_type, value, unit")
        return esg_companion.calculate_emissions(
            params['activity_type'],
            params['value'],
            params['unit']
        )
    else:
        raise HTTPException(400, f"Unknown query type: {query_type}")


@router.delete("/history")
async def clear_history():
    """
    🗑️ Clear conversation history.
    """
    esg_companion.clear_history()
    return {"status": "success", "message": "Conversation history cleared"}


@router.get("/status")
async def get_status():
    """
    ℹ️ Get ESG Companion status.
    """
    return {
        "status": "online",
        "llm_configured": esg_companion.llm_router is not None,
        "rag_configured": esg_companion.rag_engine is not None,
        "history_length": len(esg_companion.conversation_history),
        "capabilities": [
            "Chat about emissions data",
            "Query company statistics",
            "Calculate CO2e emissions",
            "Search knowledge base",
            "Guide through platform features",
            "Provide recommendations"
        ]
    }


@router.get("/help")
async def get_system_help(topic: Optional[str] = None):
    """
    📚 Get help about platform features.
    
    Topics: upload, submissions, review, analytics, companion
    """
    return esg_companion.get_system_help(topic)


@router.get("/document-status")
async def get_document_status():
    """
    📋 Get current document status summary.
    """
    return esg_companion.get_document_status_summary()


"""
Platform Conversations API

Centralized API for managing conversations across ALL agents and use cases.
This enables conversation history to persist across different chatbots/assistants.

Endpoints:
- POST /conversations - Create new conversation
- GET /conversations - List conversations (filterable by agent_type)
- GET /conversations/{id} - Get conversation with messages
- DELETE /conversations/{id} - Delete conversation
- GET /conversations/stats - Get statistics
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from modules.conversations import conversation_service

router = APIRouter()


# ==================== MODELS ====================

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    user_id: str = Field(..., description="User identifier")
    agent_type: str = Field(default="custom", description="Type of agent (esg_companion, meeting_notes, etc.)")
    title: Optional[str] = Field(None, description="Conversation title")
    company_id: Optional[str] = Field(None, description="Company identifier")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Use-case specific context")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")


class SaveMessageRequest(BaseModel):
    """Request to save a message."""
    role: str = Field(..., description="Role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    tool_results: Optional[Dict[str, Any]] = Field(None, description="Tool call results")
    attachments: Optional[List[str]] = Field(None, description="Attachment IDs/URLs")


# ==================== ENDPOINTS ====================

@router.post("")
async def create_conversation(request: CreateConversationRequest):
    """
    ➕ Create a new conversation.
    
    Supports any agent type - this is the central conversation store for the platform.
    
    Example:
    ```json
    {
        "user_id": "user@company.com",
        "agent_type": "meeting_notes",
        "context_data": {"meeting_id": "mtg_123"}
    }
    ```
    """
    conv_id = conversation_service.create_conversation(
        user_id=request.user_id,
        agent_type=request.agent_type,
        title=request.title,
        company_id=request.company_id,
        context_data=request.context_data,
        tags=request.tags
    )
    
    return {
        "conversation_id": conv_id,
        "agent_type": request.agent_type,
        "message": "Conversation created"
    }


@router.get("")
async def list_conversations(
    user_id: str = Query(..., description="User ID to filter by"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    company_id: Optional[str] = Query(None, description="Filter by company"),
    include_archived: bool = Query(False, description="Include archived conversations"),
    limit: int = Query(50, le=100, description="Max results"),
    offset: int = Query(0, description="Pagination offset")
):
    """
    📜 List conversations with optional filters.
    
    Filter by agent_type to get conversations for a specific use case:
    - `esg_companion` - ESG/Sustainability chats
    - `meeting_notes` - Meeting notes assistant
    - `research_agent` - Research/analysis
    - `custom` - Custom agents
    """
    conversations = conversation_service.get_conversations(
        user_id=user_id,
        agent_type=agent_type,
        company_id=company_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset
    )
    
    return {
        "conversations": conversations,
        "count": len(conversations),
        "filters": {
            "user_id": user_id,
            "agent_type": agent_type,
            "company_id": company_id
        }
    }


@router.get("/agent-types")
async def list_agent_types():
    """
    📋 List supported agent types.
    """
    return {
        "agent_types": conversation_service.AGENT_TYPES,
        "description": {
            "esg_companion": "ESG/Sustainability expert chatbot",
            "meeting_notes": "Meeting notes summarizer",
            "research_agent": "Research and analysis assistant",
            "customer_support": "Customer support agent",
            "code_reviewer": "Code review assistant",
            "data_analyst": "Data analysis expert",
            "sql_expert": "SQL query expert",
            "project_planner": "Project planning assistant",
            "custom": "Custom/generic agent"
        }
    }


@router.get("/stats")
async def get_conversation_stats(
    user_id: Optional[str] = Query(None, description="Filter by user (omit for global stats)")
):
    """
    📊 Get conversation statistics.
    
    Shows total conversations and messages by agent type.
    """
    stats = conversation_service.get_stats(user_id=user_id)
    return stats


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    include_messages: bool = Query(True, description="Include messages in response"),
    message_limit: int = Query(100, description="Max messages to return")
):
    """
    💬 Get a conversation with its messages.
    """
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    
    result = {
        "id": conv.id,
        "user_id": conv.user_id,
        "agent_type": conv.agent_type,
        "title": conv.title,
        "company_id": conv.company_id,
        "context_data": conv.context_data,
        "tags": conv.tags,
        "message_count": conv.message_count,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
    }
    
    if include_messages:
        result["messages"] = conversation_service.get_messages(
            conversation_id,
            limit=message_limit
        )
    
    return result


@router.post("/{conversation_id}/messages")
async def save_message(conversation_id: str, request: SaveMessageRequest):
    """
    💾 Save a message to a conversation.
    
    Used by agents to persist their chat messages.
    """
    conv = conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    
    msg_id = conversation_service.save_message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        tool_results=request.tool_results,
        attachments=request.attachments
    )
    
    return {
        "message_id": msg_id,
        "conversation_id": conversation_id,
        "saved": True
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, permanent: bool = Query(False)):
    """
    🗑️ Delete a conversation.
    
    By default, archives the conversation (soft delete).
    Set permanent=true to permanently delete.
    """
    if permanent:
        deleted = conversation_service.delete_conversation(conversation_id)
    else:
        deleted = conversation_service.archive_conversation(conversation_id)
    
    if not deleted:
        raise HTTPException(404, "Conversation not found")
    
    return {
        "message": "Conversation deleted" if permanent else "Conversation archived",
        "conversation_id": conversation_id,
        "permanent": permanent
    }


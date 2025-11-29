from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from modules.rag import rag_engine, RAGMode
from modules.ingestion import ingestion_engine
from core.llm import llm_router
from core.vector import vector_retriever

router = APIRouter()

# Wire up the RAG engine with all components
rag_engine.set_llm_router(llm_router)
rag_engine.set_vector_retriever(vector_retriever)
rag_engine.set_ingestion_engine(ingestion_engine)


# Request/Response Models
class IngestRequest(BaseModel):
    content: str
    filename: Optional[str] = "document"
    metadata: Optional[Dict[str, Any]] = None


class IngestResponse(BaseModel):
    success: bool
    doc_id: str
    filename: str
    chunks: int
    status: str
    error: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    mode: Optional[str] = "simple"  # simple, conv, multi, step_back, hyde
    top_k: Optional[int] = 5
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    conversation_id: Optional[str] = None
    temperature: Optional[float] = 0.7
    filters: Optional[Dict[str, Any]] = None


class SourceModel(BaseModel):
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceModel]
    query: str
    model: str
    mode: str
    tokens_used: int = 0
    latency_ms: float = 0
    metadata: Dict[str, Any] = {}


class ConversationRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    query: str
    conversation_id: str
    top_k: Optional[int] = 5
    model: Optional[str] = None


# Endpoints
@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    """
    Ingest a document into the RAG knowledge base.
    The document will be chunked, embedded, and stored for retrieval.
    """
    result = await rag_engine.ingest(
        content=request.content,
        filename=request.filename,
        metadata=request.metadata
    )
    
    return IngestResponse(**result)


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system with a question.
    
    Modes:
    - simple: Basic retrieval + generation
    - conv: Conversational with history
    - multi: Query expansion for better coverage
    - step_back: Uses broader context
    - hyde: Hypothetical document embeddings
    """
    # Map string mode to enum
    mode_map = {
        "simple": RAGMode.SIMPLE,
        "conv": RAGMode.CONVERSATIONAL,
        "multi": RAGMode.MULTI_QUERY,
        "step_back": RAGMode.STEP_BACK,
        "hyde": RAGMode.HYDE
    }
    mode = mode_map.get(request.mode, RAGMode.SIMPLE)
    
    result = await rag_engine.query(
        query=request.query,
        mode=mode,
        top_k=request.top_k,
        model=request.model,
        system_prompt=request.system_prompt,
        filters=request.filters,
        conversation_id=request.conversation_id,
        temperature=request.temperature
    )
    
    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceModel(
                id=s.id,
                content=s.content,
                score=s.score,
                metadata=s.metadata
            )
            for s in result.sources
        ],
        query=result.query,
        model=result.model,
        mode=result.mode.value,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
        metadata=result.metadata
    )


@router.post("/stream")
async def stream_query(request: QueryRequest):
    """
    Stream RAG response with Server-Sent Events.
    Returns sources first, then streams the answer.
    """
    async def generate():
        async for event in rag_engine.stream_query(
            query=request.query,
            top_k=request.top_k,
            model=request.model
        ):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.post("/conversation", response_model=Dict[str, str])
async def create_conversation(request: ConversationRequest):
    """
    Create a new conversation for multi-turn RAG.
    """
    conv_id = rag_engine.create_conversation(metadata=request.metadata)
    return {"conversation_id": conv_id}


@router.post("/chat", response_model=QueryResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for conversational RAG.
    Maintains conversation history for context.
    """
    result = await rag_engine.query(
        query=request.query,
        mode=RAGMode.CONVERSATIONAL,
        top_k=request.top_k,
        model=request.model,
        conversation_id=request.conversation_id
    )
    
    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceModel(
                id=s.id,
                content=s.content,
                score=s.score,
                metadata=s.metadata
            )
            for s in result.sources
        ],
        query=result.query,
        model=result.model,
        mode=result.mode.value,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
        metadata=result.metadata
    )


@router.get("/conversations")
async def list_conversations():
    """
    List all conversations.
    """
    conversations = []
    
    for conv_id, conv in rag_engine.conversations.items():
        # Get preview from last user message
        last_query = ""
        last_response = ""
        for msg in reversed(conv.messages):
            if msg.role == "user" and not last_query:
                last_query = msg.content[:100]
            elif msg.role == "assistant" and not last_response:
                last_response = msg.content[:100]
            if last_query and last_response:
                break
        
        conversations.append({
            "id": conv_id,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.messages[-1].timestamp.isoformat() if conv.messages else conv.created_at.isoformat(),
            "message_count": len(conv.messages),
            "preview": last_query or "Empty conversation",
            "last_query": last_query,
            "last_response": last_response
        })
    
    # Sort by updated_at descending
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {
        "conversations": conversations,
        "total": len(conversations)
    }


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation history.
    """
    conv = rag_engine.get_conversation(conversation_id)
    
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": conv.id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "sources_count": len(msg.sources)
            }
            for msg in conv.messages
        ],
        "created_at": conv.created_at.isoformat(),
        "metadata": conv.metadata
    }


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation.
    """
    success = rag_engine.clear_conversation(conversation_id)
    return {"deleted": success}


@router.get("/stats")
async def get_stats():
    """
    Get RAG system statistics.
    """
    return rag_engine.get_stats()


@router.get("/documents")
async def list_documents(limit: int = 50, group_by_file: bool = True):
    """
    List all ingested documents in the vector store.
    
    Args:
        limit: Maximum number of documents to return
        group_by_file: If True, group chunks by filename/document_id (default: True)
    """
    if rag_engine.vector_retriever is None:
        return {"documents": [], "count": 0}
    
    if group_by_file:
        # Group chunks by filename/document_id
        doc_groups = {}
        for chunk_id, doc in rag_engine.vector_retriever.documents.items():
            # Use filename or document_id from metadata, fallback to chunk prefix
            filename = doc.metadata.get("filename") or doc.metadata.get("document_id")
            if not filename:
                # Try to extract from chunk_id (format: docid_chunknum)
                filename = chunk_id.rsplit("_", 1)[0] if "_" in chunk_id else chunk_id
            
            if filename not in doc_groups:
                doc_groups[filename] = {
                    "id": filename,
                    "filename": filename,
                    "chunks": [],
                    "chunk_count": 0,
                    "total_length": 0,
                    "preview": ""
                }
            
            doc_groups[filename]["chunks"].append(chunk_id)
            doc_groups[filename]["chunk_count"] += 1
            doc_groups[filename]["total_length"] += len(doc.content)
            
            # Store preview from first chunk
            if not doc_groups[filename]["preview"]:
                doc_groups[filename]["preview"] = doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
        
        # Create display-friendly names for UUID-based filenames
        docs = []
        for doc in list(doc_groups.values())[:limit]:
            # If filename is a UUID, create a friendlier name from preview
            if len(doc["filename"]) == 36 and doc["filename"].count("-") == 4:
                preview_words = doc["preview"][:50].split()[:5]
                display_name = " ".join(preview_words) + "..."
                doc["display_name"] = display_name
            else:
                doc["display_name"] = doc["filename"]
            docs.append(doc)
        
        return {
            "documents": docs,
            "count": len(docs),
            "total": len(doc_groups)
        }
    else:
        # Return individual chunks
        docs = []
        for doc_id, doc in list(rag_engine.vector_retriever.documents.items())[:limit]:
            docs.append({
                "id": doc_id,
                "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                "content_length": len(doc.content),
                "metadata": doc.metadata,
                "chunk_index": doc.chunk_index
            })
        
        return {
            "documents": docs,
            "count": len(docs),
            "total": len(rag_engine.vector_retriever.documents)
        }


@router.post("/ask")
async def simple_ask(query: str, top_k: int = 5):
    """
    Simple ask endpoint - just pass a question.
    """
    result = await rag_engine.query(
        query=query,
        top_k=top_k
    )
    
    return {
        "answer": result.answer,
        "sources": [
            {
                "content": s.content[:200] + "..." if len(s.content) > 200 else s.content,
                "score": round(s.score, 3)
            }
            for s in result.sources
        ]
    }


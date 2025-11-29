"""
Streaming API - Real-time token streaming for chat responses.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio

from core.llm import llm_router, get_ollama
from modules.rag import rag_engine
from api.v1 import memory as memory_api

router = APIRouter()


async def get_memory_context(user_id: str = "default", max_tokens: int = 500) -> str:
    """Fetch user memory context for injection into prompts."""
    try:
        result = await memory_api.get_memory_context(user_id=user_id, max_tokens=max_tokens)
        return result.get("context", "")
    except Exception:
        return ""


class StreamChatRequest(BaseModel):
    """Stream chat request with conversation and RAG mode support."""
    query: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    top_k: int = 5
    include_history: bool = True
    rag_mode: str = "all"  # "none", "all", "selected"
    document_ids: Optional[List[str]] = None
    include_memory: bool = True  # Include user memory context
    user_id: str = "default"


class StreamCompletionRequest(BaseModel):
    """Stream completion request."""
    prompt: str
    model: Optional[str] = None
    provider: Optional[str] = None
    max_tokens: int = 500
    temperature: float = 0.7


def get_document_awareness_prompt(rag_mode: str, document_ids: Optional[List[str]] = None) -> str:
    """Build system prompt section about available documents."""
    
    # Get all documents from RAG engine
    all_docs = rag_engine.list_documents()
    
    if rag_mode == "none":
        return """
You are a helpful AI assistant. You do NOT have access to any documents or files in this conversation.
Answer questions based on your general knowledge. If the user asks about specific documents or files, 
let them know they need to switch to "All Docs" or "Select" mode to query their documents.
"""
    
    if not all_docs:
        return """
You are a helpful AI assistant with document retrieval capabilities, but no documents have been uploaded yet.
If the user asks about documents, suggest they upload some files first through the Documents page.
"""
    
    # Build document list
    if rag_mode == "selected" and document_ids:
        # Filter to selected docs
        docs = [d for d in all_docs if d.get("id") in document_ids]
        doc_intro = f"You have access to {len(docs)} selected document(s):"
    else:
        docs = all_docs
        doc_intro = f"You have access to {len(docs)} document(s) in the knowledge base:"
    
    doc_list = []
    for doc in docs[:20]:  # Limit to 20 docs to avoid token overflow
        filename = doc.get("filename", doc.get("id", "unknown"))
        chunks = doc.get("chunk_count", 0)
        doc_list.append(f"  • {filename} ({chunks} chunks)")
    
    if len(docs) > 20:
        doc_list.append(f"  ... and {len(docs) - 20} more documents")
    
    return f"""
You are a helpful AI assistant with access to a document knowledge base.

{doc_intro}
{chr(10).join(doc_list)}

When answering questions:
1. Use information from these documents when relevant
2. Cite which document(s) your information comes from
3. If the question cannot be answered from the documents, say so and offer general knowledge if appropriate
4. Be specific about what you found vs. what you're inferring
"""


async def generate_rag_stream(
    query: str, 
    model: str, 
    top_k: int, 
    conversation_id: Optional[str] = None,
    rag_mode: str = "all",
    document_ids: Optional[List[str]] = None,
    include_memory: bool = True,
    user_id: str = "default"
):
    """Generate streaming response with flexible RAG modes, document awareness, and user memory."""
    
    model = model or "gpt-4o-mini"
    
    # Get document-aware system prompt
    doc_awareness = get_document_awareness_prompt(rag_mode, document_ids)
    
    # Get user memory context
    memory_context = ""
    if include_memory:
        memory_context = await get_memory_context(user_id)
        if memory_context:
            doc_awareness = f"{doc_awareness}\n\n{memory_context}"
    
    if rag_mode == "none":
        # Pure LLM mode - no document retrieval
        yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"
        
        # Build messages with document awareness
        messages = [
            {"role": "system", "content": doc_awareness},
            {"role": "user", "content": query}
        ]
        
        # Add conversation history if available
        if conversation_id and conversation_id in rag_engine.conversations:
            history = rag_engine.conversations[conversation_id].messages
            for msg in history[-10:]:  # Last 10 messages
                messages.insert(-1, {"role": msg.role, "content": msg.content})
        
        full_response = ""
        try:
            async for chunk in llm_router.stream(model_id=model, messages=messages):
                if chunk.get("chunk"):
                    full_response += chunk["chunk"]
                    yield f"data: {json.dumps({'type': 'token', 'data': chunk['chunk']})}\n\n"
                if chunk.get("done"):
                    # Store in conversation
                    if conversation_id:
                        rag_engine._add_to_conversation(conversation_id, query, full_response, [])
                    yield f"data: {json.dumps({'type': 'done', 'data': {'model': model, 'rag_mode': 'none'}})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    else:
        # RAG mode - use documents with awareness
        async for event in rag_engine.stream_query(
            query=query,
            model=model,
            top_k=top_k,
            conversation_id=conversation_id,
            document_ids=document_ids if rag_mode == "selected" else None,
            system_prompt_prefix=doc_awareness
        ):
            if event["type"] == "sources":
                yield f"data: {json.dumps({'type': 'sources', 'data': event['data']})}\n\n"
            elif event["type"] == "chunk":
                yield f"data: {json.dumps({'type': 'token', 'data': event['data']})}\n\n"
            elif event["type"] == "done":
                data = event.get('data', {'model': model})
                if isinstance(data, dict):
                    data['rag_mode'] = rag_mode
                yield f"data: {json.dumps({'type': 'done', 'data': data})}\n\n"
            elif event["type"] == "error":
                yield f"data: {json.dumps({'type': 'error', 'data': event['data']})}\n\n"
        
        await asyncio.sleep(0)  # Allow other tasks


async def generate_completion_stream(prompt: str, model: str, provider: str, max_tokens: int, temperature: float):
    """Generate streaming completion."""
    
    ollama = get_ollama()
    
    if provider == "ollama" or (model and "llama" in model.lower()):
        if await ollama.is_available():
            async for chunk in ollama.stream(prompt=prompt, model=model or "llama3.2"):
                yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"
                await asyncio.sleep(0)
        else:
            yield f"data: {json.dumps({'type': 'error', 'data': 'Ollama not available'})}\n\n"
    else:
        try:
            messages = [{"role": "user", "content": prompt}]
            async for chunk in llm_router.stream(
                model_id=model or "gpt-4o-mini",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"
                await asyncio.sleep(0)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat")
async def stream_chat(request: StreamChatRequest):
    """
    Stream chat response with flexible RAG modes.
    
    RAG Modes:
    - "none": Pure LLM chat without document context
    - "all": Use all ingested documents for context
    - "selected": Use only specified document_ids for context
    
    Returns Server-Sent Events (SSE) with:
    - sources: Retrieved context sources (empty for "none" mode)
    - token: Each generated token
    - done: Completion signal with model and mode info
    """
    return StreamingResponse(
        generate_rag_stream(
            query=request.query,
            model=request.model,
            top_k=request.top_k,
            conversation_id=request.conversation_id,
            rag_mode=request.rag_mode,
            document_ids=request.document_ids,
            include_memory=request.include_memory,
            user_id=request.user_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/completion")
async def stream_completion(request: StreamCompletionRequest):
    """
    Stream LLM completion.
    
    Returns Server-Sent Events (SSE) with tokens as they generate.
    """
    return StreamingResponse(
        generate_completion_stream(
            prompt=request.prompt,
            model=request.model,
            provider=request.provider,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/test")
async def test_stream():
    """Test streaming endpoint."""
    async def generate():
        for i in range(10):
            yield f"data: {json.dumps({'count': i, 'message': f'Token {i}'})}\n\n"
            await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


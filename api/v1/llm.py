"""
LLM API - Model management and inference endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

from core.llm import llm_router, get_ollama, check_ollama

router = APIRouter()


class CompletionRequest(BaseModel):
    """Completion request."""
    prompt: str
    model: Optional[str] = None
    provider: Optional[str] = None  # "openai", "anthropic", "ollama"
    temperature: float = 0.7
    max_tokens: int = 500
    system: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 500


class CompletionResponse(BaseModel):
    """Completion response."""
    content: str
    model: str
    provider: str
    latency_ms: float
    tokens: int
    cached: bool = False


@router.get("/providers")
async def list_providers():
    """
    List available LLM providers and their status.
    """
    providers = {
        "openai": {
            "available": bool(os.getenv("OPENAI_API_KEY")),
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
        },
        "anthropic": {
            "available": bool(os.getenv("ANTHROPIC_API_KEY")),
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
        }
    }
    
    # Check Ollama
    ollama_status = await check_ollama()
    providers["ollama"] = {
        "available": ollama_status["available"],
        "models": ollama_status.get("models", [])[:10],
        "url": ollama_status.get("url", "http://localhost:11434")
    }
    
    return {
        "providers": providers,
        "default": "openai" if providers["openai"]["available"] else 
                   "ollama" if providers["ollama"]["available"] else None
    }


@router.get("/ollama/status")
async def ollama_status():
    """
    Check Ollama availability and list models.
    """
    status = await check_ollama()
    
    if not status["available"]:
        return {
            "available": False,
            "message": "Ollama is not running. Start with: ollama serve",
            "url": status["url"]
        }
    
    return {
        "available": True,
        "url": status["url"],
        "models": status["models"],
        "recommended": [
            {"name": "llama3.2", "size": "2B", "speed": "very fast"},
            {"name": "llama3.2:3b", "size": "3B", "speed": "fast"},
            {"name": "mistral", "size": "7B", "speed": "medium"},
            {"name": "llama3.1", "size": "8B", "speed": "medium"}
        ]
    }


@router.post("/ollama/pull")
async def pull_ollama_model(model: str = "llama3.2"):
    """
    Pull a model from Ollama registry.
    
    Common models:
    - llama3.2 (2B, very fast)
    - llama3.2:3b (3B, fast) 
    - mistral (7B, medium)
    - llama3.1 (8B, medium)
    """
    ollama = get_ollama()
    
    if not await ollama.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start with: ollama serve"
        )
    
    # Note: This returns immediately, pulling happens in background
    return {
        "message": f"To pull {model}, run: ollama pull {model}",
        "model": model,
        "command": f"ollama pull {model}"
    }


@router.post("/complete", response_model=CompletionResponse)
async def complete(request: CompletionRequest):
    """
    Generate completion from any provider.
    """
    provider = request.provider
    
    # Auto-select provider
    if not provider:
        ollama = get_ollama()
        if await ollama.is_available():
            provider = "ollama"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        else:
            raise HTTPException(
                status_code=503,
                detail="No LLM provider available"
            )
    
    if provider == "ollama":
        ollama = get_ollama()
        if not await ollama.is_available():
            raise HTTPException(status_code=503, detail="Ollama not available")
        
        result = await ollama.generate(
            prompt=request.prompt,
            model=request.model,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return CompletionResponse(
            content=result["content"],
            model=result["model"],
            provider="ollama",
            latency_ms=result["latency_ms"],
            tokens=result.get("tokens", 0),
            cached=result.get("cached", False)
        )
    
    else:
        # Use LLM router for OpenAI/Anthropic
        messages = [{"role": "user", "content": request.prompt}]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        
        result = await llm_router.run(
            model_id=request.model or "gpt-4o-mini",
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return CompletionResponse(
            content=result.get("content", ""),
            model=result.get("model", request.model or "gpt-4o-mini"),
            provider=provider or "openai",
            latency_ms=result.get("latency_ms", 0),
            tokens=result.get("usage", {}).get("total_tokens", 0),
            cached=False
        )


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat completion from any provider.
    """
    provider = request.provider
    
    if not provider:
        ollama = get_ollama()
        if await ollama.is_available():
            provider = "ollama"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        else:
            raise HTTPException(status_code=503, detail="No LLM provider available")
    
    if provider == "ollama":
        ollama = get_ollama()
        result = await ollama.chat(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return {
            "content": result["content"],
            "model": result["model"],
            "provider": "ollama",
            "latency_ms": result["latency_ms"],
            "tokens": result.get("tokens", 0)
        }
    
    else:
        result = await llm_router.run(
            model_id=request.model or "gpt-4o-mini",
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return {
            "content": result.get("content", ""),
            "model": result.get("model", ""),
            "provider": provider,
            "latency_ms": result.get("latency_ms", 0),
            "tokens": result.get("usage", {}).get("total_tokens", 0)
        }


@router.post("/compare")
async def compare_providers(prompt: str, providers: List[str] = ["ollama", "openai"]):
    """
    Compare response time and quality across providers.
    """
    results = []
    
    for provider in providers:
        try:
            if provider == "ollama":
                ollama = get_ollama()
                if await ollama.is_available():
                    result = await ollama.generate(
                        prompt=prompt,
                        temperature=0.7,
                        max_tokens=100
                    )
                    results.append({
                        "provider": "ollama",
                        "model": result["model"],
                        "content": result["content"][:200],
                        "latency_ms": result["latency_ms"],
                        "status": "success"
                    })
                else:
                    results.append({
                        "provider": "ollama",
                        "status": "unavailable"
                    })
            
            elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
                import time
                start = time.time()
                result = await llm_router.run(
                    model_id="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=100
                )
                latency = round((time.time() - start) * 1000, 2)
                
                results.append({
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "content": result.get("content", "")[:200],
                    "latency_ms": latency,
                    "status": "success"
                })
            
        except Exception as e:
            results.append({
                "provider": provider,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "prompt": prompt[:100],
        "results": results,
        "fastest": min(
            [r for r in results if r.get("status") == "success"],
            key=lambda x: x.get("latency_ms", float("inf")),
            default=None
        )
    }


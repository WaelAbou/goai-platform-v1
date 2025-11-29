"""
Ollama Local LLM Client.
Fast local inference with llama3, mistral, and other models.
"""

import os
import time
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

from core.telemetry import tracer, SpanStatus, logger
from core.cache import cache


@dataclass
class OllamaConfig:
    """Ollama configuration."""
    base_url: str = "http://localhost:11434"
    default_model: str = "llama3.2"
    timeout: float = 60.0
    # Performance settings
    num_ctx: int = 4096  # Context window
    num_predict: int = 512  # Max tokens to generate
    temperature: float = 0.7


class OllamaClient:
    """
    High-performance Ollama client for local LLM inference.
    
    Typical latency: 200-500ms (vs 2-5s for cloud APIs)
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.config.base_url = os.getenv("OLLAMA_URL", self.config.base_url)
        self._client: Optional[httpx.AsyncClient] = None
        self._available_models: List[str] = []
        self._is_available: Optional[bool] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout)
            )
        return self._client
    
    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        if self._is_available is not None:
            return self._is_available
        
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            self._is_available = response.status_code == 200
            
            if self._is_available:
                data = response.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
                logger.info(
                    "Ollama available",
                    models=self._available_models[:5],
                    total=len(self._available_models)
                )
            
            return self._is_available
        except Exception as e:
            logger.warning("Ollama not available", error=str(e))
            self._is_available = False
            return False
    
    async def list_models(self) -> List[str]:
        """List available models."""
        if not await self.is_available():
            return []
        return self._available_models
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate completion using Ollama.
        
        Args:
            prompt: User prompt
            model: Model name (default: llama3.2)
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            use_cache: Whether to use response cache
            
        Returns:
            {
                "content": str,
                "model": str,
                "latency_ms": float,
                "tokens": int,
                "cached": bool
            }
        """
        model = model or self.config.default_model
        
        # Check cache
        if use_cache and temperature and temperature < 0.1:
            cache_key = f"ollama:{model}:{hash(prompt[:500])}"
            cached = cache.get(cache_key, "llm")
            if cached:
                logger.debug("Ollama cache hit")
                return {**cached, "cached": True, "latency_ms": 0}
        
        span = tracer.start_span("ollama.generate", attributes={
            "model": model,
            "prompt_length": len(prompt)
        })
        
        start = time.time()
        
        try:
            if not await self.is_available():
                raise ConnectionError("Ollama is not available")
            
            client = await self._get_client()
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": self.config.num_ctx,
                    "num_predict": max_tokens or self.config.num_predict,
                    "temperature": temperature or self.config.temperature
                }
            }
            
            if system:
                payload["system"] = system
            
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            
            data = response.json()
            latency = round((time.time() - start) * 1000, 2)
            
            result = {
                "content": data.get("response", ""),
                "model": model,
                "latency_ms": latency,
                "tokens": data.get("eval_count", 0),
                "cached": False,
                "provider": "ollama"
            }
            
            span.set_attribute("latency_ms", latency)
            span.set_attribute("tokens", result["tokens"])
            span.set_status(SpanStatus.OK)
            
            logger.info(
                "Ollama generation complete",
                model=model,
                latency_ms=latency,
                tokens=result["tokens"]
            )
            
            # Cache result
            if use_cache and temperature and temperature < 0.1:
                cache.set(cache_key, result, "llm", ttl=3600)
            
            return result
            
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            logger.error("Ollama generation failed", error=str(e))
            raise
        finally:
            tracer.end_span(span)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Chat completion using Ollama.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens
            
        Returns:
            Same as generate()
        """
        model = model or self.config.default_model
        
        span = tracer.start_span("ollama.chat", attributes={
            "model": model,
            "message_count": len(messages)
        })
        
        start = time.time()
        
        try:
            if not await self.is_available():
                raise ConnectionError("Ollama is not available")
            
            client = await self._get_client()
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": self.config.num_ctx,
                    "num_predict": max_tokens or self.config.num_predict,
                    "temperature": temperature or self.config.temperature
                }
            }
            
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            
            data = response.json()
            latency = round((time.time() - start) * 1000, 2)
            
            result = {
                "content": data.get("message", {}).get("content", ""),
                "model": model,
                "latency_ms": latency,
                "tokens": data.get("eval_count", 0),
                "cached": False,
                "provider": "ollama"
            }
            
            span.set_attribute("latency_ms", latency)
            span.set_status(SpanStatus.OK)
            
            return result
            
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            tracer.end_span(span)
    
    async def stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream generation from Ollama.
        
        Yields:
            Text chunks as they are generated
        """
        model = model or self.config.default_model
        
        if not await self.is_available():
            raise ConnectionError("Ollama is not available")
        
        client = await self._get_client()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        
        if system:
            payload["system"] = system
        
        async with client.stream("POST", "/api/generate", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
    
    async def embeddings(
        self,
        texts: List[str],
        model: str = "nomic-embed-text"
    ) -> List[List[float]]:
        """
        Get embeddings from Ollama.
        
        Args:
            texts: Texts to embed
            model: Embedding model (default: nomic-embed-text)
            
        Returns:
            List of embedding vectors
        """
        if not await self.is_available():
            raise ConnectionError("Ollama is not available")
        
        client = await self._get_client()
        embeddings = []
        
        for text in texts:
            response = await client.post("/api/embeddings", json={
                "model": model,
                "prompt": text
            })
            response.raise_for_status()
            data = response.json()
            embeddings.append(data.get("embedding", []))
        
        return embeddings
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "available": self._is_available,
            "base_url": self.config.base_url,
            "default_model": self.config.default_model,
            "models": self._available_models[:10],
            "model_count": len(self._available_models)
        }


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama() -> OllamaClient:
    """Get Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


async def check_ollama() -> Dict[str, Any]:
    """Quick check if Ollama is available."""
    client = get_ollama()
    available = await client.is_available()
    return {
        "available": available,
        "models": await client.list_models() if available else [],
        "url": client.config.base_url
    }


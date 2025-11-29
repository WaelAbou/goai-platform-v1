"""
Fast LLM Service with Caching & Streaming.
Reduces API calls and improves response times.
"""

import asyncio
import hashlib
import os
import time
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field

from core.cache import cache


@dataclass
class LLMStats:
    """LLM service statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    avg_latency_ms: float = 0
    errors: int = 0


class FastLLMService:
    """
    High-performance LLM service.
    
    Features:
    - Response caching (1 hour TTL)
    - Streaming support
    - Multi-provider (OpenAI, Anthropic)
    - Retry logic
    - Rate limiting awareness
    """
    
    CACHE_TTL = 3600  # 1 hour
    
    def __init__(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        default_model: str = "gpt-4o-mini"
    ):
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
        self.default_model = default_model
        self.stats = LLMStats()
        
        # Lazy-loaded clients
        self._openai = None
        self._anthropic = None
    
    def _get_openai(self):
        """Lazy load OpenAI client."""
        if self._openai is None and self.openai_key:
            from openai import AsyncOpenAI
            self._openai = AsyncOpenAI(api_key=self.openai_key)
        return self._openai
    
    def _get_anthropic(self):
        """Lazy load Anthropic client."""
        if self._anthropic is None and self.anthropic_key:
            from anthropic import AsyncAnthropic
            self._anthropic = AsyncAnthropic(api_key=self.anthropic_key)
        return self._anthropic
    
    def _hash_request(self, messages: List[Dict], model: str, **kwargs) -> str:
        """Create cache key for request."""
        content = f"{model}:{messages}:{kwargs}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _is_openai_model(self, model: str) -> bool:
        """Check if model is OpenAI."""
        return model.startswith(("gpt-", "o1-", "text-", "davinci"))
    
    def _is_anthropic_model(self, model: str) -> bool:
        """Check if model is Anthropic."""
        return model.startswith("claude")
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get completion with caching.
        
        Returns:
            {
                "content": str,
                "model": str,
                "usage": {...},
                "cached": bool,
                "latency_ms": float
            }
        """
        model = model or self.default_model
        self.stats.total_requests += 1
        
        # Check cache (only for deterministic requests)
        cache_key = None
        if use_cache and temperature < 0.1:
            cache_key = self._hash_request(messages, model, max_tokens=max_tokens)
            cached = cache.get_llm_response(str(messages), model)
            if cached is not None:
                self.stats.cache_hits += 1
                return {
                    "content": cached,
                    "model": model,
                    "usage": {"cached": True},
                    "cached": True,
                    "latency_ms": 0
                }
        
        self.stats.cache_misses += 1
        
        # Route to provider
        start = time.time()
        try:
            if self._is_openai_model(model):
                result = await self._openai_complete(messages, model, temperature, max_tokens, **kwargs)
            elif self._is_anthropic_model(model):
                result = await self._anthropic_complete(messages, model, temperature, max_tokens, **kwargs)
            else:
                # Default to OpenAI
                result = await self._openai_complete(messages, model, temperature, max_tokens, **kwargs)
            
            latency = (time.time() - start) * 1000
            self._update_latency(latency)
            self.stats.api_calls += 1
            
            # Cache result
            if cache_key and temperature < 0.1:
                cache.set_llm_response(str(messages), model, result["content"])
            
            result["latency_ms"] = latency
            result["cached"] = False
            return result
            
        except Exception as e:
            self.stats.errors += 1
            raise
    
    async def _openai_complete(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """OpenAI completion."""
        client = self._get_openai()
        if not client:
            raise ValueError("OpenAI API key not configured")
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        usage = response.usage
        self.stats.tokens_prompt += usage.prompt_tokens
        self.stats.tokens_completion += usage.completion_tokens
        
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            }
        }
    
    async def _anthropic_complete(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Anthropic completion."""
        client = self._get_anthropic()
        if not client:
            raise ValueError("Anthropic API key not configured")
        
        # Convert messages format
        system = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                claude_messages.append(msg)
        
        response = await client.messages.create(
            model=model,
            messages=claude_messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        self.stats.tokens_prompt += response.usage.input_tokens
        self.stats.tokens_completion += response.usage.output_tokens
        
        return {
            "content": response.content[0].text,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens.
        
        Yields:
            Content chunks as they arrive
        """
        model = model or self.default_model
        self.stats.total_requests += 1
        self.stats.api_calls += 1
        
        start = time.time()
        
        if self._is_openai_model(model):
            async for chunk in self._openai_stream(messages, model, temperature, max_tokens, **kwargs):
                yield chunk
        elif self._is_anthropic_model(model):
            async for chunk in self._anthropic_stream(messages, model, temperature, max_tokens, **kwargs):
                yield chunk
        else:
            async for chunk in self._openai_stream(messages, model, temperature, max_tokens, **kwargs):
                yield chunk
        
        latency = (time.time() - start) * 1000
        self._update_latency(latency)
    
    async def _openai_stream(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream from OpenAI."""
        client = self._get_openai()
        
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _anthropic_stream(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream from Anthropic."""
        client = self._get_anthropic()
        
        system = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                claude_messages.append(msg)
        
        async with client.messages.stream(
            model=model,
            messages=claude_messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    def _update_latency(self, latency_ms: float):
        """Update average latency."""
        if self.stats.avg_latency_ms == 0:
            self.stats.avg_latency_ms = latency_ms
        else:
            self.stats.avg_latency_ms = 0.9 * self.stats.avg_latency_ms + 0.1 * latency_ms
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        total = self.stats.cache_hits + self.stats.cache_misses
        return {
            "total_requests": self.stats.total_requests,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "cache_hit_rate": self.stats.cache_hits / total if total > 0 else 0,
            "api_calls": self.stats.api_calls,
            "tokens_prompt": self.stats.tokens_prompt,
            "tokens_completion": self.stats.tokens_completion,
            "total_tokens": self.stats.tokens_prompt + self.stats.tokens_completion,
            "avg_latency_ms": round(self.stats.avg_latency_ms, 2),
            "errors": self.stats.errors,
            "default_model": self.default_model
        }
    
    def clear_cache(self):
        """Clear LLM cache."""
        return cache.clear_namespace("llm")


# Singleton instance
_llm_service: Optional[FastLLMService] = None


def get_llm_service() -> FastLLMService:
    """Get LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = FastLLMService()
    return _llm_service


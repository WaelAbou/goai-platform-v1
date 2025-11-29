"""
High-Performance HTTP Connection Pool.
Reuses connections for faster API calls.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import httpx
from contextlib import asynccontextmanager


@dataclass
class PoolConfig:
    """HTTP pool configuration."""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0  # seconds
    connect_timeout: float = 10.0
    read_timeout: float = 60.0
    write_timeout: float = 30.0
    retries: int = 3
    retry_delay: float = 0.5


class HTTPPool:
    """
    Async HTTP connection pool with retry logic.
    Reuses connections for OpenAI, Anthropic, etc.
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig()
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._stats = {
            "requests": 0,
            "retries": 0,
            "errors": 0,
            "avg_latency_ms": 0
        }
        self._latencies: List[float] = []
    
    def _get_timeout(self) -> httpx.Timeout:
        """Get timeout configuration."""
        return httpx.Timeout(
            connect=self.config.connect_timeout,
            read=self.config.read_timeout,
            write=self.config.write_timeout,
            pool=self.config.connect_timeout
        )
    
    def _get_limits(self) -> httpx.Limits:
        """Get connection limits."""
        return httpx.Limits(
            max_connections=self.config.max_connections,
            max_keepalive_connections=self.config.max_keepalive_connections,
            keepalive_expiry=self.config.keepalive_expiry
        )
    
    async def get_client(self, base_url: str = "") -> httpx.AsyncClient:
        """Get or create a client for the given base URL."""
        if base_url not in self._clients:
            self._clients[base_url] = httpx.AsyncClient(
                base_url=base_url,
                timeout=self._get_timeout(),
                limits=self._get_limits(),
                http2=True  # Enable HTTP/2 for better performance
            )
        return self._clients[base_url]
    
    async def request(
        self,
        method: str,
        url: str,
        base_url: str = "",
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retries and metrics.
        """
        client = await self.get_client(base_url)
        last_error = None
        
        for attempt in range(self.config.retries):
            try:
                start = time.time()
                response = await client.request(method, url, **kwargs)
                latency = (time.time() - start) * 1000
                
                # Update stats
                self._stats["requests"] += 1
                self._latencies.append(latency)
                if len(self._latencies) > 1000:
                    self._latencies = self._latencies[-1000:]
                self._stats["avg_latency_ms"] = sum(self._latencies) / len(self._latencies)
                
                return response
                
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                self._stats["retries"] += 1
                if attempt < self.config.retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        self._stats["errors"] += 1
        raise last_error
    
    async def get(self, url: str, base_url: str = "", **kwargs) -> httpx.Response:
        """GET request."""
        return await self.request("GET", url, base_url, **kwargs)
    
    async def post(self, url: str, base_url: str = "", **kwargs) -> httpx.Response:
        """POST request."""
        return await self.request("POST", url, base_url, **kwargs)
    
    async def close(self):
        """Close all connections."""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            **self._stats,
            "active_clients": len(self._clients),
            "config": {
                "max_connections": self.config.max_connections,
                "keepalive": self.config.max_keepalive_connections
            }
        }


class OpenAIPool:
    """
    Optimized connection pool for OpenAI API.
    """
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key: str, config: Optional[PoolConfig] = None):
        self.api_key = api_key
        self.pool = HTTPPool(config)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small"
    ) -> List[List[float]]:
        """
        Get embeddings with batching for efficiency.
        """
        response = await self.pool.post(
            "/embeddings",
            base_url=self.BASE_URL,
            headers=self._headers,
            json={
                "input": texts,
                "model": model
            }
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
    
    async def chat(
        self,
        messages: List[Dict],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ):
        """
        Chat completion with streaming support.
        """
        response = await self.pool.post(
            "/chat/completions",
            base_url=self.BASE_URL,
            headers=self._headers,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close pool."""
        await self.pool.close()
    
    def stats(self) -> Dict[str, Any]:
        """Get pool stats."""
        return self.pool.stats()


class AnthropicPool:
    """
    Optimized connection pool for Anthropic API.
    """
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    def __init__(self, api_key: str, config: Optional[PoolConfig] = None):
        self.api_key = api_key
        self.pool = HTTPPool(config)
        self._headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    async def messages(
        self,
        messages: List[Dict],
        model: str = "claude-3-haiku-20240307",
        max_tokens: int = 1000,
        system: Optional[str] = None
    ):
        """
        Send messages to Claude.
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens
        }
        if system:
            payload["system"] = system
        
        response = await self.pool.post(
            "/messages",
            base_url=self.BASE_URL,
            headers=self._headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close pool."""
        await self.pool.close()


# Singleton pools
_http_pool: Optional[HTTPPool] = None
_openai_pool: Optional[OpenAIPool] = None
_anthropic_pool: Optional[AnthropicPool] = None


def get_http_pool() -> HTTPPool:
    """Get HTTP pool singleton."""
    global _http_pool
    if _http_pool is None:
        _http_pool = HTTPPool()
    return _http_pool


def get_openai_pool(api_key: str) -> OpenAIPool:
    """Get OpenAI pool singleton."""
    global _openai_pool
    if _openai_pool is None:
        _openai_pool = OpenAIPool(api_key)
    return _openai_pool


def get_anthropic_pool(api_key: str) -> AnthropicPool:
    """Get Anthropic pool singleton."""
    global _anthropic_pool
    if _anthropic_pool is None:
        _anthropic_pool = AnthropicPool(api_key)
    return _anthropic_pool


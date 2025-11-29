"""
High-Performance Caching Engine.
Supports in-memory (LRU) and Redis backends with TTL.
"""

import hashlib
import json
import time
import asyncio
from typing import Any, Optional, Dict, Callable, Union
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import wraps
import threading


@dataclass
class CacheConfig:
    """Cache configuration."""
    backend: str = "memory"  # "memory" or "redis"
    max_size: int = 10000  # Max items in memory cache
    default_ttl: int = 3600  # 1 hour default TTL
    redis_url: str = "redis://localhost:6379"
    prefix: str = "goai:"
    
    # Feature-specific TTLs
    embedding_ttl: int = 86400 * 7  # 7 days - embeddings rarely change
    llm_ttl: int = 3600  # 1 hour - LLM responses
    query_ttl: int = 300  # 5 minutes - search results


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    O(1) get/set operations.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.ttls: Dict[str, float] = {}
        self.lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self.lock:
            if key not in self.cache:
                self._misses += 1
                return None
            
            # Check TTL
            if key in self.ttls and time.time() > self.ttls[key]:
                del self.cache[key]
                del self.ttls[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self._hits += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache with optional TTL."""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Remove oldest item
                    oldest = next(iter(self.cache))
                    del self.cache[oldest]
                    self.ttls.pop(oldest, None)
            
            self.cache[key] = value
            if ttl:
                self.ttls[key] = time.time() + ttl
    
    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.ttls.pop(key, None)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache."""
        with self.lock:
            self.cache.clear()
            self.ttls.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self._hits + self._misses
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0,
                "memory_mb": self._estimate_memory_mb()
            }
    
    def _estimate_memory_mb(self) -> float:
        """Rough memory estimate."""
        # Very rough estimate
        return len(self.cache) * 0.001  # ~1KB per item avg


class CacheEngine:
    """
    Unified caching engine with namespace support.
    """
    
    NAMESPACES = {
        "embedding": "emb:",
        "llm": "llm:",
        "query": "qry:",
        "document": "doc:",
        "general": "gen:"
    }
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._memory_cache = LRUCache(self.config.max_size)
        self._redis = None
        
        if self.config.backend == "redis":
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(
                self.config.redis_url,
                decode_responses=True
            )
            self._redis.ping()
            print("✅ Redis cache connected")
        except Exception as e:
            print(f"⚠️ Redis not available, using memory cache: {e}")
            self._redis = None
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key."""
        prefix = self.NAMESPACES.get(namespace, "gen:")
        return f"{self.config.prefix}{prefix}{key}"
    
    def _hash_key(self, data: Any) -> str:
        """Create hash key from data."""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # ========== Sync API ==========
    
    def get(self, key: str, namespace: str = "general") -> Optional[Any]:
        """Get from cache."""
        full_key = self._make_key(namespace, key)
        
        if self._redis:
            try:
                data = self._redis.get(full_key)
                if data:
                    return json.loads(data)
            except:
                pass
        
        return self._memory_cache.get(full_key)
    
    def set(
        self,
        key: str,
        value: Any,
        namespace: str = "general",
        ttl: Optional[int] = None
    ) -> None:
        """Set in cache."""
        full_key = self._make_key(namespace, key)
        ttl = ttl or self.config.default_ttl
        
        if self._redis:
            try:
                self._redis.setex(full_key, ttl, json.dumps(value, default=str))
                return
            except:
                pass
        
        self._memory_cache.set(full_key, value, ttl)
    
    def delete(self, key: str, namespace: str = "general") -> bool:
        """Delete from cache."""
        full_key = self._make_key(namespace, key)
        
        if self._redis:
            try:
                return bool(self._redis.delete(full_key))
            except:
                pass
        
        return self._memory_cache.delete(full_key)
    
    # ========== Async API ==========
    
    async def aget(self, key: str, namespace: str = "general") -> Optional[Any]:
        """Async get from cache."""
        return self.get(key, namespace)
    
    async def aset(
        self,
        key: str,
        value: Any,
        namespace: str = "general",
        ttl: Optional[int] = None
    ) -> None:
        """Async set in cache."""
        self.set(key, value, namespace, ttl)
    
    # ========== Specialized Methods ==========
    
    def get_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding for text."""
        key = self._hash_key(text)
        return self.get(key, "embedding")
    
    def set_embedding(self, text: str, embedding: list) -> None:
        """Cache embedding for text."""
        key = self._hash_key(text)
        self.set(key, embedding, "embedding", self.config.embedding_ttl)
    
    def get_llm_response(self, prompt: str, model: str) -> Optional[str]:
        """Get cached LLM response."""
        key = self._hash_key({"prompt": prompt, "model": model})
        return self.get(key, "llm")
    
    def set_llm_response(self, prompt: str, model: str, response: str) -> None:
        """Cache LLM response."""
        key = self._hash_key({"prompt": prompt, "model": model})
        self.set(key, response, "llm", self.config.llm_ttl)
    
    def get_query_result(self, query: str, params: dict) -> Optional[Any]:
        """Get cached query result."""
        key = self._hash_key({"query": query, **params})
        return self.get(key, "query")
    
    def set_query_result(self, query: str, params: dict, result: Any) -> None:
        """Cache query result."""
        key = self._hash_key({"query": query, **params})
        self.set(key, result, "query", self.config.query_ttl)
    
    # ========== Decorator ==========
    
    def cached(
        self,
        namespace: str = "general",
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """
        Decorator for caching function results.
        
        Usage:
            @cache.cached(namespace="llm", ttl=3600)
            def get_response(prompt):
                return llm.complete(prompt)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._hash_key({
                        "func": func.__name__,
                        "args": args,
                        "kwargs": kwargs
                    })
                
                # Try cache
                cached = self.get(cache_key, namespace)
                if cached is not None:
                    return cached
                
                # Execute and cache
                result = func(*args, **kwargs)
                self.set(cache_key, result, namespace, ttl)
                return result
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._hash_key({
                        "func": func.__name__,
                        "args": args,
                        "kwargs": kwargs
                    })
                
                cached = await self.aget(cache_key, namespace)
                if cached is not None:
                    return cached
                
                result = await func(*args, **kwargs)
                await self.aset(cache_key, result, namespace, ttl)
                return result
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return wrapper
        
        return decorator
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "backend": self.config.backend,
            "memory": self._memory_cache.stats()
        }
        
        if self._redis:
            try:
                info = self._redis.info("memory")
                stats["redis"] = {
                    "connected": True,
                    "memory_mb": info.get("used_memory", 0) / (1024 * 1024)
                }
            except:
                stats["redis"] = {"connected": False}
        
        return stats
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        prefix = self._make_key(namespace, "")
        count = 0
        
        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=f"{prefix}*")
                    if keys:
                        count += self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except:
                pass
        
        # Clear from memory
        with self._memory_cache.lock:
            to_delete = [k for k in self._memory_cache.cache if k.startswith(prefix)]
            for k in to_delete:
                del self._memory_cache.cache[k]
                self._memory_cache.ttls.pop(k, None)
                count += 1
        
        return count


# Singleton instance
cache = CacheEngine()


def get_cache() -> CacheEngine:
    """Get cache instance."""
    return cache


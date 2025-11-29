"""
Fast Embedding Service with Caching & Batching.
Dramatically reduces embedding API calls.
"""

import asyncio
import hashlib
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from core.cache import cache


@dataclass
class EmbeddingStats:
    """Embedding service statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    tokens_used: int = 0
    avg_latency_ms: float = 0


class FastEmbeddingService:
    """
    High-performance embedding service.
    
    Features:
    - LRU cache with 7-day TTL
    - Batch API calls (up to 2048 texts)
    - Deduplication
    - Async processing
    """
    
    # OpenAI embedding limits
    MAX_BATCH_SIZE = 2048
    MAX_TOKENS_PER_BATCH = 8191
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.dimensions = dimensions
        self.stats = EmbeddingStats()
        self._client = None
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client
    
    def _hash_text(self, text: str) -> str:
        """Create cache key for text."""
        return hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()[:16]
    
    async def embed_single(self, text: str) -> List[float]:
        """
        Get embedding for single text with caching.
        """
        self.stats.total_requests += 1
        
        # Check cache
        cache_key = self._hash_text(text)
        cached = cache.get_embedding(text)
        if cached is not None:
            self.stats.cache_hits += 1
            return cached
        
        self.stats.cache_misses += 1
        
        # Call API
        start = time.time()
        client = self._get_client()
        response = await client.embeddings.create(
            model=self.model,
            input=text
        )
        latency = (time.time() - start) * 1000
        
        # Update stats
        self.stats.api_calls += 1
        self.stats.tokens_used += response.usage.total_tokens
        self._update_latency(latency)
        
        embedding = response.data[0].embedding
        
        # Cache result
        cache.set_embedding(text, embedding)
        
        return embedding
    
    async def embed_batch(
        self,
        texts: List[str],
        skip_cache: bool = False
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts with batching.
        
        1. Check cache for each text
        2. Batch uncached texts
        3. Call API once for batch
        4. Cache results
        """
        if not texts:
            return []
        
        self.stats.total_requests += len(texts)
        
        # Deduplicate while preserving order
        unique_texts = list(dict.fromkeys(texts))
        text_to_idx = {t: i for i, t in enumerate(unique_texts)}
        
        # Check cache for all texts
        results: Dict[str, List[float]] = {}
        uncached: List[str] = []
        
        if not skip_cache:
            for text in unique_texts:
                cached = cache.get_embedding(text)
                if cached is not None:
                    results[text] = cached
                    self.stats.cache_hits += 1
                else:
                    uncached.append(text)
                    self.stats.cache_misses += 1
        else:
            uncached = unique_texts
        
        # Batch API call for uncached
        if uncached:
            start = time.time()
            client = self._get_client()
            
            # Process in batches
            for i in range(0, len(uncached), self.MAX_BATCH_SIZE):
                batch = uncached[i:i + self.MAX_BATCH_SIZE]
                
                response = await client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                self.stats.api_calls += 1
                self.stats.tokens_used += response.usage.total_tokens
                
                # Map results back
                for j, item in enumerate(response.data):
                    text = batch[j]
                    embedding = item.embedding
                    results[text] = embedding
                    
                    # Cache
                    if not skip_cache:
                        cache.set_embedding(text, embedding)
            
            latency = (time.time() - start) * 1000
            self._update_latency(latency)
        
        # Reconstruct results in original order
        return [results[text] for text in texts]
    
    async def embed_documents(
        self,
        documents: List[Dict[str, Any]],
        content_key: str = "content"
    ) -> List[Dict[str, Any]]:
        """
        Add embeddings to document dictionaries.
        """
        texts = [doc.get(content_key, "") for doc in documents]
        embeddings = await self.embed_batch(texts)
        
        for doc, embedding in zip(documents, embeddings):
            doc["embedding"] = embedding
        
        return documents
    
    def _update_latency(self, latency_ms: float):
        """Update average latency."""
        if self.stats.avg_latency_ms == 0:
            self.stats.avg_latency_ms = latency_ms
        else:
            # Exponential moving average
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
            "tokens_used": self.stats.tokens_used,
            "avg_latency_ms": round(self.stats.avg_latency_ms, 2),
            "model": self.model
        }
    
    def clear_cache(self):
        """Clear embedding cache."""
        return cache.clear_namespace("embedding")


# Singleton instance
_embedding_service: Optional[FastEmbeddingService] = None


def get_embedding_service() -> FastEmbeddingService:
    """Get embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = FastEmbeddingService()
    return _embedding_service


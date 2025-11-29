"""
Vector Retriever - Semantic search using vector embeddings.
Supports FAISS backend with multiple embedding providers.
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import httpx

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


@dataclass
class Document:
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0


@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    rank: int = 0


class EmbeddingProvider:
    """Base class for embedding providers"""

    async def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    async def embed_single(self, text: str) -> List[float]:
        results = await self.embed([text])
        return results[0]


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI embedding provider"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(timeout=60.0)
        # Dimension mapping for OpenAI models
        self.dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }

    @property
    def dimension(self) -> int:
        return self.dimensions.get(self.model, 1536)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Process in batches of 100 (OpenAI limit)
        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            payload = {
                "model": self.model,
                "input": batch
            }

            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # Sort by index to maintain order
            embeddings = sorted(data["data"], key=lambda x: x["index"])
            all_embeddings.extend([e["embedding"] for e in embeddings])

        return all_embeddings

    async def close(self):
        await self.client.aclose()


class LocalEmbedding(EmbeddingProvider):
    """
    Local embedding using sentence-transformers or similar.
    Falls back to simple TF-IDF-like representation if not available.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        self._model = None

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Simple hash-based embedding for demo (replace with real model in production)
        embeddings = []
        for text in texts:
            # Create a deterministic pseudo-embedding based on text hash
            hash_bytes = hashlib.sha512(text.encode()).digest()
            # Convert to floats and normalize
            raw = np.frombuffer(hash_bytes, dtype=np.float32)[:self._dimension]
            if len(raw) < self._dimension:
                raw = np.pad(raw, (0, self._dimension - len(raw)))
            # Normalize to unit vector
            norm = np.linalg.norm(raw)
            if norm > 0:
                raw = raw / norm
            embeddings.append(raw.tolist())
        return embeddings


class VectorRetriever:
    """
    Retrieves documents using vector similarity search.
    Supports FAISS backend with multiple index types.
    """

    def __init__(
        self,
        dimension: int = 1536,
        index_type: str = "flat",  # "flat", "ivf", "hnsw"
        nlist: int = 100,  # For IVF index
        metric: str = "cosine"  # "cosine", "l2", "ip"
    ):
        self.dimension = dimension
        self.index_type = index_type
        self.nlist = nlist
        self.metric = metric
        
        self.index = None
        self.documents: Dict[str, Document] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}
        self.current_idx = 0

        # Embedding provider
        self.embedding_provider: Optional[EmbeddingProvider] = None
        
        self._initialize_index()

    def _initialize_index(self):
        """Initialize the FAISS index"""
        if not FAISS_AVAILABLE:
            print("Warning: FAISS not available. Using in-memory numpy search.")
            self.embeddings_matrix = None
            return

        # Create appropriate index based on metric
        if self.metric == "cosine":
            # For cosine similarity, we normalize vectors and use inner product
            if self.index_type == "flat":
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "ivf":
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist, faiss.METRIC_INNER_PRODUCT)
            elif self.index_type == "hnsw":
                self.index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
        elif self.metric == "l2":
            if self.index_type == "flat":
                self.index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "ivf":
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
            elif self.index_type == "hnsw":
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        else:  # inner product
            if self.index_type == "flat":
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "ivf":
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist, faiss.METRIC_INNER_PRODUCT)

    def set_embedding_provider(self, provider: EmbeddingProvider):
        """Set the embedding provider"""
        self.embedding_provider = provider
        self.dimension = getattr(provider, 'dimension', self.dimension)
        self._initialize_index()

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    async def add_documents(
        self,
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Add documents with their embeddings to the index.
        
        Args:
            documents: List of document texts
            embeddings: Optional pre-computed embeddings
            ids: Optional document IDs (generated if not provided)
            metadata: Optional metadata for each document
            
        Returns:
            Dict with add statistics
        """
        n_docs = len(documents)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [hashlib.md5(f"{doc[:100]}_{i}".encode()).hexdigest() for i, doc in enumerate(documents)]
        
        # Generate embeddings if not provided
        if embeddings is None:
            if self.embedding_provider is None:
                # Use local embedding as fallback
                self.embedding_provider = LocalEmbedding(self.dimension)
            embeddings = await self.embedding_provider.embed(documents)
        
        # Ensure metadata list
        if metadata is None:
            metadata = [{} for _ in documents]
        
        # Convert to numpy array
        vectors = np.array(embeddings, dtype=np.float32)
        
        # Normalize for cosine similarity
        if self.metric == "cosine":
            vectors = self._normalize(vectors)
        
        # Add to index
        if FAISS_AVAILABLE and self.index is not None:
            # Train IVF index if needed
            if self.index_type == "ivf" and not self.index.is_trained:
                self.index.train(vectors)
            
            self.index.add(vectors)
        else:
            # Fallback: store in numpy matrix
            if self.embeddings_matrix is None:
                self.embeddings_matrix = vectors
            else:
                self.embeddings_matrix = np.vstack([self.embeddings_matrix, vectors])
        
        # Store document info
        for i, (doc_id, doc, emb, meta) in enumerate(zip(ids, documents, embeddings, metadata)):
            self.documents[doc_id] = Document(
                id=doc_id,
                content=doc,
                embedding=emb,
                metadata=meta,
                chunk_index=self.current_idx + i
            )
            self.id_to_idx[doc_id] = self.current_idx + i
            self.idx_to_id[self.current_idx + i] = doc_id
        
        self.current_idx += n_docs
        
        return {
            "added": n_docs,
            "total": len(self.documents),
            "ids": ids
        }

    async def search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: The search query text
            query_embedding: Pre-computed query embedding
            top_k: Number of results to return
            filters: Optional metadata filters
            threshold: Optional minimum similarity threshold
            
        Returns:
            List of SearchResult objects
        """
        if len(self.documents) == 0:
            return []
        
        # Get query embedding
        if query_embedding is None:
            if self.embedding_provider is None:
                self.embedding_provider = LocalEmbedding(self.dimension)
            query_embedding = await self.embedding_provider.embed_single(query)
        
        query_vector = np.array([query_embedding], dtype=np.float32)
        
        # Normalize for cosine similarity
        if self.metric == "cosine":
            query_vector = self._normalize(query_vector)
        
        # Search
        if FAISS_AVAILABLE and self.index is not None:
            distances, indices = self.index.search(query_vector, min(top_k * 2, len(self.documents)))
            distances = distances[0]
            indices = indices[0]
        else:
            # Fallback: numpy search
            if self.embeddings_matrix is None:
                return []
            
            if self.metric == "cosine" or self.metric == "ip":
                similarities = np.dot(self.embeddings_matrix, query_vector.T).flatten()
                indices = np.argsort(-similarities)[:top_k * 2]
                distances = similarities[indices]
            else:  # L2
                distances_sq = np.sum((self.embeddings_matrix - query_vector) ** 2, axis=1)
                indices = np.argsort(distances_sq)[:top_k * 2]
                distances = -distances_sq[indices]  # Negate so higher is better
        
        # Build results
        results = []
        for rank, (idx, score) in enumerate(zip(indices, distances)):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            doc_id = self.idx_to_id.get(int(idx))
            if doc_id is None:
                continue
            
            doc = self.documents[doc_id]
            
            # Apply threshold
            if threshold is not None and score < threshold:
                continue
            
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            results.append(SearchResult(
                id=doc_id,
                content=doc.content,
                score=float(score),
                metadata=doc.metadata,
                rank=rank
            ))
            
            if len(results) >= top_k:
                break
        
        return results

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,  # Weight for semantic vs keyword
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Hybrid search combining semantic and keyword matching.
        
        Args:
            query: The search query
            top_k: Number of results
            alpha: Weight for semantic (1.0) vs keyword (0.0) search
            filters: Optional filters
            
        Returns:
            List of SearchResult objects
        """
        # Semantic search
        semantic_results = await self.search(query, top_k=top_k * 2, filters=filters)
        
        # Simple keyword matching
        query_terms = set(query.lower().split())
        keyword_scores = {}
        
        for doc_id, doc in self.documents.items():
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            doc_terms = set(doc.content.lower().split())
            overlap = len(query_terms & doc_terms)
            if overlap > 0:
                keyword_scores[doc_id] = overlap / len(query_terms)
        
        # Combine scores
        combined_scores = {}
        
        # Add semantic scores
        for result in semantic_results:
            combined_scores[result.id] = alpha * result.score
        
        # Add keyword scores
        for doc_id, score in keyword_scores.items():
            if doc_id in combined_scores:
                combined_scores[doc_id] += (1 - alpha) * score
            else:
                combined_scores[doc_id] = (1 - alpha) * score
        
        # Sort and return
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        
        results = []
        for rank, doc_id in enumerate(sorted_ids[:top_k]):
            doc = self.documents[doc_id]
            results.append(SearchResult(
                id=doc_id,
                content=doc.content,
                score=combined_scores[doc_id],
                metadata=doc.metadata,
                rank=rank
            ))
        
        return results

    def delete(self, ids: List[str]) -> int:
        """
        Delete documents by ID.
        Note: FAISS doesn't support deletion well, so we mark as deleted.
        """
        deleted = 0
        for doc_id in ids:
            if doc_id in self.documents:
                # Mark as deleted (actual removal requires index rebuild)
                self.documents[doc_id].metadata["_deleted"] = True
                deleted += 1
        return deleted

    def clear(self):
        """Clear the entire index"""
        self.documents = {}
        self.id_to_idx = {}
        self.idx_to_id = {}
        self.current_idx = 0
        self._initialize_index()

    def save(self, path: str):
        """Save the index and documents to disk"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        if FAISS_AVAILABLE and self.index is not None:
            faiss.write_index(self.index, str(path / "index.faiss"))
        
        # Save documents and mappings
        data = {
            "documents": {
                doc_id: {
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "chunk_index": doc.chunk_index
                }
                for doc_id, doc in self.documents.items()
            },
            "id_to_idx": self.id_to_idx,
            "idx_to_id": {str(k): v for k, v in self.idx_to_id.items()},
            "current_idx": self.current_idx,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "metric": self.metric
        }
        
        with open(path / "data.json", "w") as f:
            json.dump(data, f)

    def load(self, path: str):
        """Load the index and documents from disk"""
        path = Path(path)
        
        # Load FAISS index
        if FAISS_AVAILABLE and (path / "index.faiss").exists():
            self.index = faiss.read_index(str(path / "index.faiss"))
        
        # Load documents and mappings
        with open(path / "data.json", "r") as f:
            data = json.load(f)
        
        self.dimension = data["dimension"]
        self.index_type = data["index_type"]
        self.metric = data["metric"]
        self.current_idx = data["current_idx"]
        self.id_to_idx = data["id_to_idx"]
        self.idx_to_id = {int(k): v for k, v in data["idx_to_id"].items()}
        
        self.documents = {}
        for doc_id, doc_data in data["documents"].items():
            self.documents[doc_id] = Document(
                id=doc_data["id"],
                content=doc_data["content"],
                metadata=doc_data["metadata"],
                chunk_index=doc_data["chunk_index"]
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "document_count": len(self.documents),
            "dimension": self.dimension,
            "index_type": self.index_type,
            "metric": self.metric,
            "faiss_available": FAISS_AVAILABLE,
            "index_size": self.index.ntotal if FAISS_AVAILABLE and self.index else 0
        }


# Singleton instance
vector_retriever = VectorRetriever()

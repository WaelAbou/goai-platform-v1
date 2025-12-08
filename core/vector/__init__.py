# Vector Store Core Module
import os
from .retriever import (
    VectorRetriever,
    vector_retriever,
    Document,
    SearchResult,
    EmbeddingProvider,
    OpenAIEmbedding,
    LocalEmbedding
)

# Shared embedding provider instance (singleton pattern to avoid resource leaks)
_shared_embedding_provider = None

def get_embedding_provider() -> OpenAIEmbedding:
    """Get the shared OpenAI embedding provider instance."""
    global _shared_embedding_provider
    if _shared_embedding_provider is None and os.getenv("OPENAI_API_KEY"):
        _shared_embedding_provider = OpenAIEmbedding()
    return _shared_embedding_provider

__all__ = [
    "VectorRetriever",
    "vector_retriever",
    "Document",
    "SearchResult",
    "EmbeddingProvider",
    "OpenAIEmbedding",
    "LocalEmbedding",
    "get_embedding_provider"
]

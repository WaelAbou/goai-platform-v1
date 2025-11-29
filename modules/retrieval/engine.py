"""
Retrieval Engine - Semantic search and document retrieval.
Combines vector search with reranking and filtering.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class RetrievalMode(Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RerankStrategy(Enum):
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    LLM = "llm"
    RECIPROCAL_RANK_FUSION = "rrf"


@dataclass
class RetrievalConfig:
    mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = 10
    rerank: RerankStrategy = RerankStrategy.NONE
    rerank_top_k: int = 5
    min_score: float = 0.0
    hybrid_alpha: float = 0.7  # Weight for semantic vs keyword


@dataclass
class RetrievedDocument:
    id: str
    content: str
    score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    query: str
    documents: List[RetrievedDocument]
    total_found: int
    mode: RetrievalMode
    metadata: Dict[str, Any] = field(default_factory=dict)


class RetrievalEngine:
    """
    Advanced retrieval engine with multiple search modes.
    """

    def __init__(self, config: Optional[RetrievalConfig] = None):
        self.config = config or RetrievalConfig()
        self.vector_retriever = None
        self.llm_router = None

    def set_vector_retriever(self, retriever):
        """Set the vector retriever for semantic search"""
        self.vector_retriever = retriever

    def set_llm_router(self, router):
        """Set the LLM router for LLM-based reranking"""
        self.llm_router = router

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        mode: Optional[RetrievalMode] = None,
        rerank: Optional[RerankStrategy] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: The search query
            top_k: Number of results to return
            filters: Metadata filters
            mode: Search mode override
            rerank: Reranking strategy override
            
        Returns:
            RetrievalResult with ranked documents
        """
        top_k = top_k or self.config.top_k
        mode = mode or self.config.mode
        rerank = rerank or self.config.rerank

        if self.vector_retriever is None:
            return RetrievalResult(
                query=query,
                documents=[],
                total_found=0,
                mode=mode,
                metadata={"error": "Vector retriever not configured"}
            )

        # Fetch more results for reranking
        fetch_k = top_k * 3 if rerank != RerankStrategy.NONE else top_k

        # Execute search based on mode
        if mode == RetrievalMode.SEMANTIC:
            results = await self.vector_retriever.search(
                query=query,
                top_k=fetch_k,
                filters=filters
            )
        elif mode == RetrievalMode.HYBRID:
            results = await self.vector_retriever.hybrid_search(
                query=query,
                top_k=fetch_k,
                alpha=self.config.hybrid_alpha,
                filters=filters
            )
        else:  # KEYWORD
            # Simple keyword search fallback
            results = await self._keyword_search(query, fetch_k, filters)

        # Apply minimum score filter
        results = [r for r in results if r.score >= self.config.min_score]

        # Apply reranking
        if rerank != RerankStrategy.NONE and len(results) > 0:
            results = await self._rerank(query, results, rerank)

        # Limit to top_k
        results = results[:top_k]

        # Convert to RetrievedDocument
        documents = [
            RetrievedDocument(
                id=r.id,
                content=r.content,
                score=r.score,
                rank=i,
                metadata=r.metadata,
                highlights=self._extract_highlights(query, r.content)
            )
            for i, r in enumerate(results)
        ]

        return RetrievalResult(
            query=query,
            documents=documents,
            total_found=len(results),
            mode=mode,
            metadata={"rerank": rerank.value, "filters": filters}
        )

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List:
        """Simple keyword-based search"""
        if self.vector_retriever is None:
            return []
        
        # Use the vector retriever's documents for keyword matching
        query_terms = set(query.lower().split())
        scored_docs = []
        
        for doc_id, doc in self.vector_retriever.documents.items():
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # Score by term overlap
            doc_terms = set(doc.content.lower().split())
            overlap = len(query_terms & doc_terms)
            if overlap > 0:
                score = overlap / len(query_terms)
                scored_docs.append((doc, score))
        
        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to SearchResult format
        from core.vector import SearchResult
        return [
            SearchResult(
                id=doc.id,
                content=doc.content,
                score=score,
                metadata=doc.metadata,
                rank=i
            )
            for i, (doc, score) in enumerate(scored_docs[:top_k])
        ]

    async def _rerank(
        self,
        query: str,
        results: List,
        strategy: RerankStrategy
    ) -> List:
        """Rerank results using specified strategy"""
        
        if strategy == RerankStrategy.RECIPROCAL_RANK_FUSION:
            # RRF is typically used for combining multiple result lists
            # Here we just apply a simple rank-based score normalization
            return self._rrf_rerank(results)
        
        elif strategy == RerankStrategy.LLM and self.llm_router:
            return await self._llm_rerank(query, results)
        
        elif strategy == RerankStrategy.CROSS_ENCODER:
            # Would require a cross-encoder model
            # For now, return as-is
            return results
        
        return results

    def _rrf_rerank(self, results: List, k: int = 60) -> List:
        """Apply Reciprocal Rank Fusion scoring"""
        # RRF score = 1 / (k + rank)
        for i, result in enumerate(results):
            result.score = 1.0 / (k + i + 1)
        
        # Sort by new scores
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    async def _llm_rerank(self, query: str, results: List) -> List:
        """Use LLM to rerank results"""
        if not self.llm_router or len(results) <= 1:
            return results
        
        # Create a prompt for LLM reranking
        docs_text = "\n\n".join([
            f"[{i}] {r.content[:500]}..."
            for i, r in enumerate(results[:10])  # Limit to 10 for context
        ])
        
        prompt = f"""Given the query: "{query}"

Rank the following documents by relevance (most relevant first).
Return only the document numbers in order, separated by commas.

Documents:
{docs_text}

Ranking (comma-separated numbers):"""

        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            # Parse ranking
            ranking_text = response.get("content", "")
            rankings = [int(x.strip()) for x in ranking_text.split(",") if x.strip().isdigit()]
            
            # Reorder results
            if rankings:
                reordered = []
                for idx in rankings:
                    if 0 <= idx < len(results):
                        reordered.append(results[idx])
                
                # Add any missing results at the end
                for r in results:
                    if r not in reordered:
                        reordered.append(r)
                
                # Update scores based on new ranking
                for i, r in enumerate(reordered):
                    r.score = 1.0 - (i / len(reordered))
                
                return reordered
        
        except Exception:
            pass
        
        return results

    def _extract_highlights(self, query: str, content: str, max_highlights: int = 3) -> List[str]:
        """Extract relevant snippets from content"""
        query_terms = query.lower().split()
        content_lower = content.lower()
        highlights = []
        
        for term in query_terms:
            idx = content_lower.find(term)
            while idx != -1 and len(highlights) < max_highlights:
                # Extract surrounding context
                start = max(0, idx - 50)
                end = min(len(content), idx + len(term) + 50)
                snippet = content[start:end]
                
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                
                if snippet not in highlights:
                    highlights.append(snippet)
                
                idx = content_lower.find(term, idx + 1)
        
        return highlights

    async def multi_query_retrieve(
        self,
        queries: List[str],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Retrieve using multiple queries and combine results.
        """
        all_docs = {}
        
        for query in queries:
            result = await self.retrieve(query, top_k=top_k, filters=filters)
            for doc in result.documents:
                if doc.id in all_docs:
                    # Combine scores
                    all_docs[doc.id].score += doc.score
                else:
                    all_docs[doc.id] = doc
        
        # Sort by combined score
        documents = sorted(all_docs.values(), key=lambda x: x.score, reverse=True)
        
        # Re-rank
        for i, doc in enumerate(documents):
            doc.rank = i
        
        return RetrievalResult(
            query=" | ".join(queries),
            documents=documents[:top_k],
            total_found=len(documents),
            mode=self.config.mode,
            metadata={"multi_query": True, "num_queries": len(queries)}
        )

    async def query_expansion(self, query: str) -> List[str]:
        """Expand query into multiple related queries using LLM"""
        if not self.llm_router:
            return [query]
        
        prompt = f"""Generate 3 alternative search queries that capture the same intent as:
"{query}"

Return only the queries, one per line."""

        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = response.get("content", "")
            queries = [q.strip() for q in content.split("\n") if q.strip()]
            return [query] + queries[:3]
        
        except Exception:
            return [query]


# Singleton instance
retrieval_engine = RetrievalEngine()


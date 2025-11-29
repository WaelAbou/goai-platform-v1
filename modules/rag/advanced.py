"""
Advanced RAG Features - Reranking, HyDE, Multi-hop Reasoning.

Provides enhanced retrieval strategies:
- Reranking: LLM-based relevance scoring
- HyDE: Hypothetical Document Embeddings
- Multi-hop: Chain-of-thought retrieval
- Query Decomposition: Break complex queries into sub-queries
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

from core.llm import llm_router


class RetrievalStrategy(Enum):
    """Available retrieval strategies."""
    BASIC = "basic"  # Standard vector search
    RERANK = "rerank"  # LLM reranking
    HYDE = "hyde"  # Hypothetical Document Embeddings
    MULTI_HOP = "multi_hop"  # Multi-step reasoning
    DECOMPOSE = "decompose"  # Query decomposition


@dataclass
class RankedSource:
    """A source with relevance score."""
    id: str
    content: str
    original_score: float
    rerank_score: float
    metadata: Dict[str, Any]
    reasoning: Optional[str] = None


class AdvancedRAG:
    """
    Advanced RAG retrieval strategies.
    
    Features:
    - LLM-based reranking for better relevance
    - HyDE for improved semantic matching
    - Multi-hop reasoning for complex queries
    - Query decomposition for multi-part questions
    """
    
    RERANK_PROMPT = """You are a relevance judge. Rate how relevant each document is to the query.

Query: {query}

Documents:
{documents}

For each document, provide:
1. A relevance score from 0-10 (10 = highly relevant)
2. Brief reasoning

Respond in JSON format:
[
  {{"doc_id": 1, "score": 8, "reason": "Directly addresses..."}},
  {{"doc_id": 2, "score": 3, "reason": "Tangentially related..."}}
]"""

    HYDE_PROMPT = """Given the question below, write a hypothetical paragraph that would perfectly answer it.
This paragraph should be factual-sounding and detailed, as if from an expert document.

Question: {query}

Hypothetical answer paragraph:"""

    DECOMPOSE_PROMPT = """Break down this complex question into simpler sub-questions that can be answered independently.

Question: {query}

Provide 2-4 sub-questions in JSON format:
["sub-question 1", "sub-question 2", ...]"""

    MULTI_HOP_PROMPT = """Based on the information gathered so far, determine the next step.

Original Question: {query}
Information So Far: {context}

Either:
1. Provide a follow-up question to get more information
2. Indicate you have enough to answer (respond with "SUFFICIENT")

Response:"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
    
    async def rerank(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[RankedSource]:
        """
        Rerank sources using LLM for better relevance.
        
        Args:
            query: User query
            sources: List of retrieved sources
            top_k: Number of top sources to return
            
        Returns:
            Reranked sources with scores and reasoning
        """
        if not sources:
            return []
        
        # Format documents for the prompt
        docs_text = "\n\n".join([
            f"[Document {i+1}]\n{s.get('content', '')[:500]}"
            for i, s in enumerate(sources[:10])  # Limit to 10 for context
        ])
        
        prompt = self.RERANK_PROMPT.format(query=query, documents=docs_text)
        
        try:
            response = await llm_router.run(
                model_id=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response.get("content", "")
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON array
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                rankings = json.loads(json_match.group())
                
                # Map rankings to sources
                ranked = []
                for rank in rankings:
                    doc_idx = rank.get("doc_id", 1) - 1
                    if 0 <= doc_idx < len(sources):
                        source = sources[doc_idx]
                        ranked.append(RankedSource(
                            id=source.get("id", str(doc_idx)),
                            content=source.get("content", ""),
                            original_score=source.get("score", 0),
                            rerank_score=rank.get("score", 0) / 10,
                            metadata=source.get("metadata", {}),
                            reasoning=rank.get("reason", "")
                        ))
                
                # Sort by rerank score
                ranked.sort(key=lambda x: x.rerank_score, reverse=True)
                return ranked[:top_k]
        
        except Exception as e:
            print(f"Reranking failed: {e}")
        
        # Fallback to original ordering
        return [
            RankedSource(
                id=s.get("id", str(i)),
                content=s.get("content", ""),
                original_score=s.get("score", 0),
                rerank_score=s.get("score", 0),
                metadata=s.get("metadata", {})
            )
            for i, s in enumerate(sources[:top_k])
        ]
    
    async def hyde(self, query: str) -> str:
        """
        Generate Hypothetical Document Embedding (HyDE).
        
        Creates a hypothetical answer to use for retrieval,
        which often matches relevant documents better than the query.
        
        Args:
            query: User query
            
        Returns:
            Hypothetical document text for embedding
        """
        prompt = self.HYDE_PROMPT.format(query=query)
        
        try:
            response = await llm_router.run(
                model_id=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            return response.get("content", query)
        
        except Exception:
            return query
    
    async def decompose_query(self, query: str) -> List[str]:
        """
        Decompose a complex query into sub-queries.
        
        Args:
            query: Complex user query
            
        Returns:
            List of simpler sub-queries
        """
        prompt = self.DECOMPOSE_PROMPT.format(query=query)
        
        try:
            response = await llm_router.run(
                model_id=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response.get("content", "")
            
            # Parse JSON
            import json
            import re
            
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                sub_queries = json.loads(json_match.group())
                return sub_queries
        
        except Exception:
            pass
        
        return [query]  # Fallback to original
    
    async def multi_hop_retrieve(
        self,
        query: str,
        retrieve_fn,
        max_hops: int = 3
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Multi-hop retrieval for complex questions.
        
        Iteratively retrieves information and refines the query
        until sufficient context is gathered.
        
        Args:
            query: User query
            retrieve_fn: Async function to retrieve sources
            max_hops: Maximum retrieval iterations
            
        Returns:
            (all_sources, hop_queries) - accumulated sources and queries used
        """
        all_sources = []
        hop_queries = [query]
        context_summary = ""
        
        for hop in range(max_hops):
            # Retrieve for current query
            sources = await retrieve_fn(hop_queries[-1])
            all_sources.extend(sources)
            
            # Summarize new context
            new_context = "\n".join([s.get("content", "")[:200] for s in sources[:3]])
            context_summary += f"\n\nHop {hop + 1}: {new_context}"
            
            # Determine if we need more information
            prompt = self.MULTI_HOP_PROMPT.format(
                query=query,
                context=context_summary
            )
            
            try:
                response = await llm_router.run(
                    model_id=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                next_step = response.get("content", "").strip()
                
                if "SUFFICIENT" in next_step.upper():
                    break
                
                # Use the response as next query
                hop_queries.append(next_step)
            
            except Exception:
                break
        
        # Deduplicate sources
        seen_ids = set()
        unique_sources = []
        for s in all_sources:
            sid = s.get("id", "")
            if sid not in seen_ids:
                seen_ids.add(sid)
                unique_sources.append(s)
        
        return unique_sources, hop_queries
    
    async def enhanced_retrieve(
        self,
        query: str,
        retrieve_fn,
        strategy: RetrievalStrategy = RetrievalStrategy.RERANK,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Perform enhanced retrieval using the specified strategy.
        
        Args:
            query: User query
            retrieve_fn: Async function to retrieve sources
            strategy: Retrieval strategy to use
            top_k: Number of results
            
        Returns:
            Dict with sources and metadata
        """
        result = {
            "strategy": strategy.value,
            "original_query": query,
            "sources": [],
            "metadata": {}
        }
        
        if strategy == RetrievalStrategy.BASIC:
            sources = await retrieve_fn(query)
            result["sources"] = sources[:top_k]
        
        elif strategy == RetrievalStrategy.RERANK:
            sources = await retrieve_fn(query)
            ranked = await self.rerank(query, sources, top_k)
            result["sources"] = [
                {
                    "id": r.id,
                    "content": r.content,
                    "score": r.rerank_score,
                    "original_score": r.original_score,
                    "reasoning": r.reasoning,
                    "metadata": r.metadata
                }
                for r in ranked
            ]
        
        elif strategy == RetrievalStrategy.HYDE:
            hyde_doc = await self.hyde(query)
            result["metadata"]["hyde_document"] = hyde_doc[:500]
            
            # Retrieve using hypothetical document
            sources = await retrieve_fn(hyde_doc)
            result["sources"] = sources[:top_k]
        
        elif strategy == RetrievalStrategy.MULTI_HOP:
            sources, queries = await self.multi_hop_retrieve(query, retrieve_fn)
            result["sources"] = sources[:top_k]
            result["metadata"]["hop_queries"] = queries
        
        elif strategy == RetrievalStrategy.DECOMPOSE:
            sub_queries = await self.decompose_query(query)
            result["metadata"]["sub_queries"] = sub_queries
            
            # Retrieve for each sub-query
            all_sources = []
            for sq in sub_queries:
                sources = await retrieve_fn(sq)
                all_sources.extend(sources)
            
            # Deduplicate and rerank
            seen = set()
            unique = []
            for s in all_sources:
                sid = s.get("id", "")
                if sid not in seen:
                    seen.add(sid)
                    unique.append(s)
            
            result["sources"] = unique[:top_k]
        
        return result


# Singleton instance
advanced_rag = AdvancedRAG()


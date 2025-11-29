from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from modules.retrieval import retrieval_engine, RetrievalMode, RerankStrategy
from core.vector import vector_retriever
from core.llm import llm_router

router = APIRouter()

# Wire up the retrieval engine with the vector retriever and LLM router
retrieval_engine.set_vector_retriever(vector_retriever)
retrieval_engine.set_llm_router(llm_router)


class RetrieveRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    filters: Optional[Dict[str, Any]] = None
    mode: Optional[str] = "hybrid"  # "semantic", "keyword", "hybrid"
    rerank: Optional[str] = "none"  # "none", "rrf", "llm"
    min_score: Optional[float] = 0.0


class DocumentResult(BaseModel):
    id: str
    content: str
    score: float
    rank: int
    metadata: Dict[str, Any] = {}
    highlights: List[str] = []


class RetrieveResponse(BaseModel):
    query: str
    documents: List[DocumentResult]
    total_found: int
    mode: str
    metadata: Dict[str, Any] = {}


@router.post("/", response_model=RetrieveResponse)
async def retrieve_documents(request: RetrieveRequest):
    """
    Retrieve relevant documents based on semantic search.
    """
    # Map string mode to enum
    mode_map = {
        "semantic": RetrievalMode.SEMANTIC,
        "keyword": RetrievalMode.KEYWORD,
        "hybrid": RetrievalMode.HYBRID
    }
    mode = mode_map.get(request.mode, RetrievalMode.HYBRID)
    
    # Map string rerank to enum
    rerank_map = {
        "none": RerankStrategy.NONE,
        "rrf": RerankStrategy.RECIPROCAL_RANK_FUSION,
        "llm": RerankStrategy.LLM
    }
    rerank = rerank_map.get(request.rerank, RerankStrategy.NONE)
    
    result = await retrieval_engine.retrieve(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
        mode=mode,
        rerank=rerank
    )
    
    return RetrieveResponse(
        query=result.query,
        documents=[
            DocumentResult(
                id=doc.id,
                content=doc.content,
                score=doc.score,
                rank=doc.rank,
                metadata=doc.metadata,
                highlights=doc.highlights
            )
            for doc in result.documents
        ],
        total_found=result.total_found,
        mode=result.mode.value,
        metadata=result.metadata
    )


class HybridRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    alpha: Optional[float] = 0.7  # Weight for semantic (1.0) vs keyword (0.0)
    filters: Optional[Dict[str, Any]] = None


@router.post("/hybrid", response_model=RetrieveResponse)
async def hybrid_retrieve(request: HybridRequest):
    """
    Hybrid retrieval combining semantic and keyword search.
    """
    # Update config for this request
    retrieval_engine.config.hybrid_alpha = request.alpha
    
    result = await retrieval_engine.retrieve(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
        mode=RetrievalMode.HYBRID
    )
    
    return RetrieveResponse(
        query=result.query,
        documents=[
            DocumentResult(
                id=doc.id,
                content=doc.content,
                score=doc.score,
                rank=doc.rank,
                metadata=doc.metadata,
                highlights=doc.highlights
            )
            for doc in result.documents
        ],
        total_found=result.total_found,
        mode="hybrid",
        metadata={"alpha": request.alpha, **result.metadata}
    )


class MultiQueryRequest(BaseModel):
    queries: List[str]
    top_k: Optional[int] = 10
    filters: Optional[Dict[str, Any]] = None


@router.post("/multi-query", response_model=RetrieveResponse)
async def multi_query_retrieve(request: MultiQueryRequest):
    """
    Retrieve using multiple queries and combine results.
    """
    result = await retrieval_engine.multi_query_retrieve(
        queries=request.queries,
        top_k=request.top_k,
        filters=request.filters
    )
    
    return RetrieveResponse(
        query=result.query,
        documents=[
            DocumentResult(
                id=doc.id,
                content=doc.content,
                score=doc.score,
                rank=doc.rank,
                metadata=doc.metadata,
                highlights=doc.highlights
            )
            for doc in result.documents
        ],
        total_found=result.total_found,
        mode=result.mode.value,
        metadata=result.metadata
    )


@router.get("/stats")
async def get_retrieval_stats():
    """Get retrieval system statistics"""
    return vector_retriever.get_stats()

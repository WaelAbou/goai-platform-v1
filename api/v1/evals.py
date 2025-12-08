"""
AI Evaluations API - Analyze, Measure, Improve AI quality.

Features:
- Run evaluations on test datasets
- Track evaluation history
- Compare runs for regression detection
- Export evaluation data
- Custom dataset management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter()


class EvalRequest(BaseModel):
    """Request to evaluate a response."""
    query: str
    response: str
    context: Optional[List[str]] = None
    expected: Optional[str] = None
    metrics: Optional[List[str]] = Field(
        None,
        description="Metrics to evaluate: relevance, faithfulness, helpfulness, correctness, harmlessness"
    )
    model: Optional[str] = None


class DatasetCreate(BaseModel):
    """Create a new evaluation dataset."""
    name: str
    description: Optional[str] = ""
    test_cases: List[Dict[str, Any]] = Field(
        ...,
        description="List of test cases with query, expected (optional), context (optional)"
    )


class RunEvalRequest(BaseModel):
    """Request to run evaluation on a dataset."""
    dataset_id: str
    model: Optional[str] = "gpt-4o-mini"
    metrics: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


# ============================================
# Single Response Evaluation
# ============================================

@router.post("/evaluate")
async def evaluate_response(request: EvalRequest):
    """
    Evaluate a single AI response using LLM-as-Judge.
    
    Example:
    ```
    POST /api/v1/evals/evaluate
    {
        "query": "What is Python?",
        "response": "Python is a programming language...",
        "metrics": ["relevance", "helpfulness"]
    }
    ```
    
    Returns scores for each metric on a 0-1 scale.
    """
    from modules.evals import eval_engine
    from core.llm import llm_router
    
    eval_engine.set_llm_router(llm_router)
    
    result = await eval_engine.evaluate_response(
        query=request.query,
        response=request.response,
        context=request.context,
        expected=request.expected,
        metrics=request.metrics,
        model=request.model or ""
    )
    
    return result.to_dict()


# ============================================
# Dataset Management
# ============================================

@router.get("/datasets")
async def list_datasets():
    """
    List all evaluation datasets.
    """
    from modules.evals import eval_engine
    
    datasets = eval_engine.list_datasets()
    
    return {
        "datasets": datasets,
        "total": len(datasets)
    }


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """
    Get a specific dataset with all test cases.
    """
    from modules.evals import eval_engine
    
    dataset = eval_engine.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "test_cases": dataset.test_cases,
        "test_cases_count": len(dataset.test_cases),
        "created_at": dataset.created_at.isoformat()
    }


@router.post("/datasets")
async def create_dataset(request: DatasetCreate):
    """
    Create a new evaluation dataset.
    
    Example:
    ```
    POST /api/v1/evals/datasets
    {
        "name": "My RAG Tests",
        "description": "Custom test cases for my RAG system",
        "test_cases": [
            {
                "query": "What is X?",
                "expected": "X is...",
                "context": ["Source 1...", "Source 2..."]
            }
        ]
    }
    ```
    """
    from modules.evals import eval_engine
    
    if not request.test_cases:
        raise HTTPException(status_code=400, detail="test_cases cannot be empty")
    
    dataset = eval_engine.add_dataset(
        name=request.name,
        description=request.description,
        test_cases=request.test_cases
    )
    
    return {
        "id": dataset.id,
        "name": dataset.name,
        "test_cases_count": len(dataset.test_cases),
        "message": "Dataset created successfully"
    }


# ============================================
# Evaluation Runs
# ============================================

@router.post("/run")
async def run_evaluation(request: RunEvalRequest, background_tasks: BackgroundTasks):
    """
    Run evaluation on a dataset.
    
    Uses the RAG engine to generate responses for each test case,
    then evaluates them using LLM-as-Judge.
    
    Example:
    ```
    POST /api/v1/evals/run
    {
        "dataset_id": "qa_general",
        "model": "gpt-4o-mini",
        "metrics": ["relevance", "helpfulness", "correctness"]
    }
    ```
    """
    from modules.evals import eval_engine
    from modules.rag import rag_engine
    from core.llm import llm_router
    
    eval_engine.set_llm_router(llm_router)
    
    # Verify dataset exists
    dataset = eval_engine.get_dataset(request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create evaluator function using RAG engine
    async def evaluator(query: str) -> Dict[str, Any]:
        result = await rag_engine.query(
            query=query,
            model=request.model,
            top_k=5
        )
        return {
            "response": result.answer,
            "model": result.model,
            "context": [s.content for s in result.sources]
        }
    
    # Run evaluation
    run = await eval_engine.run_evaluation(
        dataset_id=request.dataset_id,
        evaluator=evaluator,
        metrics=request.metrics,
        config=request.config or {"model": request.model}
    )
    
    return run.to_dict()


@router.get("/runs")
async def list_runs(limit: int = 50):
    """
    List evaluation runs.
    """
    from modules.evals import eval_engine
    
    runs = eval_engine.list_runs(limit=limit)
    
    return {
        "runs": runs,
        "total": len(runs)
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """
    Get detailed evaluation run results.
    """
    from modules.evals import eval_engine
    
    run = eval_engine.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return run


@router.get("/runs/{run_id}/export")
async def export_run(run_id: str, format: str = "json"):
    """
    Export evaluation run results.
    
    Formats: json, csv
    """
    from modules.evals import eval_engine
    
    run = eval_engine.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if format == "csv":
        # Build CSV
        lines = ["query,response,overall_score,passed,latency_ms,model"]
        for r in run["results"]:
            query = r["query"].replace('"', '""')
            response = r["response"][:200].replace('"', '""')
            lines.append(f'"{query}","{response}",{r["overall_score"]},{r["passed"]},{r["latency_ms"]},{r["model"]}')
        
        return {
            "format": "csv",
            "content": "\n".join(lines)
        }
    
    return {
        "format": "json",
        "run": run
    }


# ============================================
# Comparison & Regression Detection
# ============================================

@router.get("/compare/{run_id_1}/{run_id_2}")
async def compare_runs(run_id_1: str, run_id_2: str):
    """
    Compare two evaluation runs for regression detection.
    
    Returns score differences and identifies potential regressions.
    """
    from modules.evals import eval_engine
    
    # Need to load runs into memory first
    run_1 = eval_engine.get_run(run_id_1)
    run_2 = eval_engine.get_run(run_id_2)
    
    if not run_1 or not run_2:
        raise HTTPException(status_code=404, detail="One or both runs not found")
    
    summary_1 = run_1.get("summary", {})
    summary_2 = run_2.get("summary", {})
    
    score_diff = summary_2.get("avg_score", 0) - summary_1.get("avg_score", 0)
    pass_rate_diff = summary_2.get("pass_rate", 0) - summary_1.get("pass_rate", 0)
    latency_diff = summary_2.get("avg_latency_ms", 0) - summary_1.get("avg_latency_ms", 0)
    
    is_regression = score_diff < -0.05 or pass_rate_diff < -0.1
    
    return {
        "run_1": {"id": run_id_1, "summary": summary_1},
        "run_2": {"id": run_id_2, "summary": summary_2},
        "comparison": {
            "score_diff": round(score_diff, 3),
            "pass_rate_diff": round(pass_rate_diff, 3),
            "latency_diff_ms": round(latency_diff, 2),
            "is_regression": is_regression,
            "verdict": "regression" if is_regression else "no_regression" if score_diff >= 0 else "minor_decline"
        }
    }


# ============================================
# Quick Evaluation Helpers
# ============================================

@router.post("/quick-check")
async def quick_check(
    query: str,
    response: str,
    threshold: float = 0.6
):
    """
    Quick pass/fail check for a response.
    
    Returns a simple pass/fail based on relevance and helpfulness scores.
    
    Example:
    ```
    POST /api/v1/evals/quick-check?query=What is X?&response=X is a...&threshold=0.6
    ```
    """
    from modules.evals import eval_engine
    from core.llm import llm_router
    
    eval_engine.set_llm_router(llm_router)
    
    result = await eval_engine.evaluate_response(
        query=query,
        response=response,
        metrics=["relevance", "helpfulness"]
    )
    
    return {
        "passed": result.overall_score >= threshold,
        "score": result.overall_score,
        "threshold": threshold,
        "metrics": {m.name: m.score for m in result.metrics}
    }


@router.get("/metrics")
async def list_available_metrics():
    """
    List available evaluation metrics with descriptions.
    """
    return {
        "metrics": [
            {
                "name": "faithfulness",
                "description": "Measures if response is supported by provided context (for RAG)",
                "use_case": "RAG evaluation"
            },
            {
                "name": "relevance",
                "description": "Measures if response addresses the user's question",
                "use_case": "General evaluation"
            },
            {
                "name": "helpfulness",
                "description": "Measures if response is useful and actionable",
                "use_case": "General evaluation"
            },
            {
                "name": "correctness",
                "description": "Measures if response matches expected answer",
                "use_case": "Test cases with ground truth"
            },
            {
                "name": "harmlessness",
                "description": "Measures if response is safe and appropriate",
                "use_case": "Safety evaluation"
            }
        ]
    }



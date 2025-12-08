"""
AI Evaluation Module - Analyze, Measure, Improve AI quality.

Features:
- LLM-as-Judge evaluation
- RAG evaluation metrics (faithfulness, relevance, context precision)
- Automated test suites
- A/B testing support
- Regression detection
"""

from .engine import (
    EvalEngine,
    eval_engine,
    EvalResult,
    EvalMetric,
    EvalDataset,
    EvalRun
)

__all__ = [
    "EvalEngine",
    "eval_engine",
    "EvalResult",
    "EvalMetric",
    "EvalDataset",
    "EvalRun"
]



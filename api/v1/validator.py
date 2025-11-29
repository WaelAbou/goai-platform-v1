from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from modules.validator import validator_engine, ValidationCategory, ValidationSeverity
from core.llm import llm_router

router = APIRouter()

# Wire up the validator engine with the LLM router
validator_engine.set_llm_router(llm_router)


class ValidateRequest(BaseModel):
    content: str
    rules: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    use_llm: Optional[bool] = True


class ValidationIssueModel(BaseModel):
    category: str
    severity: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    score: float
    errors: List[str] = []
    warnings: List[str] = []
    issues: List[ValidationIssueModel] = []
    metadata: Dict[str, Any] = {}


class FactCheckRequest(BaseModel):
    claim: str
    context: Optional[str] = None


class FactCheckResult(BaseModel):
    claim: str
    verdict: str  # "supported", "refuted", "unverifiable"
    confidence: float
    evidence: List[str] = []
    sources: List[str] = []


class QualityAssessmentRequest(BaseModel):
    content: str


@router.post("/validate", response_model=ValidationResult)
async def validate_content(request: ValidateRequest):
    """
    Validate content against specified rules.
    """
    result = await validator_engine.validate(
        content=request.content,
        rules=request.rules,
        context=request.context,
        use_llm=request.use_llm
    )
    
    return ValidationResult(
        valid=result.valid,
        score=result.score,
        errors=result.errors,
        warnings=result.warnings,
        issues=[
            ValidationIssueModel(
                category=issue.category.value,
                severity=issue.severity.value,
                message=issue.message,
                location=issue.location,
                suggestion=issue.suggestion
            )
            for issue in result.issues
        ],
        metadata=result.metadata
    )


@router.post("/fact-check", response_model=FactCheckResult)
async def fact_check(request: FactCheckRequest):
    """
    Perform fact-checking on a specific claim.
    """
    result = await validator_engine.fact_check(
        claim=request.claim,
        context=request.context
    )
    
    return FactCheckResult(
        claim=result.claim,
        verdict=result.verdict,
        confidence=result.confidence,
        evidence=result.evidence,
        sources=result.sources
    )


@router.post("/quality")
async def assess_quality(request: QualityAssessmentRequest):
    """
    Assess overall content quality.
    """
    result = await validator_engine.assess_quality(content=request.content)
    return result


@router.get("/rules")
async def list_rules():
    """
    List all available validation rules.
    """
    rules = validator_engine.list_rules()
    return {
        "rules": rules,
        "count": len(rules)
    }


@router.post("/rules/{rule_name}/enable")
async def enable_rule(rule_name: str):
    """
    Enable a validation rule.
    """
    validator_engine.enable_rule(rule_name)
    return {
        "rule": rule_name,
        "enabled": True
    }


@router.post("/rules/{rule_name}/disable")
async def disable_rule(rule_name: str):
    """
    Disable a validation rule.
    """
    validator_engine.disable_rule(rule_name)
    return {
        "rule": rule_name,
        "enabled": False
    }


class BatchValidateRequest(BaseModel):
    contents: List[str]
    rules: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/batch")
async def batch_validate(request: BatchValidateRequest):
    """
    Validate multiple content pieces at once.
    """
    results = []
    for content in request.contents:
        result = await validator_engine.validate(
            content=content,
            rules=request.rules,
            context=request.context,
            use_llm=False  # Disable LLM for batch to save costs
        )
        results.append({
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "valid": result.valid,
            "score": result.score,
            "issue_count": len(result.issues)
        })
    
    return {
        "validated": len(results),
        "passed": len([r for r in results if r["valid"]]),
        "failed": len([r for r in results if not r["valid"]]),
        "results": results
    }

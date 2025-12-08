"""
AI Guardrails API

Safety guardrails for AI agent operations.

Endpoints:
- POST /check/input - Check user input for safety
- POST /check/output - Check AI output for safety
- POST /check/tool - Check tool call permission
- GET /rules - List all guardrail rules
- PUT /rules/{name}/enable - Enable a rule
- PUT /rules/{name}/disable - Disable a rule
- GET /stats - Get guardrail statistics
- GET /violations - Get recent violations
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from modules.agents.guardrails import (
    guardrails,
    GuardrailResult,
    GuardrailType,
    Severity
)

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class CheckInputRequest(BaseModel):
    """Request to check user input."""
    content: str = Field(..., description="User input to check")
    user_id: str = Field("default", description="User identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class CheckOutputRequest(BaseModel):
    """Request to check AI output."""
    content: str = Field(..., description="AI output to check")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class CheckToolRequest(BaseModel):
    """Request to check tool call."""
    tool_name: str = Field(..., description="Name of the tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    user_id: str = Field("default", description="User identifier")


class CheckCostRequest(BaseModel):
    """Request to check cost limits."""
    tokens: int = Field(..., description="Number of tokens")
    model: str = Field("gpt-4o-mini", description="Model name")
    user_id: str = Field("default", description="User identifier")


class AddRuleRequest(BaseModel):
    """Request to add a custom rule."""
    name: str = Field(..., description="Unique rule name")
    guardrail_type: str = Field(..., description="Type: input, output, tool, pii")
    pattern: str = Field(..., description="Regex pattern to match")
    action: str = Field("block", description="Action: block, warn, modify")
    severity: str = Field("medium", description="Severity: low, medium, high, critical")
    description: str = Field("", description="Rule description")


class ConfigRequest(BaseModel):
    """Request to update guardrail configuration."""
    enabled: Optional[bool] = None
    rate_limit_requests: Optional[int] = None
    rate_limit_window: Optional[int] = None
    max_tokens_per_request: Optional[int] = None
    daily_token_limit: Optional[int] = None


class CheckResultResponse(BaseModel):
    """Response for check operations."""
    passed: bool
    blocked: bool = False
    modified: bool = False
    reason: Optional[str] = None
    content: Optional[str] = None
    violations: List[Dict[str, Any]] = []
    violation_count: int = 0


# ============================================
# Check Endpoints
# ============================================

@router.post("/check/input", response_model=CheckResultResponse)
async def check_input(request: CheckInputRequest):
    """
    Check user input against safety guardrails.
    
    Checks for:
    - Prompt injection attempts
    - Harmful/dangerous content requests
    - Rate limiting
    
    Example:
    ```
    POST /api/v1/guardrails/check/input
    {
        "content": "How do I hack into a system?",
        "user_id": "user-123"
    }
    ```
    """
    result = await guardrails.check_input(
        content=request.content,
        user_id=request.user_id,
        context=request.context
    )
    
    return CheckResultResponse(
        passed=result.passed,
        blocked=result.blocked,
        modified=result.modified,
        reason=result.reason,
        content=result.content,
        violations=[v.to_dict() for v in result.violations],
        violation_count=len(result.violations)
    )


@router.post("/check/output", response_model=CheckResultResponse)
async def check_output(request: CheckOutputRequest):
    """
    Check AI output against safety guardrails.
    
    Checks for:
    - Inappropriate language
    - PII leakage
    - Harmful content
    
    If `modify` action is configured, returns sanitized content.
    
    Example:
    ```
    POST /api/v1/guardrails/check/output
    {
        "content": "Here is the user's SSN: 123-45-6789"
    }
    ```
    """
    result = await guardrails.check_output(
        content=request.content,
        context=request.context
    )
    
    return CheckResultResponse(
        passed=result.passed,
        blocked=result.blocked,
        modified=result.modified,
        reason=result.reason,
        content=result.content,
        violations=[v.to_dict() for v in result.violations],
        violation_count=len(result.violations)
    )


@router.post("/check/tool", response_model=CheckResultResponse)
async def check_tool(request: CheckToolRequest):
    """
    Check if a tool call is allowed.
    
    Restricted tools may require human approval.
    
    Example:
    ```
    POST /api/v1/guardrails/check/tool
    {
        "tool_name": "execute_python",
        "arguments": {"code": "print('hello')"}
    }
    ```
    """
    result = await guardrails.check_tool_call(
        tool_name=request.tool_name,
        arguments=request.arguments,
        user_id=request.user_id
    )
    
    return CheckResultResponse(
        passed=result.passed,
        blocked=result.blocked,
        modified=result.modified,
        reason=result.reason,
        violations=[v.to_dict() for v in result.violations],
        violation_count=len(result.violations)
    )


@router.post("/check/cost", response_model=CheckResultResponse)
async def check_cost(request: CheckCostRequest):
    """
    Check if token usage is within limits.
    
    Example:
    ```
    POST /api/v1/guardrails/check/cost
    {
        "tokens": 50000,
        "model": "gpt-4o",
        "user_id": "user-123"
    }
    ```
    """
    result = guardrails.check_cost(
        tokens=request.tokens,
        model=request.model,
        user_id=request.user_id
    )
    
    return CheckResultResponse(
        passed=result.passed,
        blocked=result.blocked,
        reason=result.reason,
        violations=[v.to_dict() for v in result.violations],
        violation_count=len(result.violations)
    )


# ============================================
# Rule Management Endpoints
# ============================================

@router.get("/rules")
async def list_rules(
    guardrail_type: Optional[str] = Query(None, description="Filter by type"),
    enabled_only: bool = Query(False, description="Show only enabled rules")
):
    """
    List all guardrail rules.
    
    Example:
    ```
    GET /api/v1/guardrails/rules
    GET /api/v1/guardrails/rules?guardrail_type=input&enabled_only=true
    ```
    """
    rules = guardrails.list_rules()
    
    if guardrail_type:
        rules = [r for r in rules if r["type"] == guardrail_type]
    if enabled_only:
        rules = [r for r in rules if r["enabled"]]
    
    return {
        "rules": rules,
        "total": len(rules),
        "filters": {
            "type": guardrail_type,
            "enabled_only": enabled_only
        }
    }


@router.put("/rules/{rule_name}/enable")
async def enable_rule(rule_name: str):
    """
    Enable a guardrail rule.
    
    Example:
    ```
    PUT /api/v1/guardrails/rules/prompt_injection/enable
    ```
    """
    if rule_name not in guardrails.rules:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")
    
    guardrails.enable_rule(rule_name)
    return {"message": f"Rule '{rule_name}' enabled", "rule": rule_name}


@router.put("/rules/{rule_name}/disable")
async def disable_rule(rule_name: str):
    """
    Disable a guardrail rule.
    
    ⚠️ Warning: Disabling security rules may expose the system to risks.
    
    Example:
    ```
    PUT /api/v1/guardrails/rules/profanity_filter/disable
    ```
    """
    if rule_name not in guardrails.rules:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")
    
    guardrails.disable_rule(rule_name)
    return {"message": f"Rule '{rule_name}' disabled", "rule": rule_name}


@router.get("/rules/{rule_name}")
async def get_rule(rule_name: str):
    """
    Get details of a specific rule.
    """
    if rule_name not in guardrails.rules:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")
    
    rule = guardrails.rules[rule_name]
    return {
        "name": rule.name,
        "type": rule.guardrail_type.value,
        "enabled": rule.enabled,
        "action": rule.action.value,
        "severity": rule.severity.value,
        "description": rule.description
    }


# ============================================
# Configuration Endpoints
# ============================================

@router.get("/config")
async def get_config():
    """
    Get current guardrail configuration.
    """
    return {
        "enabled": guardrails.enabled,
        "rate_limit_requests": guardrails.rate_limit_requests,
        "rate_limit_window": guardrails.rate_limit_window,
        "max_tokens_per_request": guardrails.max_tokens_per_request,
        "daily_token_limit": guardrails.daily_token_limit,
        "allowed_topics": list(guardrails.allowed_topics) if guardrails.allowed_topics else None
    }


@router.put("/config")
async def update_config(request: ConfigRequest):
    """
    Update guardrail configuration.
    
    Example:
    ```
    PUT /api/v1/guardrails/config
    {
        "rate_limit_requests": 200,
        "max_tokens_per_request": 50000
    }
    ```
    """
    if request.enabled is not None:
        guardrails.enabled = request.enabled
    if request.rate_limit_requests is not None:
        guardrails.rate_limit_requests = request.rate_limit_requests
    if request.rate_limit_window is not None:
        guardrails.rate_limit_window = request.rate_limit_window
    if request.max_tokens_per_request is not None:
        guardrails.max_tokens_per_request = request.max_tokens_per_request
    if request.daily_token_limit is not None:
        guardrails.daily_token_limit = request.daily_token_limit
    
    return {"message": "Configuration updated", "config": await get_config()}


@router.put("/toggle")
async def toggle_guardrails(enabled: bool):
    """
    Enable or disable all guardrails.
    
    ⚠️ Warning: Disabling guardrails removes all safety protections.
    
    Example:
    ```
    PUT /api/v1/guardrails/toggle?enabled=false
    ```
    """
    guardrails.enabled = enabled
    return {
        "message": f"Guardrails {'enabled' if enabled else 'disabled'}",
        "enabled": guardrails.enabled
    }


# ============================================
# Statistics & Monitoring Endpoints
# ============================================

@router.get("/stats")
async def get_stats():
    """
    Get guardrail statistics.
    
    Example:
    ```
    GET /api/v1/guardrails/stats
    ```
    """
    return guardrails.get_stats()


@router.get("/violations")
async def get_violations(limit: int = Query(20, ge=1, le=100)):
    """
    Get recent guardrail violations.
    
    Example:
    ```
    GET /api/v1/guardrails/violations?limit=50
    ```
    """
    violations = guardrails.get_recent_violations(limit)
    return {
        "violations": violations,
        "count": len(violations)
    }


@router.post("/reset-limits")
async def reset_limits():
    """
    Reset daily token limits for all users.
    
    Should be called at midnight or as needed.
    """
    guardrails.reset_daily_limits()
    return {"message": "Daily limits reset"}


# ============================================
# Info Endpoint
# ============================================

@router.get("/")
async def get_guardrails_info():
    """
    Get information about the guardrails system.
    """
    stats = guardrails.get_stats()
    
    return {
        "name": "AI Guardrails System",
        "version": "1.0.0",
        "description": "Safety guardrails for AI agent operations",
        
        "features": [
            "Prompt injection detection",
            "Harmful content blocking",
            "PII detection and redaction",
            "Profanity filtering",
            "Tool call restrictions",
            "Token/cost limits",
            "Rate limiting"
        ],
        
        "endpoints": [
            {"path": "/check/input", "method": "POST", "description": "Check user input"},
            {"path": "/check/output", "method": "POST", "description": "Check AI output"},
            {"path": "/check/tool", "method": "POST", "description": "Check tool call"},
            {"path": "/check/cost", "method": "POST", "description": "Check cost limits"},
            {"path": "/rules", "method": "GET", "description": "List rules"},
            {"path": "/stats", "method": "GET", "description": "Get statistics"},
            {"path": "/violations", "method": "GET", "description": "Get violations"}
        ],
        
        "guardrail_types": [t.value for t in GuardrailType],
        "severity_levels": [s.value for s in Severity],
        
        "stats": {
            "enabled": stats["enabled"],
            "rules_count": stats["rules_count"],
            "active_rules": stats["active_rules"],
            "total_violations": stats["total_violations"]
        }
    }


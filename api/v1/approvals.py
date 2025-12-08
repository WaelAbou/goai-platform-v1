"""
Human-in-the-Loop Approvals API

Endpoints for managing approval requests in agentic workflows.
Allows humans to review and approve/reject agent actions.

Endpoints:
- GET /pending - List pending approval requests
- GET /requests - List all requests with filters
- GET /requests/{id} - Get specific request
- POST /requests - Create a new request
- POST /requests/{id}/approve - Approve a request
- POST /requests/{id}/reject - Reject a request
- POST /requests/{id}/cancel - Cancel a request
- GET /policies - List approval policies
- POST /policies - Create custom policy
- GET /stats - Get approval statistics
- GET /audit - Get audit log
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

from modules.agents.hitl import (
    approval_manager,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalPriority,
    ActionCategory,
    ApprovalPolicy
)

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class ApprovalStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    cancelled = "cancelled"


class ActionCategoryEnum(str, Enum):
    external_api = "external_api"
    file_write = "file_write"
    database_modify = "database_modify"
    send_email = "send_email"
    payment = "payment"
    delete = "delete"
    publish = "publish"
    high_cost = "high_cost"
    sensitive_data = "sensitive_data"
    custom = "custom"


class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CreateApprovalRequest(BaseModel):
    """Request to create a new approval request."""
    action: str = Field(..., description="Brief description of the action")
    description: Optional[str] = Field(None, description="Detailed description")
    category: ActionCategoryEnum = Field(ActionCategoryEnum.custom, description="Action category")
    context: Optional[Dict[str, Any]] = Field(None, description="Contextual information")
    agent_id: Optional[str] = Field(None, description="ID of the requesting agent")
    timeout_seconds: Optional[int] = Field(None, description="Custom timeout in seconds")
    priority: Optional[PriorityEnum] = Field(None, description="Priority level")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ApprovalDecision(BaseModel):
    """Request to approve or reject."""
    reason: Optional[str] = Field(None, description="Reason for the decision")
    responded_by: Optional[str] = Field(None, description="ID/name of the responder")


class CreatePolicyRequest(BaseModel):
    """Request to create a custom policy."""
    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    categories: List[ActionCategoryEnum] = Field(..., description="Categories requiring approval")
    auto_approve: bool = Field(False, description="Auto-approve without human review")
    default_timeout_seconds: int = Field(3600, description="Default timeout in seconds")
    priority: PriorityEnum = Field(PriorityEnum.medium, description="Default priority")
    notify_webhook: bool = Field(True, description="Send webhook notification")
    require_reason: bool = Field(False, description="Require reason for approval/rejection")


class CheckApprovalRequest(BaseModel):
    """Request to check if approval is required."""
    action_type: Optional[str] = None
    category: Optional[ActionCategoryEnum] = None
    context: Optional[Dict[str, Any]] = None


# ============================================
# API Endpoints
# ============================================

@router.get("/pending")
async def list_pending_approvals():
    """
    List all pending approval requests.
    
    Returns requests that are waiting for human review.
    
    Example:
    ```
    GET /api/v1/approvals/pending
    ```
    """
    pending = approval_manager.list_pending()
    return {
        "pending": [r.to_dict() for r in pending],
        "count": len(pending)
    }


@router.get("/requests")
async def list_approval_requests(
    status: Optional[ApprovalStatusEnum] = Query(None, description="Filter by status"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    category: Optional[ActionCategoryEnum] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
    """
    List approval requests with optional filters.
    
    Example:
    ```
    GET /api/v1/approvals/requests?status=pending&category=payment
    ```
    """
    # Convert enums
    status_filter = ApprovalStatus(status.value) if status else None
    category_filter = ActionCategory(category.value) if category else None
    
    requests = approval_manager.list_requests(
        status=status_filter,
        agent_id=agent_id,
        category=category_filter,
        limit=limit
    )
    
    return {
        "requests": [r.to_dict() for r in requests],
        "count": len(requests),
        "filters": {
            "status": status.value if status else None,
            "agent_id": agent_id,
            "category": category.value if category else None
        }
    }


@router.get("/requests/{request_id}")
async def get_approval_request(request_id: str):
    """
    Get a specific approval request by ID.
    
    Example:
    ```
    GET /api/v1/approvals/requests/abc123
    ```
    """
    request = approval_manager.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    
    return request.to_dict()


@router.post("/requests")
async def create_approval_request(request: CreateApprovalRequest):
    """
    Create a new approval request.
    
    This pauses an agent workflow until human approval is received.
    
    Example:
    ```
    POST /api/v1/approvals/requests
    {
        "action": "Send promotional email to 10,000 customers",
        "category": "send_email",
        "context": {"recipients": 10000, "template": "promo_v2"},
        "agent_id": "marketing-agent"
    }
    ```
    """
    try:
        approval_request = await approval_manager.create_request(
            action=request.action,
            description=request.description,
            category=ActionCategory(request.category.value),
            context=request.context,
            agent_id=request.agent_id,
            timeout_seconds=request.timeout_seconds,
            priority=ApprovalPriority(request.priority.value) if request.priority else None,
            metadata=request.metadata
        )
        
        return {
            "message": "Approval request created",
            "request": approval_request.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: str, decision: ApprovalDecision):
    """
    Approve an approval request.
    
    Example:
    ```
    POST /api/v1/approvals/requests/abc123/approve
    {
        "reason": "Looks good, proceed",
        "responded_by": "admin@company.com"
    }
    ```
    """
    try:
        response = await approval_manager.respond(
            request_id=request_id,
            approved=True,
            reason=decision.reason,
            responded_by=decision.responded_by
        )
        
        return {
            "message": "Request approved",
            "request_id": request_id,
            "approved": True,
            "reason": decision.reason,
            "responded_by": decision.responded_by
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/requests/{request_id}/reject")
async def reject_request(request_id: str, decision: ApprovalDecision):
    """
    Reject an approval request.
    
    Example:
    ```
    POST /api/v1/approvals/requests/abc123/reject
    {
        "reason": "Too risky, need more review",
        "responded_by": "admin@company.com"
    }
    ```
    """
    try:
        response = await approval_manager.respond(
            request_id=request_id,
            approved=False,
            reason=decision.reason,
            responded_by=decision.responded_by
        )
        
        return {
            "message": "Request rejected",
            "request_id": request_id,
            "approved": False,
            "reason": decision.reason,
            "responded_by": decision.responded_by
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/requests/{request_id}/cancel")
async def cancel_request(request_id: str, reason: Optional[str] = None):
    """
    Cancel a pending approval request.
    
    Example:
    ```
    POST /api/v1/approvals/requests/abc123/cancel?reason=No longer needed
    ```
    """
    try:
        approval_manager.cancel_request(request_id, reason)
        return {
            "message": "Request cancelled",
            "request_id": request_id,
            "reason": reason
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check")
async def check_approval_required(request: CheckApprovalRequest):
    """
    Check if an action requires approval.
    
    Example:
    ```
    POST /api/v1/approvals/check
    {
        "category": "payment",
        "context": {"amount": 500}
    }
    ```
    """
    category = ActionCategory(request.category.value) if request.category else None
    
    required = approval_manager.requires_approval(
        action_type=request.action_type,
        category=category,
        context=request.context
    )
    
    policy = None
    if category:
        policy_obj = approval_manager.get_policy_for_category(category)
        if policy_obj:
            policy = policy_obj.to_dict()
    
    return {
        "requires_approval": required,
        "category": request.category.value if request.category else None,
        "applicable_policy": policy
    }


# ============================================
# Policy Management
# ============================================

@router.get("/policies")
async def list_policies():
    """
    List all approval policies.
    
    Example:
    ```
    GET /api/v1/approvals/policies
    ```
    """
    policies = []
    for policy_id, policy in approval_manager.policies.items():
        policies.append({
            "id": policy_id,
            **policy.to_dict()
        })
    
    return {
        "policies": policies,
        "count": len(policies)
    }


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    """
    Get a specific policy.
    """
    policy = approval_manager.policies.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    
    return {
        "id": policy_id,
        **policy.to_dict()
    }


@router.post("/policies")
async def create_policy(request: CreatePolicyRequest):
    """
    Create a custom approval policy.
    
    Example:
    ```
    POST /api/v1/approvals/policies
    {
        "policy_id": "custom_review",
        "name": "Custom Review Policy",
        "description": "Requires approval for custom actions",
        "categories": ["custom"],
        "default_timeout_seconds": 7200,
        "priority": "high",
        "require_reason": true
    }
    ```
    """
    policy = ApprovalPolicy(
        name=request.name,
        description=request.description,
        categories=[ActionCategory(c.value) for c in request.categories],
        auto_approve=request.auto_approve,
        default_timeout_seconds=request.default_timeout_seconds,
        priority=ApprovalPriority(request.priority.value),
        notify_webhook=request.notify_webhook,
        require_reason=request.require_reason
    )
    
    approval_manager.add_policy(request.policy_id, policy)
    
    return {
        "message": "Policy created",
        "policy": {
            "id": request.policy_id,
            **policy.to_dict()
        }
    }


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str):
    """
    Delete a custom approval policy.
    """
    if policy_id not in approval_manager.policies:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    
    approval_manager.remove_policy(policy_id)
    
    return {
        "message": f"Policy '{policy_id}' deleted"
    }


# ============================================
# Statistics and Audit
# ============================================

@router.get("/stats")
async def get_approval_stats():
    """
    Get approval system statistics.
    
    Example:
    ```
    GET /api/v1/approvals/stats
    ```
    """
    stats = approval_manager.get_stats()
    return stats


@router.get("/audit")
async def get_audit_log(limit: int = Query(100, ge=1, le=1000)):
    """
    Get recent audit log entries.
    
    Example:
    ```
    GET /api/v1/approvals/audit?limit=50
    ```
    """
    log = approval_manager.get_audit_log(limit)
    return {
        "audit_log": log,
        "count": len(log)
    }


@router.post("/cleanup")
async def cleanup_expired():
    """
    Mark expired requests and clean up.
    
    Example:
    ```
    POST /api/v1/approvals/cleanup
    ```
    """
    count = approval_manager.cleanup_expired()
    return {
        "message": f"Cleaned up {count} expired requests",
        "expired_count": count
    }


@router.get("/")
async def get_hitl_info():
    """
    Get information about the HITL approval system.
    """
    stats = approval_manager.get_stats()
    
    return {
        "name": "Human-in-the-Loop Approval System",
        "version": "1.0.0",
        "description": "Manage human approvals for agent actions",
        
        "endpoints": [
            {"path": "/pending", "method": "GET", "description": "List pending approvals"},
            {"path": "/requests", "method": "GET", "description": "List all requests"},
            {"path": "/requests/{id}", "method": "GET", "description": "Get specific request"},
            {"path": "/requests", "method": "POST", "description": "Create approval request"},
            {"path": "/requests/{id}/approve", "method": "POST", "description": "Approve request"},
            {"path": "/requests/{id}/reject", "method": "POST", "description": "Reject request"},
            {"path": "/policies", "method": "GET", "description": "List policies"},
            {"path": "/stats", "method": "GET", "description": "Get statistics"}
        ],
        
        "categories": [c.value for c in ActionCategory],
        "priorities": [p.value for p in ApprovalPriority],
        "statuses": [s.value for s in ApprovalStatus],
        
        "stats": {
            "pending_count": stats["pending_count"],
            "total_requests": stats["total_requests"],
            "policies_count": stats["policies_count"]
        }
    }


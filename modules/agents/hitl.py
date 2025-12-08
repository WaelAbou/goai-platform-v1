"""
Human-in-the-Loop (HITL) Approval System

Enables agents to pause and request human approval before executing
sensitive or high-risk actions.

Features:
- Approval request creation and tracking
- Configurable approval criteria
- Timeout handling
- Webhook notifications
- Audit trail
- Multiple approval workflows

Usage:
    from modules.agents.hitl import approval_manager, ApprovalRequest
    
    # Check if action needs approval
    if approval_manager.requires_approval(action_type="external_api"):
        request = await approval_manager.create_request(
            action="Send email to customer",
            context={"recipient": "customer@example.com"},
            agent_id="agent-123"
        )
        
        # Wait for approval (or timeout)
        result = await approval_manager.wait_for_approval(request.id, timeout=3600)
        
        if result.approved:
            # Execute action
            pass
        else:
            # Handle rejection
            pass
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import json


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(str, Enum):
    """Priority level of approval request."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionCategory(str, Enum):
    """Categories of actions that may require approval."""
    EXTERNAL_API = "external_api"
    FILE_WRITE = "file_write"
    DATABASE_MODIFY = "database_modify"
    SEND_EMAIL = "send_email"
    PAYMENT = "payment"
    DELETE = "delete"
    PUBLISH = "publish"
    HIGH_COST = "high_cost"
    SENSITIVE_DATA = "sensitive_data"
    CUSTOM = "custom"


@dataclass
class ApprovalRequest:
    """A request for human approval."""
    id: str
    action: str
    description: str
    category: ActionCategory
    priority: ApprovalPriority
    context: Dict[str, Any]
    agent_id: str
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Response fields
    responded_at: Optional[datetime] = None
    responded_by: Optional[str] = None
    response_reason: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    webhook_sent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "context": self.context,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "responded_by": self.responded_by,
            "response_reason": self.response_reason,
            "metadata": self.metadata,
            "is_expired": datetime.now() > self.expires_at,
            "time_remaining_seconds": max(0, (self.expires_at - datetime.now()).total_seconds())
        }


@dataclass
class ApprovalResponse:
    """Response to an approval request."""
    request_id: str
    approved: bool
    reason: Optional[str] = None
    responded_by: Optional[str] = None
    responded_at: datetime = field(default_factory=datetime.now)


@dataclass 
class ApprovalPolicy:
    """Policy defining when approval is required."""
    name: str
    description: str
    categories: List[ActionCategory]
    auto_approve: bool = False
    default_timeout_seconds: int = 3600  # 1 hour
    priority: ApprovalPriority = ApprovalPriority.MEDIUM
    notify_webhook: bool = True
    require_reason: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "categories": [c.value for c in self.categories],
            "auto_approve": self.auto_approve,
            "default_timeout_seconds": self.default_timeout_seconds,
            "priority": self.priority.value,
            "notify_webhook": self.notify_webhook,
            "require_reason": self.require_reason
        }


class ApprovalManager:
    """
    Manages human-in-the-loop approval workflows.
    
    Provides:
    - Request creation and tracking
    - Policy-based approval requirements
    - Async waiting with timeout
    - Webhook notifications
    - Audit logging
    """
    
    def __init__(self):
        # Storage
        self.requests: Dict[str, ApprovalRequest] = {}
        self.policies: Dict[str, ApprovalPolicy] = {}
        self.audit_log: List[Dict[str, Any]] = []
        
        # Async events for waiting
        self._events: Dict[str, asyncio.Event] = {}
        
        # Webhook callback
        self.webhook_callback: Optional[Callable] = None
        
        # Default policies
        self._init_default_policies()
    
    def _init_default_policies(self):
        """Initialize default approval policies."""
        self.policies = {
            "high_risk": ApprovalPolicy(
                name="High Risk Actions",
                description="Requires approval for high-risk operations",
                categories=[
                    ActionCategory.PAYMENT,
                    ActionCategory.DELETE,
                    ActionCategory.SENSITIVE_DATA
                ],
                priority=ApprovalPriority.HIGH,
                default_timeout_seconds=7200,  # 2 hours
                require_reason=True
            ),
            "external": ApprovalPolicy(
                name="External Communications",
                description="Requires approval for external communications",
                categories=[
                    ActionCategory.SEND_EMAIL,
                    ActionCategory.EXTERNAL_API,
                    ActionCategory.PUBLISH
                ],
                priority=ApprovalPriority.MEDIUM,
                default_timeout_seconds=3600  # 1 hour
            ),
            "data_modification": ApprovalPolicy(
                name="Data Modifications",
                description="Requires approval for data changes",
                categories=[
                    ActionCategory.DATABASE_MODIFY,
                    ActionCategory.FILE_WRITE
                ],
                priority=ApprovalPriority.MEDIUM,
                default_timeout_seconds=1800  # 30 minutes
            ),
            "cost_control": ApprovalPolicy(
                name="Cost Control",
                description="Requires approval for high-cost operations",
                categories=[ActionCategory.HIGH_COST],
                priority=ApprovalPriority.HIGH,
                default_timeout_seconds=3600
            )
        }
    
    def set_webhook_callback(self, callback: Callable):
        """Set callback function for webhook notifications."""
        self.webhook_callback = callback
    
    def add_policy(self, policy_id: str, policy: ApprovalPolicy):
        """Add a custom approval policy."""
        self.policies[policy_id] = policy
        self._log_audit("policy_added", {"policy_id": policy_id, "policy": policy.to_dict()})
    
    def remove_policy(self, policy_id: str):
        """Remove an approval policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]
            self._log_audit("policy_removed", {"policy_id": policy_id})
    
    def requires_approval(
        self,
        action_type: str = None,
        category: ActionCategory = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Check if an action requires approval based on policies.
        
        Args:
            action_type: Type of action being performed
            category: Category of the action
            context: Additional context for the check
            
        Returns:
            True if approval is required
        """
        if category:
            for policy in self.policies.values():
                if category in policy.categories and not policy.auto_approve:
                    return True
        
        # Check context-based rules
        if context:
            # High cost check
            if context.get("estimated_cost", 0) > 100:
                return True
            # Sensitive data check
            if context.get("contains_pii", False):
                return True
        
        return False
    
    def get_policy_for_category(self, category: ActionCategory) -> Optional[ApprovalPolicy]:
        """Get the applicable policy for a category."""
        for policy in self.policies.values():
            if category in policy.categories:
                return policy
        return None
    
    async def create_request(
        self,
        action: str,
        description: str = None,
        category: ActionCategory = ActionCategory.CUSTOM,
        context: Dict[str, Any] = None,
        agent_id: str = None,
        timeout_seconds: int = None,
        priority: ApprovalPriority = None,
        metadata: Dict[str, Any] = None
    ) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            action: Brief description of the action
            description: Detailed description
            category: Category of the action
            context: Contextual information
            agent_id: ID of the requesting agent
            timeout_seconds: Custom timeout (uses policy default if not set)
            priority: Priority level
            metadata: Additional metadata
            
        Returns:
            Created ApprovalRequest
        """
        # Get policy defaults
        policy = self.get_policy_for_category(category)
        if policy:
            timeout_seconds = timeout_seconds or policy.default_timeout_seconds
            priority = priority or policy.priority
        else:
            timeout_seconds = timeout_seconds or 3600
            priority = priority or ApprovalPriority.MEDIUM
        
        # Create request
        request_id = str(uuid.uuid4())
        now = datetime.now()
        
        request = ApprovalRequest(
            id=request_id,
            action=action,
            description=description or action,
            category=category,
            priority=priority,
            context=context or {},
            agent_id=agent_id or "unknown",
            created_at=now,
            expires_at=now + timedelta(seconds=timeout_seconds),
            metadata=metadata or {}
        )
        
        # Store request
        self.requests[request_id] = request
        
        # Create async event for waiting
        self._events[request_id] = asyncio.Event()
        
        # Log audit
        self._log_audit("request_created", {
            "request_id": request_id,
            "action": action,
            "category": category.value,
            "agent_id": agent_id
        })
        
        # Send webhook notification
        if policy and policy.notify_webhook:
            await self._send_webhook_notification(request)
        
        return request
    
    async def _send_webhook_notification(self, request: ApprovalRequest):
        """Send webhook notification for approval request."""
        if self.webhook_callback:
            try:
                await self.webhook_callback({
                    "event": "approval_requested",
                    "request": request.to_dict(),
                    "timestamp": datetime.now().isoformat()
                })
                request.webhook_sent = True
            except Exception as e:
                self._log_audit("webhook_failed", {
                    "request_id": request.id,
                    "error": str(e)
                })
    
    async def respond(
        self,
        request_id: str,
        approved: bool,
        reason: str = None,
        responded_by: str = None
    ) -> ApprovalResponse:
        """
        Respond to an approval request.
        
        Args:
            request_id: ID of the request
            approved: Whether the action is approved
            reason: Reason for the decision
            responded_by: ID/name of the responder
            
        Returns:
            ApprovalResponse
        """
        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request '{request_id}' not found")
        
        # Check if already responded
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request already has status: {request.status.value}")
        
        # Check if expired
        if datetime.now() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            raise ValueError("Request has expired")
        
        # Check if reason is required
        policy = self.get_policy_for_category(request.category)
        if policy and policy.require_reason and not reason:
            raise ValueError("Reason is required for this approval")
        
        # Update request
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.responded_at = datetime.now()
        request.responded_by = responded_by
        request.response_reason = reason
        
        # Signal waiting coroutines
        if request_id in self._events:
            self._events[request_id].set()
        
        # Log audit
        self._log_audit("request_responded", {
            "request_id": request_id,
            "approved": approved,
            "responded_by": responded_by,
            "reason": reason
        })
        
        return ApprovalResponse(
            request_id=request_id,
            approved=approved,
            reason=reason,
            responded_by=responded_by
        )
    
    async def wait_for_approval(
        self,
        request_id: str,
        timeout: int = None
    ) -> ApprovalResponse:
        """
        Wait for an approval response.
        
        Args:
            request_id: ID of the request to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            ApprovalResponse when decision is made
            
        Raises:
            TimeoutError: If timeout expires before response
        """
        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request '{request_id}' not found")
        
        # Calculate timeout
        if timeout is None:
            timeout = max(0, (request.expires_at - datetime.now()).total_seconds())
        
        # Wait for response
        event = self._events.get(request_id)
        if event:
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Mark as expired
                request.status = ApprovalStatus.EXPIRED
                self._log_audit("request_expired", {"request_id": request_id})
                raise TimeoutError(f"Approval request '{request_id}' timed out")
        
        # Return response
        return ApprovalResponse(
            request_id=request_id,
            approved=request.status == ApprovalStatus.APPROVED,
            reason=request.response_reason,
            responded_by=request.responded_by,
            responded_at=request.responded_at or datetime.now()
        )
    
    def cancel_request(self, request_id: str, reason: str = None):
        """Cancel a pending approval request."""
        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request '{request_id}' not found")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot cancel request with status: {request.status.value}")
        
        request.status = ApprovalStatus.CANCELLED
        request.response_reason = reason
        
        # Signal waiting coroutines
        if request_id in self._events:
            self._events[request_id].set()
        
        self._log_audit("request_cancelled", {
            "request_id": request_id,
            "reason": reason
        })
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self.requests.get(request_id)
    
    def list_requests(
        self,
        status: ApprovalStatus = None,
        agent_id: str = None,
        category: ActionCategory = None,
        limit: int = 50
    ) -> List[ApprovalRequest]:
        """
        List approval requests with optional filters.
        
        Args:
            status: Filter by status
            agent_id: Filter by agent ID
            category: Filter by category
            limit: Maximum number of results
            
        Returns:
            List of matching requests
        """
        results = []
        for request in self.requests.values():
            if status and request.status != status:
                continue
            if agent_id and request.agent_id != agent_id:
                continue
            if category and request.category != category:
                continue
            results.append(request)
        
        # Sort by created_at descending
        results.sort(key=lambda r: r.created_at, reverse=True)
        
        return results[:limit]
    
    def list_pending(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return self.list_requests(status=ApprovalStatus.PENDING)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get approval system statistics."""
        total = len(self.requests)
        by_status = {}
        by_category = {}
        avg_response_time = 0
        response_times = []
        
        for request in self.requests.values():
            # Count by status
            status = request.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            # Count by category
            category = request.category.value
            by_category[category] = by_category.get(category, 0) + 1
            
            # Calculate response time
            if request.responded_at:
                response_time = (request.responded_at - request.created_at).total_seconds()
                response_times.append(response_time)
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
        
        return {
            "total_requests": total,
            "by_status": by_status,
            "by_category": by_category,
            "pending_count": by_status.get("pending", 0),
            "approval_rate": (
                by_status.get("approved", 0) / 
                (by_status.get("approved", 0) + by_status.get("rejected", 0))
                if by_status.get("approved", 0) + by_status.get("rejected", 0) > 0
                else 0
            ),
            "avg_response_time_seconds": avg_response_time,
            "policies_count": len(self.policies)
        }
    
    def _log_audit(self, event_type: str, data: Dict[str, Any]):
        """Log an audit event."""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]
    
    def cleanup_expired(self) -> int:
        """Mark expired requests and clean up old data."""
        now = datetime.now()
        count = 0
        
        for request in self.requests.values():
            if request.status == ApprovalStatus.PENDING and now > request.expires_at:
                request.status = ApprovalStatus.EXPIRED
                count += 1
        
        return count


# Global instance
approval_manager = ApprovalManager()


# ============================================
# Helper Functions for Agent Integration
# ============================================

async def require_approval(
    action: str,
    category: ActionCategory = ActionCategory.CUSTOM,
    context: Dict[str, Any] = None,
    agent_id: str = None,
    timeout: int = 3600
) -> bool:
    """
    Convenience function to request and wait for approval.
    
    Args:
        action: Description of the action
        category: Action category
        context: Additional context
        agent_id: Requesting agent ID
        timeout: Timeout in seconds
        
    Returns:
        True if approved, False otherwise
    """
    if not approval_manager.requires_approval(category=category, context=context):
        return True  # No approval needed
    
    request = await approval_manager.create_request(
        action=action,
        category=category,
        context=context,
        agent_id=agent_id
    )
    
    try:
        response = await approval_manager.wait_for_approval(request.id, timeout=timeout)
        return response.approved
    except TimeoutError:
        return False


def check_approval_required(
    action_type: str = None,
    category: ActionCategory = None,
    context: Dict[str, Any] = None
) -> bool:
    """Check if approval is required without creating a request."""
    return approval_manager.requires_approval(
        action_type=action_type,
        category=category,
        context=context
    )


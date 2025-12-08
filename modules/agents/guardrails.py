"""
AI Guardrails Module

Comprehensive safety guardrails for AI agent operations.

Features:
- Input Guardrails: Block harmful/malicious inputs
- Output Guardrails: Filter inappropriate AI responses
- Tool Guardrails: Restrict dangerous tool usage
- Cost Guardrails: Prevent runaway token consumption
- Topic Guardrails: Keep agents on-topic
- PII Guardrails: Detect and redact sensitive data
- Rate Limiting: Prevent abuse

Usage:
    from modules.agents.guardrails import guardrails, GuardrailResult
    
    # Check input before processing
    result = await guardrails.check_input("User message here")
    if not result.passed:
        print(f"Blocked: {result.reason}")
    
    # Check output before returning
    result = await guardrails.check_output(ai_response)
    if result.modified:
        safe_response = result.content
"""

from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re
import asyncio
from collections import defaultdict


class GuardrailType(str, Enum):
    """Types of guardrails."""
    INPUT = "input"
    OUTPUT = "output"
    TOOL = "tool"
    COST = "cost"
    TOPIC = "topic"
    PII = "pii"
    RATE_LIMIT = "rate_limit"


class GuardrailAction(str, Enum):
    """Actions to take when guardrail triggers."""
    BLOCK = "block"        # Completely block the request
    WARN = "warn"          # Allow but log warning
    MODIFY = "modify"      # Modify content to be safe
    REQUIRE_APPROVAL = "require_approval"  # Require human approval


class Severity(str, Enum):
    """Severity levels for guardrail violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GuardrailViolation:
    """Record of a guardrail violation."""
    guardrail_type: GuardrailType
    rule_name: str
    severity: Severity
    message: str
    matched_content: Optional[str] = None
    action_taken: GuardrailAction = GuardrailAction.BLOCK
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.guardrail_type.value,
            "rule": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "matched_content": self.matched_content[:50] + "..." if self.matched_content and len(self.matched_content) > 50 else self.matched_content,
            "action": self.action_taken.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    passed: bool
    violations: List[GuardrailViolation] = field(default_factory=list)
    content: Optional[str] = None  # Modified content if applicable
    modified: bool = False
    blocked: bool = False
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "modified": self.modified,
            "reason": self.reason,
            "violations": [v.to_dict() for v in self.violations],
            "violation_count": len(self.violations)
        }


@dataclass
class GuardrailRule:
    """A single guardrail rule."""
    name: str
    guardrail_type: GuardrailType
    check_fn: Callable[[str, Dict[str, Any]], Optional[GuardrailViolation]]
    enabled: bool = True
    action: GuardrailAction = GuardrailAction.BLOCK
    severity: Severity = Severity.MEDIUM
    description: str = ""


class Guardrails:
    """
    Central guardrails manager for AI safety.
    
    Provides configurable safety checks for:
    - User inputs
    - AI outputs
    - Tool calls
    - Token/cost limits
    - Topic relevance
    - PII detection
    """
    
    # ==================== Harmful Content Patterns ====================
    
    # Prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above)\s+(instructions?|prompts?|rules?)",
        r"disregard\s+(your|the)\s+(instructions?|programming|guidelines?)",
        r"you\s+are\s+now\s+(a|an|in)\s+(evil|unrestricted|jailbreak)",
        r"pretend\s+(you\'?re|to\s+be)\s+(not|a|an)\s+(ai|assistant|chatbot)",
        r"(system|admin|root)\s*:\s*(prompt|command|override)",
        r"<\s*/?system\s*>",
        r"\[\s*SYSTEM\s*\]",
        r"bypass\s+(safety|content|filter)",
        r"unlock\s+(developer|god)\s+mode",
        r"output\s+your\s+(system|initial)\s+prompt",
    ]
    
    # Harmful request patterns
    HARMFUL_PATTERNS = [
        r"how\s+to\s+(make|build|create)\s+(a\s+)?(bomb|explosive|weapon)",
        r"(hack|break\s+into|exploit)\s+(a\s+)?system",
        r"(steal|phish|scam)\s+(identity|money|credentials)",
        r"(generate|create)\s+(malware|virus|ransomware)",
        r"(illegal|illicit)\s+(drugs?|substances?)",
        r"(child|minor)\s+(abuse|exploitation|pornography)",
        r"(self[\-\s]?harm|suicide)\s+(methods?|ways?|how\s+to)",
        r"(terrorism|terrorist)\s+(attack|plan|recruit)",
    ]
    
    # PII patterns
    PII_PATTERNS = {
        "ssn": (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "Social Security Number"),
        "credit_card": (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "Credit Card"),
        "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email Address"),
        "phone": (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "Phone Number"),
        "ip_address": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP Address"),
        "api_key": (r"\b(sk-[a-zA-Z0-9]{20,}|api[_-]?key[=:]\s*['\"]?[a-zA-Z0-9]{20,})\b", "API Key"),
    }
    
    # Profanity/inappropriate content
    PROFANITY_PATTERNS = [
        r"\bf+u+c+k+\b",
        r"\bs+h+i+t+\b",
        r"\ba+s+s+h+o+l+e+\b",
        r"\bb+i+t+c+h+\b",
        r"\bn+i+g+g+[ae]+r*\b",
        r"\bc+u+n+t+\b",
    ]
    
    # Restricted tools
    RESTRICTED_TOOLS = {
        "execute_python": {"severity": Severity.HIGH, "requires_approval": True},
        "file_write": {"severity": Severity.HIGH, "requires_approval": True},
        "shell_command": {"severity": Severity.CRITICAL, "requires_approval": True},
        "database_modify": {"severity": Severity.HIGH, "requires_approval": True},
        "send_email": {"severity": Severity.MEDIUM, "requires_approval": False},
    }
    
    def __init__(self):
        self.rules: Dict[str, GuardrailRule] = {}
        self.enabled = True
        self.violations_log: List[GuardrailViolation] = []
        
        # Rate limiting
        self._rate_limits: Dict[str, List[datetime]] = defaultdict(list)
        self.rate_limit_requests = 100  # requests per window
        self.rate_limit_window = 60  # seconds
        
        # Cost limits
        self.max_tokens_per_request = 100000
        self.max_cost_per_request = 10.0  # dollars
        self.daily_token_limit = 1000000
        self._daily_tokens: Dict[str, int] = defaultdict(int)
        
        # Allowed topics (if set, restricts to only these)
        self.allowed_topics: Optional[Set[str]] = None
        
        # Initialize built-in rules
        self._register_builtin_rules()
    
    def _register_builtin_rules(self):
        """Register all built-in guardrail rules."""
        
        # ==================== Input Guardrails ====================
        
        # Prompt injection detection
        def check_injection(content: str, ctx: Dict) -> Optional[GuardrailViolation]:
            for pattern in self.INJECTION_PATTERNS:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return GuardrailViolation(
                        guardrail_type=GuardrailType.INPUT,
                        rule_name="prompt_injection",
                        severity=Severity.CRITICAL,
                        message="Potential prompt injection detected",
                        matched_content=match.group(0)
                    )
            return None
        
        self.register_rule(GuardrailRule(
            name="prompt_injection",
            guardrail_type=GuardrailType.INPUT,
            check_fn=check_injection,
            action=GuardrailAction.BLOCK,
            severity=Severity.CRITICAL,
            description="Detects attempts to manipulate AI through prompt injection"
        ))
        
        # Harmful content detection
        def check_harmful(content: str, ctx: Dict) -> Optional[GuardrailViolation]:
            for pattern in self.HARMFUL_PATTERNS:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return GuardrailViolation(
                        guardrail_type=GuardrailType.INPUT,
                        rule_name="harmful_content",
                        severity=Severity.CRITICAL,
                        message="Request for harmful or dangerous content",
                        matched_content=match.group(0)
                    )
            return None
        
        self.register_rule(GuardrailRule(
            name="harmful_content",
            guardrail_type=GuardrailType.INPUT,
            check_fn=check_harmful,
            action=GuardrailAction.BLOCK,
            severity=Severity.CRITICAL,
            description="Blocks requests for harmful, dangerous, or illegal content"
        ))
        
        # ==================== Output Guardrails ====================
        
        # Profanity filter
        def check_profanity(content: str, ctx: Dict) -> Optional[GuardrailViolation]:
            for pattern in self.PROFANITY_PATTERNS:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return GuardrailViolation(
                        guardrail_type=GuardrailType.OUTPUT,
                        rule_name="profanity_filter",
                        severity=Severity.MEDIUM,
                        message="Response contains inappropriate language",
                        matched_content=match.group(0),
                        action_taken=GuardrailAction.MODIFY
                    )
            return None
        
        self.register_rule(GuardrailRule(
            name="profanity_filter",
            guardrail_type=GuardrailType.OUTPUT,
            check_fn=check_profanity,
            action=GuardrailAction.MODIFY,
            severity=Severity.MEDIUM,
            description="Filters profanity from AI responses"
        ))
        
        # ==================== PII Guardrails ====================
        
        # PII detection
        def check_pii(content: str, ctx: Dict) -> Optional[GuardrailViolation]:
            for pii_type, (pattern, description) in self.PII_PATTERNS.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return GuardrailViolation(
                        guardrail_type=GuardrailType.PII,
                        rule_name=f"pii_{pii_type}",
                        severity=Severity.HIGH,
                        message=f"Potential {description} detected",
                        matched_content=match.group(0),
                        action_taken=GuardrailAction.MODIFY
                    )
            return None
        
        self.register_rule(GuardrailRule(
            name="pii_detection",
            guardrail_type=GuardrailType.PII,
            check_fn=check_pii,
            action=GuardrailAction.MODIFY,
            severity=Severity.HIGH,
            description="Detects and optionally redacts personally identifiable information"
        ))
        
        # ==================== Cost Guardrails ====================
        
        # Token limit check
        def check_token_limit(content: str, ctx: Dict) -> Optional[GuardrailViolation]:
            estimated_tokens = len(content.split()) * 1.3  # Rough estimate
            max_tokens = ctx.get("max_tokens", self.max_tokens_per_request)
            
            if estimated_tokens > max_tokens:
                return GuardrailViolation(
                    guardrail_type=GuardrailType.COST,
                    rule_name="token_limit",
                    severity=Severity.MEDIUM,
                    message=f"Content exceeds token limit ({int(estimated_tokens)} > {max_tokens})"
                )
            return None
        
        self.register_rule(GuardrailRule(
            name="token_limit",
            guardrail_type=GuardrailType.COST,
            check_fn=check_token_limit,
            action=GuardrailAction.BLOCK,
            severity=Severity.MEDIUM,
            description="Prevents requests that exceed token limits"
        ))
    
    def register_rule(self, rule: GuardrailRule):
        """Register a guardrail rule."""
        self.rules[rule.name] = rule
    
    def disable_rule(self, rule_name: str):
        """Disable a specific rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
    
    def enable_rule(self, rule_name: str):
        """Enable a specific rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
    
    def set_allowed_topics(self, topics: List[str]):
        """Set allowed topics (None to allow all)."""
        self.allowed_topics = set(topics) if topics else None
    
    # ==================== Check Methods ====================
    
    async def check_input(
        self,
        content: str,
        user_id: str = "default",
        context: Dict[str, Any] = None
    ) -> GuardrailResult:
        """
        Check user input against all input guardrails.
        
        Args:
            content: User input to check
            user_id: User identifier for rate limiting
            context: Additional context
            
        Returns:
            GuardrailResult with pass/fail and any violations
        """
        if not self.enabled:
            return GuardrailResult(passed=True, content=content)
        
        ctx = context or {}
        violations = []
        
        # Check rate limit first
        rate_result = self._check_rate_limit(user_id)
        if rate_result:
            violations.append(rate_result)
            return GuardrailResult(
                passed=False,
                blocked=True,
                violations=violations,
                reason="Rate limit exceeded"
            )
        
        # Run input guardrails
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            if rule.guardrail_type != GuardrailType.INPUT:
                continue
            
            violation = rule.check_fn(content, ctx)
            if violation:
                violation.action_taken = rule.action
                violations.append(violation)
                self._log_violation(violation)
                
                if rule.action == GuardrailAction.BLOCK:
                    return GuardrailResult(
                        passed=False,
                        blocked=True,
                        violations=violations,
                        reason=violation.message
                    )
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            content=content
        )
    
    async def check_output(
        self,
        content: str,
        context: Dict[str, Any] = None
    ) -> GuardrailResult:
        """
        Check AI output against all output guardrails.
        
        Args:
            content: AI response to check
            context: Additional context
            
        Returns:
            GuardrailResult with potentially modified content
        """
        if not self.enabled:
            return GuardrailResult(passed=True, content=content)
        
        ctx = context or {}
        violations = []
        modified_content = content
        was_modified = False
        
        # Run output and PII guardrails
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            if rule.guardrail_type not in [GuardrailType.OUTPUT, GuardrailType.PII]:
                continue
            
            violation = rule.check_fn(modified_content, ctx)
            if violation:
                violation.action_taken = rule.action
                violations.append(violation)
                self._log_violation(violation)
                
                if rule.action == GuardrailAction.BLOCK:
                    return GuardrailResult(
                        passed=False,
                        blocked=True,
                        violations=violations,
                        reason=violation.message
                    )
                elif rule.action == GuardrailAction.MODIFY:
                    modified_content = self._redact_content(
                        modified_content,
                        violation.matched_content
                    )
                    was_modified = True
        
        return GuardrailResult(
            passed=True,
            violations=violations,
            content=modified_content,
            modified=was_modified
        )
    
    async def check_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str = "default"
    ) -> GuardrailResult:
        """
        Check if a tool call is allowed.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments
            user_id: User identifier
            
        Returns:
            GuardrailResult indicating if tool call is allowed
        """
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        violations = []
        
        # Check if tool is restricted
        if tool_name in self.RESTRICTED_TOOLS:
            config = self.RESTRICTED_TOOLS[tool_name]
            
            if config.get("requires_approval", False):
                return GuardrailResult(
                    passed=False,
                    violations=[GuardrailViolation(
                        guardrail_type=GuardrailType.TOOL,
                        rule_name=f"restricted_tool_{tool_name}",
                        severity=config.get("severity", Severity.MEDIUM),
                        message=f"Tool '{tool_name}' requires approval before use",
                        action_taken=GuardrailAction.REQUIRE_APPROVAL
                    )],
                    reason=f"Tool '{tool_name}' requires human approval"
                )
        
        # Check arguments for dangerous patterns
        args_str = str(arguments)
        for pattern in self.HARMFUL_PATTERNS:
            if re.search(pattern, args_str, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    guardrail_type=GuardrailType.TOOL,
                    rule_name="dangerous_tool_args",
                    severity=Severity.CRITICAL,
                    message="Tool arguments contain potentially dangerous content"
                ))
                return GuardrailResult(
                    passed=False,
                    blocked=True,
                    violations=violations,
                    reason="Dangerous content in tool arguments"
                )
        
        return GuardrailResult(passed=True, violations=violations)
    
    def check_cost(
        self,
        tokens: int,
        model: str = "gpt-4o-mini",
        user_id: str = "default"
    ) -> GuardrailResult:
        """
        Check if token usage is within limits.
        
        Args:
            tokens: Number of tokens used
            model: Model name for cost calculation
            user_id: User identifier
            
        Returns:
            GuardrailResult indicating if within limits
        """
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        violations = []
        
        # Check per-request limit
        if tokens > self.max_tokens_per_request:
            violations.append(GuardrailViolation(
                guardrail_type=GuardrailType.COST,
                rule_name="max_tokens_exceeded",
                severity=Severity.MEDIUM,
                message=f"Token count ({tokens}) exceeds per-request limit ({self.max_tokens_per_request})"
            ))
        
        # Check daily limit
        self._daily_tokens[user_id] += tokens
        if self._daily_tokens[user_id] > self.daily_token_limit:
            violations.append(GuardrailViolation(
                guardrail_type=GuardrailType.COST,
                rule_name="daily_limit_exceeded",
                severity=Severity.HIGH,
                message=f"Daily token limit ({self.daily_token_limit}) exceeded"
            ))
        
        if violations:
            return GuardrailResult(
                passed=False,
                blocked=True,
                violations=violations,
                reason=violations[0].message
            )
        
        return GuardrailResult(passed=True)
    
    # ==================== Helper Methods ====================
    
    def _check_rate_limit(self, user_id: str) -> Optional[GuardrailViolation]:
        """Check rate limit for user."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.rate_limit_window)
        
        # Clean old entries
        self._rate_limits[user_id] = [
            t for t in self._rate_limits[user_id] if t > window_start
        ]
        
        # Check limit
        if len(self._rate_limits[user_id]) >= self.rate_limit_requests:
            return GuardrailViolation(
                guardrail_type=GuardrailType.RATE_LIMIT,
                rule_name="rate_limit",
                severity=Severity.MEDIUM,
                message=f"Rate limit exceeded ({self.rate_limit_requests} requests per {self.rate_limit_window}s)"
            )
        
        # Add current request
        self._rate_limits[user_id].append(now)
        return None
    
    def _redact_content(self, content: str, matched: str) -> str:
        """Redact matched content from string."""
        if not matched:
            return content
        return content.replace(matched, "[REDACTED]")
    
    def _log_violation(self, violation: GuardrailViolation):
        """Log a violation for audit."""
        self.violations_log.append(violation)
        # Keep only last 1000 violations
        if len(self.violations_log) > 1000:
            self.violations_log = self.violations_log[-1000:]
    
    # ==================== Reporting Methods ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrail statistics."""
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_rule = defaultdict(int)
        
        for v in self.violations_log:
            by_type[v.guardrail_type.value] += 1
            by_severity[v.severity.value] += 1
            by_rule[v.rule_name] += 1
        
        return {
            "enabled": self.enabled,
            "total_violations": len(self.violations_log),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "by_rule": dict(by_rule),
            "rules_count": len(self.rules),
            "active_rules": len([r for r in self.rules.values() if r.enabled])
        }
    
    def get_recent_violations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent violations."""
        return [v.to_dict() for v in self.violations_log[-limit:]]
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """List all registered rules."""
        return [
            {
                "name": rule.name,
                "type": rule.guardrail_type.value,
                "enabled": rule.enabled,
                "action": rule.action.value,
                "severity": rule.severity.value,
                "description": rule.description
            }
            for rule in self.rules.values()
        ]
    
    def reset_daily_limits(self):
        """Reset daily token limits (call at midnight)."""
        self._daily_tokens.clear()


# Global instance
guardrails = Guardrails()


# ==================== Convenience Functions ====================

async def check_input(content: str, user_id: str = "default") -> GuardrailResult:
    """Check user input against guardrails."""
    return await guardrails.check_input(content, user_id)


async def check_output(content: str) -> GuardrailResult:
    """Check AI output against guardrails."""
    return await guardrails.check_output(content)


async def check_tool(tool_name: str, arguments: Dict[str, Any]) -> GuardrailResult:
    """Check tool call against guardrails."""
    return await guardrails.check_tool_call(tool_name, arguments)


def is_safe_input(content: str) -> bool:
    """Quick sync check if input is safe (blocking patterns only)."""
    for pattern in Guardrails.INJECTION_PATTERNS + Guardrails.HARMFUL_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return False
    return True


"""
Validator Engine - Content validation, fact-checking, and quality assessment.
Uses LLM for semantic validation and rule-based checks.
"""

import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    FACTUAL = "factual"
    GRAMMAR = "grammar"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    SAFETY = "safety"
    STYLE = "style"
    CUSTOM = "custom"


@dataclass
class ValidationIssue:
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    valid: bool
    score: float  # 0.0 to 1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> List[str]:
        return [i.message for i in self.issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]

    @property
    def warnings(self) -> List[str]:
        return [i.message for i in self.issues if i.severity == ValidationSeverity.WARNING]


@dataclass
class FactCheckResult:
    claim: str
    verdict: str  # "supported", "refuted", "unverifiable"
    confidence: float
    evidence: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


# Rule function type
RuleFunction = Callable[[str, Dict[str, Any]], List[ValidationIssue]]


class ValidationRule:
    """A validation rule with a check function"""

    def __init__(
        self,
        name: str,
        category: ValidationCategory,
        check_fn: RuleFunction,
        description: str = ""
    ):
        self.name = name
        self.category = category
        self.check_fn = check_fn
        self.description = description
        self.enabled = True

    def check(self, content: str, context: Dict[str, Any] = None) -> List[ValidationIssue]:
        """Run the validation check"""
        if not self.enabled:
            return []
        return self.check_fn(content, context or {})


class ValidatorEngine:
    """
    Content validation engine with rule-based and LLM-powered checks.
    """

    # LLM validation prompts
    FACT_CHECK_PROMPT = """Analyze the following claim for factual accuracy:

Claim: {claim}

Context (if any): {context}

Evaluate the claim and respond with:
1. VERDICT: "supported", "refuted", or "unverifiable"
2. CONFIDENCE: A number from 0 to 1
3. EVIDENCE: Brief explanation of your reasoning
4. SOURCES: Any relevant knowledge sources

Format your response as:
VERDICT: [verdict]
CONFIDENCE: [number]
EVIDENCE: [explanation]
SOURCES: [sources or "general knowledge"]"""

    CONSISTENCY_CHECK_PROMPT = """Check the following text for internal consistency:

Text:
{text}

Look for:
1. Contradictory statements
2. Logical inconsistencies
3. Conflicting information

List any inconsistencies found, or respond with "No inconsistencies found" if the text is consistent."""

    QUALITY_ASSESSMENT_PROMPT = """Assess the quality of the following content:

Content:
{content}

Evaluate on these criteria (score 0-10 for each):
1. Clarity: Is the content clear and easy to understand?
2. Accuracy: Does the content appear factually accurate?
3. Completeness: Does the content cover the topic adequately?
4. Organization: Is the content well-structured?
5. Relevance: Is the content relevant and on-topic?

Provide scores and brief justification for each."""

    def __init__(self):
        self.llm_router = None
        self.vector_retriever = None
        self.rules: Dict[str, ValidationRule] = {}
        self._register_builtin_rules()

    def set_llm_router(self, router):
        """Set the LLM router for semantic validation"""
        self.llm_router = router

    def set_vector_retriever(self, retriever):
        """Set vector retriever for fact-checking against knowledge base"""
        self.vector_retriever = retriever

    def _register_builtin_rules(self):
        """Register built-in validation rules"""

        # Profanity/safety check
        def check_safety(content: str, ctx: Dict) -> List[ValidationIssue]:
            issues = []
            # Simple profanity check (would be more sophisticated in production)
            profanity_patterns = [
                r'\b(damn|hell|crap)\b',  # Mild
            ]
            for pattern in profanity_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        category=ValidationCategory.SAFETY,
                        severity=ValidationSeverity.WARNING,
                        message="Content may contain inappropriate language",
                        suggestion="Review and revise language for appropriateness"
                    ))
                    break
            return issues

        self.register_rule(ValidationRule(
            name="safety_check",
            category=ValidationCategory.SAFETY,
            check_fn=check_safety,
            description="Check for inappropriate or unsafe content"
        ))

        # Length check
        def check_length(content: str, ctx: Dict) -> List[ValidationIssue]:
            issues = []
            min_len = ctx.get("min_length", 10)
            max_len = ctx.get("max_length", 10000)
            
            if len(content) < min_len:
                issues.append(ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.ERROR,
                    message=f"Content too short (minimum {min_len} characters)",
                    metadata={"length": len(content), "min": min_len}
                ))
            elif len(content) > max_len:
                issues.append(ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    message=f"Content exceeds recommended length ({max_len} characters)",
                    metadata={"length": len(content), "max": max_len}
                ))
            return issues

        self.register_rule(ValidationRule(
            name="length_check",
            category=ValidationCategory.COMPLETENESS,
            check_fn=check_length,
            description="Check content length constraints"
        ))

        # Basic grammar checks
        def check_grammar(content: str, ctx: Dict) -> List[ValidationIssue]:
            issues = []
            
            # Check for repeated words
            repeated = re.findall(r'\b(\w+)\s+\1\b', content, re.IGNORECASE)
            for word in repeated:
                issues.append(ValidationIssue(
                    category=ValidationCategory.GRAMMAR,
                    severity=ValidationSeverity.INFO,
                    message=f"Repeated word: '{word}'",
                    suggestion=f"Consider removing duplicate '{word}'"
                ))
            
            # Check for missing capitalization at sentence start
            if content and not content[0].isupper():
                issues.append(ValidationIssue(
                    category=ValidationCategory.GRAMMAR,
                    severity=ValidationSeverity.INFO,
                    message="Content should start with a capital letter"
                ))
            
            return issues

        self.register_rule(ValidationRule(
            name="grammar_check",
            category=ValidationCategory.GRAMMAR,
            check_fn=check_grammar,
            description="Basic grammar validation"
        ))

        # URL validation
        def check_urls(content: str, ctx: Dict) -> List[ValidationIssue]:
            issues = []
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
            for url in urls:
                # Basic URL format validation
                if not re.match(r'https?://[a-zA-Z0-9]', url):
                    issues.append(ValidationIssue(
                        category=ValidationCategory.CONSISTENCY,
                        severity=ValidationSeverity.WARNING,
                        message=f"Potentially malformed URL: {url[:50]}...",
                        location=url[:50]
                    ))
            return issues

        self.register_rule(ValidationRule(
            name="url_check",
            category=ValidationCategory.CONSISTENCY,
            check_fn=check_urls,
            description="Validate URL formats in content"
        ))

    def register_rule(self, rule: ValidationRule):
        """Register a validation rule"""
        self.rules[rule.name] = rule

    def enable_rule(self, name: str):
        """Enable a rule by name"""
        if name in self.rules:
            self.rules[name].enabled = True

    def disable_rule(self, name: str):
        """Disable a rule by name"""
        if name in self.rules:
            self.rules[name].enabled = False

    async def validate(
        self,
        content: str,
        rules: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True
    ) -> ValidationResult:
        """
        Validate content using registered rules and optional LLM checks.
        
        Args:
            content: The content to validate
            rules: Specific rule names to run (None = all rules)
            context: Additional context for validation
            use_llm: Whether to use LLM for semantic validation
            
        Returns:
            ValidationResult with issues and score
        """
        all_issues = []
        context = context or {}

        # Run rule-based validation
        rules_to_run = self.rules.values()
        if rules:
            rules_to_run = [r for r in self.rules.values() if r.name in rules]

        for rule in rules_to_run:
            try:
                issues = rule.check(content, context)
                all_issues.extend(issues)
            except Exception as e:
                all_issues.append(ValidationIssue(
                    category=ValidationCategory.CUSTOM,
                    severity=ValidationSeverity.WARNING,
                    message=f"Rule '{rule.name}' failed: {str(e)}"
                ))

        # LLM-based consistency check
        if use_llm and self.llm_router and len(content) > 100:
            llm_issues = await self._llm_consistency_check(content)
            all_issues.extend(llm_issues)

        # Calculate score
        score = self._calculate_score(all_issues)

        # Determine validity
        critical_errors = [i for i in all_issues if i.severity == ValidationSeverity.CRITICAL]
        errors = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
        
        valid = len(critical_errors) == 0 and len(errors) == 0

        return ValidationResult(
            valid=valid,
            score=score,
            issues=all_issues,
            metadata={
                "rules_run": len(list(rules_to_run)),
                "llm_used": use_llm and self.llm_router is not None
            }
        )

    async def _llm_consistency_check(self, content: str) -> List[ValidationIssue]:
        """Use LLM to check for internal consistency"""
        if not self.llm_router:
            return []

        try:
            prompt = self.CONSISTENCY_CHECK_PROMPT.format(text=content[:3000])
            
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            result = response.get("content", "")
            
            if "no inconsistencies" not in result.lower():
                return [ValidationIssue(
                    category=ValidationCategory.CONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    message="Potential consistency issues detected",
                    suggestion=result[:500],
                    metadata={"llm_analysis": result}
                )]
        
        except Exception:
            pass
        
        return []

    def _calculate_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate validation score based on issues"""
        if not issues:
            return 1.0
        
        # Penalty weights by severity
        weights = {
            ValidationSeverity.INFO: 0.02,
            ValidationSeverity.WARNING: 0.1,
            ValidationSeverity.ERROR: 0.3,
            ValidationSeverity.CRITICAL: 0.5
        }
        
        total_penalty = sum(weights.get(i.severity, 0) for i in issues)
        score = max(0.0, 1.0 - total_penalty)
        
        return round(score, 2)

    async def fact_check(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> FactCheckResult:
        """
        Fact-check a specific claim.
        
        Args:
            claim: The claim to verify
            context: Additional context
            
        Returns:
            FactCheckResult with verdict and evidence
        """
        evidence = []
        sources = []

        # Search knowledge base if available
        if self.vector_retriever:
            try:
                results = await self.vector_retriever.search(claim, top_k=3)
                for r in results:
                    evidence.append(r.content[:200])
                    if "source" in r.metadata:
                        sources.append(r.metadata["source"])
            except Exception:
                pass

        # Use LLM for fact checking
        if not self.llm_router:
            return FactCheckResult(
                claim=claim,
                verdict="unverifiable",
                confidence=0.0,
                evidence=["LLM router not configured"]
            )

        try:
            prompt = self.FACT_CHECK_PROMPT.format(
                claim=claim,
                context=context or "None provided"
            )
            
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            result = response.get("content", "")
            
            # Parse response
            verdict = "unverifiable"
            confidence = 0.5
            
            if "VERDICT:" in result:
                verdict_match = re.search(r'VERDICT:\s*(\w+)', result, re.IGNORECASE)
                if verdict_match:
                    v = verdict_match.group(1).lower()
                    if v in ("supported", "refuted", "unverifiable"):
                        verdict = v
            
            if "CONFIDENCE:" in result:
                conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', result)
                if conf_match:
                    try:
                        confidence = float(conf_match.group(1))
                        confidence = min(1.0, max(0.0, confidence))
                    except ValueError:
                        pass
            
            if "EVIDENCE:" in result:
                ev_match = re.search(r'EVIDENCE:\s*(.+?)(?=SOURCES:|$)', result, re.DOTALL)
                if ev_match:
                    evidence.insert(0, ev_match.group(1).strip())
            
            return FactCheckResult(
                claim=claim,
                verdict=verdict,
                confidence=confidence,
                evidence=evidence,
                sources=sources or ["LLM knowledge"]
            )
        
        except Exception as e:
            return FactCheckResult(
                claim=claim,
                verdict="unverifiable",
                confidence=0.0,
                evidence=[f"Error: {str(e)}"]
            )

    async def assess_quality(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        Assess overall content quality.
        
        Args:
            content: Content to assess
            
        Returns:
            Quality assessment with scores
        """
        if not self.llm_router:
            return {
                "overall_score": 0,
                "error": "LLM router not configured"
            }

        try:
            prompt = self.QUALITY_ASSESSMENT_PROMPT.format(content=content[:3000])
            
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            result = response.get("content", "")
            
            # Parse scores
            scores = {}
            for criterion in ["Clarity", "Accuracy", "Completeness", "Organization", "Relevance"]:
                match = re.search(rf'{criterion}[:\s]+(\d+)', result, re.IGNORECASE)
                if match:
                    scores[criterion.lower()] = int(match.group(1))
            
            overall = sum(scores.values()) / len(scores) if scores else 0
            
            return {
                "overall_score": round(overall, 1),
                "scores": scores,
                "analysis": result
            }
        
        except Exception as e:
            return {
                "overall_score": 0,
                "error": str(e)
            }

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all registered validation rules"""
        return [
            {
                "name": rule.name,
                "category": rule.category.value,
                "description": rule.description,
                "enabled": rule.enabled
            }
            for rule in self.rules.values()
        ]


# Singleton instance
validator_engine = ValidatorEngine()


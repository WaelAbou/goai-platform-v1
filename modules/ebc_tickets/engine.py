"""
EBC Ticket Analysis Engine.

This module analyzes customer care tickets for:
- Sentiment (positive, negative, neutral)
- Priority (critical, high, medium, low)
- Category (billing, technical, account, general)
- Suggested response
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import sqlite3
import os
import json
import secrets


class TicketPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"
    FEEDBACK = "feedback"
    OTHER = "other"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


@dataclass
class TicketAnalysis:
    """Result of ticket analysis."""
    ticket_id: str
    sentiment: SentimentType
    sentiment_score: float  # -1 to 1
    priority: TicketPriority
    category: TicketCategory
    keywords: List[str] = field(default_factory=list)
    urgency_indicators: List[str] = field(default_factory=list)
    suggested_response: Optional[str] = None
    estimated_resolution_time: Optional[str] = None
    escalation_needed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/ebc_tickets.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            customer_name TEXT,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            channel TEXT DEFAULT 'email',
            agent_id TEXT,
            status TEXT DEFAULT 'open',
            sentiment TEXT,
            sentiment_score REAL,
            priority TEXT,
            category TEXT,
            keywords TEXT,
            suggested_response TEXT,
            escalation_needed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            metadata TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_analytics (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            total_tickets INTEGER DEFAULT 0,
            positive_count INTEGER DEFAULT 0,
            negative_count INTEGER DEFAULT 0,
            neutral_count INTEGER DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            avg_sentiment_score REAL,
            top_categories TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_sentiment ON tickets(sentiment)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at)")
    
    conn.commit()
    conn.close()


init_db()


class TicketAnalyzer:
    """
    Analyzes customer care tickets using LLM and rule-based methods.
    """
    
    def __init__(self, llm_router=None):
        self.llm_router = llm_router
        
        # Priority keywords
        self.critical_keywords = [
            "urgent", "emergency", "immediately", "asap", "critical",
            "down", "outage", "not working", "broken", "failed",
            "legal", "lawsuit", "lawyer", "regulatory"
        ]
        self.high_keywords = [
            "important", "soon", "frustrated", "angry", "disappointed",
            "escalate", "manager", "supervisor", "unacceptable"
        ]
        
        # Category keywords
        self.category_keywords = {
            TicketCategory.BILLING: ["invoice", "payment", "charge", "bill", "refund", "price", "cost", "fee"],
            TicketCategory.TECHNICAL: ["error", "bug", "crash", "slow", "not loading", "technical", "api", "integration"],
            TicketCategory.ACCOUNT: ["login", "password", "account", "access", "permission", "profile", "settings"],
            TicketCategory.COMPLAINT: ["complaint", "unhappy", "terrible", "worst", "never again", "cancel"],
            TicketCategory.INQUIRY: ["how to", "question", "wondering", "can i", "is it possible", "information"],
            TicketCategory.FEEDBACK: ["suggestion", "feedback", "idea", "feature request", "would be nice"]
        }
        
        # Sentiment indicators
        self.negative_indicators = [
            "angry", "frustrated", "disappointed", "terrible", "awful",
            "worst", "hate", "unacceptable", "ridiculous", "waste"
        ]
        self.positive_indicators = [
            "thank", "appreciate", "great", "excellent", "amazing",
            "helpful", "wonderful", "love", "fantastic", "best"
        ]
    
    def set_llm_router(self, llm_router):
        """Set the LLM router for advanced analysis."""
        self.llm_router = llm_router
    
    async def analyze(self, ticket_content: str, subject: str = "", use_llm: bool = True) -> TicketAnalysis:
        """
        Analyze a customer care ticket.
        
        Args:
            ticket_content: The main content of the ticket
            subject: The ticket subject line
            use_llm: Whether to use LLM for deeper analysis
        
        Returns:
            TicketAnalysis with sentiment, priority, category, etc.
        """
        ticket_id = f"ticket_{secrets.token_hex(8)}"
        combined_text = f"{subject} {ticket_content}".lower()
        
        # Rule-based analysis first
        sentiment, sentiment_score = self._analyze_sentiment_rules(combined_text)
        priority = self._detect_priority(combined_text)
        category = self._detect_category(combined_text)
        keywords = self._extract_keywords(combined_text)
        urgency_indicators = self._find_urgency_indicators(combined_text)
        
        # LLM-enhanced analysis
        suggested_response = None
        if use_llm and self.llm_router:
            llm_result = await self._analyze_with_llm(ticket_content, subject)
            if llm_result:
                # Override with LLM results if available
                if llm_result.get("sentiment"):
                    sentiment = SentimentType(llm_result["sentiment"])
                if llm_result.get("sentiment_score") is not None:
                    sentiment_score = llm_result["sentiment_score"]
                if llm_result.get("priority"):
                    priority = TicketPriority(llm_result["priority"])
                if llm_result.get("category"):
                    category = TicketCategory(llm_result["category"])
                suggested_response = llm_result.get("suggested_response")
        
        # Determine if escalation is needed
        escalation_needed = (
            priority in [TicketPriority.CRITICAL, TicketPriority.HIGH] and
            sentiment == SentimentType.NEGATIVE and
            sentiment_score < -0.5
        )
        
        # Estimate resolution time
        resolution_time = self._estimate_resolution_time(priority, category)
        
        analysis = TicketAnalysis(
            ticket_id=ticket_id,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            priority=priority,
            category=category,
            keywords=keywords,
            urgency_indicators=urgency_indicators,
            suggested_response=suggested_response,
            estimated_resolution_time=resolution_time,
            escalation_needed=escalation_needed
        )
        
        return analysis
    
    def _analyze_sentiment_rules(self, text: str) -> tuple[SentimentType, float]:
        """Rule-based sentiment analysis."""
        negative_count = sum(1 for word in self.negative_indicators if word in text)
        positive_count = sum(1 for word in self.positive_indicators if word in text)
        
        total = negative_count + positive_count
        if total == 0:
            return SentimentType.NEUTRAL, 0.0
        
        score = (positive_count - negative_count) / max(total, 1)
        score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
        
        if score > 0.3:
            return SentimentType.POSITIVE, score
        elif score < -0.3:
            return SentimentType.NEGATIVE, score
        elif negative_count > 0 and positive_count > 0:
            return SentimentType.MIXED, score
        else:
            return SentimentType.NEUTRAL, score
    
    def _detect_priority(self, text: str) -> TicketPriority:
        """Detect ticket priority based on keywords."""
        if any(kw in text for kw in self.critical_keywords):
            return TicketPriority.CRITICAL
        if any(kw in text for kw in self.high_keywords):
            return TicketPriority.HIGH
        return TicketPriority.MEDIUM
    
    def _detect_category(self, text: str) -> TicketCategory:
        """Detect ticket category based on keywords."""
        scores = {}
        for category, keywords in self.category_keywords.items():
            scores[category] = sum(1 for kw in keywords if kw in text)
        
        if max(scores.values()) == 0:
            return TicketCategory.OTHER
        
        return max(scores, key=scores.get)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        all_keywords = (
            self.critical_keywords + 
            self.high_keywords + 
            self.negative_indicators + 
            self.positive_indicators
        )
        return [kw for kw in all_keywords if kw in text]
    
    def _find_urgency_indicators(self, text: str) -> List[str]:
        """Find urgency indicators in text."""
        indicators = []
        if "urgent" in text or "asap" in text:
            indicators.append("Time-sensitive")
        if "manager" in text or "supervisor" in text:
            indicators.append("Escalation requested")
        if "cancel" in text:
            indicators.append("Churn risk")
        if "refund" in text:
            indicators.append("Refund request")
        if any(word in text for word in ["legal", "lawyer", "lawsuit"]):
            indicators.append("Legal mention")
        return indicators
    
    def _estimate_resolution_time(self, priority: TicketPriority, category: TicketCategory) -> str:
        """Estimate resolution time based on priority and category."""
        base_times = {
            TicketPriority.CRITICAL: "1-4 hours",
            TicketPriority.HIGH: "4-8 hours",
            TicketPriority.MEDIUM: "1-2 days",
            TicketPriority.LOW: "3-5 days"
        }
        return base_times.get(priority, "Unknown")
    
    async def _analyze_with_llm(self, content: str, subject: str) -> Optional[Dict[str, Any]]:
        """Use LLM for deeper analysis."""
        if not self.llm_router:
            return None
        
        prompt = f"""Analyze this customer support ticket and provide structured analysis.

Subject: {subject}
Content: {content}

Respond in JSON format:
{{
    "sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": -1.0 to 1.0,
    "priority": "critical|high|medium|low",
    "category": "billing|technical|account|complaint|inquiry|feedback|other",
    "suggested_response": "A brief, empathetic response template",
    "key_issue": "One sentence summary of the main issue"
}}

Only return valid JSON, no other text."""

        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response.get("content", "{}")
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"LLM analysis error: {e}")
        
        return None
    
    # ==========================================
    # Ticket Storage & Retrieval
    # ==========================================
    
    def save_ticket(self, analysis: TicketAnalysis, customer_id: str = None, 
                   customer_name: str = None, subject: str = "", content: str = "",
                   channel: str = "email", agent_id: str = None) -> str:
        """Save analyzed ticket to database."""
        conn = get_db()
        now = datetime.now().isoformat()
        
        conn.execute("""
            INSERT INTO tickets (
                id, customer_id, customer_name, subject, content, channel,
                agent_id, status, sentiment, sentiment_score, priority, category,
                keywords, suggested_response, escalation_needed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.ticket_id,
            customer_id,
            customer_name,
            subject,
            content,
            channel,
            agent_id,
            analysis.sentiment.value,
            analysis.sentiment_score,
            analysis.priority.value,
            analysis.category.value,
            json.dumps(analysis.keywords),
            analysis.suggested_response,
            1 if analysis.escalation_needed else 0,
            now,
            now
        ))
        conn.commit()
        conn.close()
        
        return analysis.ticket_id
    
    def get_tickets(self, status: str = None, priority: str = None, 
                   sentiment: str = None, limit: int = 50) -> List[Dict]:
        """Get tickets with optional filters."""
        conn = get_db()
        
        query = "SELECT * FROM tickets WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if sentiment:
            query += " AND sentiment = ?"
            params.append(sentiment)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get ticket analytics summary."""
        conn = get_db()
        
        # Total counts
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        
        # By sentiment
        sentiment_counts = {}
        for sentiment in ["positive", "negative", "neutral", "mixed"]:
            count = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE sentiment = ?",
                (sentiment,)
            ).fetchone()[0]
            sentiment_counts[sentiment] = count
        
        # By priority
        priority_counts = {}
        for priority in ["critical", "high", "medium", "low"]:
            count = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE priority = ?",
                (priority,)
            ).fetchone()[0]
            priority_counts[priority] = count
        
        # By category
        category_counts = {}
        for category in ["billing", "technical", "account", "complaint", "inquiry", "feedback", "other"]:
            count = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE category = ?",
                (category,)
            ).fetchone()[0]
            if count > 0:
                category_counts[category] = count
        
        # Average sentiment
        avg_sentiment = conn.execute(
            "SELECT AVG(sentiment_score) FROM tickets"
        ).fetchone()[0] or 0
        
        # Open vs resolved
        open_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'open'"
        ).fetchone()[0]
        
        # Escalation rate
        escalated = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE escalation_needed = 1"
        ).fetchone()[0]
        
        conn.close()
        
        return {
            "total_tickets": total,
            "by_sentiment": sentiment_counts,
            "by_priority": priority_counts,
            "by_category": category_counts,
            "average_sentiment_score": round(avg_sentiment, 2),
            "open_tickets": open_count,
            "resolved_tickets": total - open_count,
            "escalation_rate": round(escalated / max(total, 1) * 100, 1)
        }


# Singleton instance
ticket_analyzer = TicketAnalyzer()


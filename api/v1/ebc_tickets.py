"""
EBC Customer Care Ticket Analysis API.

Endpoints for analyzing, storing, and retrieving customer support tickets.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from modules.ebc_tickets import ticket_analyzer, TicketAnalysis, TicketPriority, TicketCategory
from core.llm import llm_router
from core.auth import get_user_id_flexible

router = APIRouter()

# Wire up LLM
ticket_analyzer.set_llm_router(llm_router)


# ==========================================
# Request/Response Models
# ==========================================

class AnalyzeTicketRequest(BaseModel):
    """Request to analyze a ticket."""
    subject: str = Field("", description="Ticket subject line")
    content: str = Field(..., description="Ticket content/body")
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    channel: str = Field("email", description="Support channel (email, chat, phone)")
    use_llm: bool = Field(True, description="Use LLM for deeper analysis")
    save_ticket: bool = Field(True, description="Save ticket to database")


class TicketResponse(BaseModel):
    """Analyzed ticket response."""
    ticket_id: str
    sentiment: str
    sentiment_score: float
    priority: str
    category: str
    keywords: List[str]
    urgency_indicators: List[str]
    suggested_response: Optional[str]
    estimated_resolution_time: Optional[str]
    escalation_needed: bool


class BulkAnalyzeRequest(BaseModel):
    """Request to analyze multiple tickets."""
    tickets: List[Dict[str, str]]  # List of {subject, content}
    use_llm: bool = False  # Disable LLM for bulk to save costs


class UpdateTicketRequest(BaseModel):
    """Request to update ticket status."""
    status: Optional[str] = None  # open, in_progress, resolved, closed
    agent_id: Optional[str] = None
    resolution_notes: Optional[str] = None


# ==========================================
# API Endpoints
# ==========================================

@router.post("/analyze", response_model=TicketResponse)
async def analyze_ticket(request: AnalyzeTicketRequest, user_id: str = Depends(get_user_id_flexible)):
    """
    Analyze a customer support ticket.
    
    Returns sentiment, priority, category, and suggested response.
    
    Example:
    ```
    POST /api/v1/ebc-tickets/analyze
    {
        "subject": "URGENT: Cannot access my account",
        "content": "I've been trying to login for 3 hours and keep getting an error. This is unacceptable! I need to access my invoices urgently.",
        "customer_name": "John Smith",
        "channel": "email"
    }
    ```
    """
    analysis = await ticket_analyzer.analyze(
        ticket_content=request.content,
        subject=request.subject,
        use_llm=request.use_llm
    )
    
    # Save to database if requested
    if request.save_ticket:
        ticket_analyzer.save_ticket(
            analysis=analysis,
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            subject=request.subject,
            content=request.content,
            channel=request.channel
        )
    
    return TicketResponse(
        ticket_id=analysis.ticket_id,
        sentiment=analysis.sentiment.value,
        sentiment_score=analysis.sentiment_score,
        priority=analysis.priority.value,
        category=analysis.category.value,
        keywords=analysis.keywords,
        urgency_indicators=analysis.urgency_indicators,
        suggested_response=analysis.suggested_response,
        estimated_resolution_time=analysis.estimated_resolution_time,
        escalation_needed=analysis.escalation_needed
    )


@router.post("/analyze/bulk")
async def analyze_bulk(request: BulkAnalyzeRequest):
    """
    Analyze multiple tickets at once.
    
    Useful for batch processing imported tickets.
    """
    results = []
    
    for ticket in request.tickets[:100]:  # Limit to 100
        analysis = await ticket_analyzer.analyze(
            ticket_content=ticket.get("content", ""),
            subject=ticket.get("subject", ""),
            use_llm=request.use_llm
        )
        
        results.append({
            "ticket_id": analysis.ticket_id,
            "sentiment": analysis.sentiment.value,
            "sentiment_score": analysis.sentiment_score,
            "priority": analysis.priority.value,
            "category": analysis.category.value,
            "escalation_needed": analysis.escalation_needed
        })
    
    return {
        "analyzed": len(results),
        "results": results,
        "summary": {
            "negative": len([r for r in results if r["sentiment"] == "negative"]),
            "critical": len([r for r in results if r["priority"] == "critical"]),
            "escalations": len([r for r in results if r["escalation_needed"]])
        }
    }


@router.get("/tickets")
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = 50
):
    """
    List tickets with optional filters.
    
    Filters:
    - status: open, in_progress, resolved, closed
    - priority: critical, high, medium, low
    - sentiment: positive, negative, neutral, mixed
    """
    tickets = ticket_analyzer.get_tickets(
        status=status,
        priority=priority,
        sentiment=sentiment,
        limit=limit
    )
    
    return {
        "tickets": tickets,
        "count": len(tickets)
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get a specific ticket by ID."""
    from modules.ebc_tickets.engine import get_db
    
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM tickets WHERE id = ?",
        (ticket_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return dict(row)


@router.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, update: UpdateTicketRequest):
    """Update ticket status or assign agent."""
    from modules.ebc_tickets.engine import get_db
    
    conn = get_db()
    
    # Check exists
    existing = conn.execute(
        "SELECT id FROM tickets WHERE id = ?",
        (ticket_id,)
    ).fetchone()
    
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Build update
    updates = ["updated_at = ?"]
    params = [datetime.now().isoformat()]
    
    if update.status:
        updates.append("status = ?")
        params.append(update.status)
        if update.status == "resolved":
            updates.append("resolved_at = ?")
            params.append(datetime.now().isoformat())
    
    if update.agent_id:
        updates.append("agent_id = ?")
        params.append(update.agent_id)
    
    params.append(ticket_id)
    
    conn.execute(
        f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    conn.close()
    
    return {"message": "Ticket updated", "ticket_id": ticket_id}


@router.get("/analytics")
async def get_analytics():
    """
    Get ticket analytics dashboard data.
    
    Returns:
    - Total tickets
    - Breakdown by sentiment, priority, category
    - Escalation rate
    - Open vs resolved counts
    """
    return ticket_analyzer.get_analytics()


@router.get("/dashboard")
async def get_dashboard():
    """
    Get comprehensive dashboard data for EBC ticket management.
    """
    analytics = ticket_analyzer.get_analytics()
    
    # Get recent critical tickets
    critical_tickets = ticket_analyzer.get_tickets(
        priority="critical",
        status="open",
        limit=5
    )
    
    # Get recent negative tickets needing attention
    negative_tickets = ticket_analyzer.get_tickets(
        sentiment="negative",
        status="open",
        limit=5
    )
    
    return {
        "analytics": analytics,
        "critical_tickets": critical_tickets,
        "negative_tickets": negative_tickets,
        "alerts": [
            {"type": "warning", "message": f"{analytics['by_priority'].get('critical', 0)} critical tickets need attention"}
            if analytics['by_priority'].get('critical', 0) > 0 else None,
            {"type": "info", "message": f"Escalation rate: {analytics['escalation_rate']}%"}
        ]
    }


# ==========================================
# Demo Data
# ==========================================

@router.post("/demo/seed")
async def seed_demo_data():
    """
    Seed demo tickets for testing.
    """
    demo_tickets = [
        {
            "subject": "URGENT: Payment failed, account locked!",
            "content": "I tried to make a payment and now my account is completely locked. This is unacceptable! I have an important deadline and need access immediately. Your support line kept me waiting for 45 minutes!",
            "customer_name": "Sarah Johnson",
            "channel": "email"
        },
        {
            "subject": "Question about billing",
            "content": "Hi, I was wondering if you could explain the charges on my latest invoice. I see a line item for 'premium support' but I don't remember signing up for that. Thanks!",
            "customer_name": "Mike Chen",
            "channel": "chat"
        },
        {
            "subject": "Great experience!",
            "content": "Just wanted to say thank you to your support team, especially Alex. They helped me resolve my issue quickly and were very patient. Excellent service!",
            "customer_name": "Emily Davis",
            "channel": "email"
        },
        {
            "subject": "API integration not working",
            "content": "We're getting timeout errors when calling your API. This started yesterday around 3pm. Error code: 504. Our production system is affected.",
            "customer_name": "Tech Team - Acme Corp",
            "channel": "email"
        },
        {
            "subject": "Cancel my subscription",
            "content": "I want to cancel my subscription immediately. The service has been terrible and I'm very disappointed. I've been a customer for 2 years but can't take this anymore.",
            "customer_name": "Robert Wilson",
            "channel": "phone"
        }
    ]
    
    results = []
    for ticket in demo_tickets:
        analysis = await ticket_analyzer.analyze(
            ticket_content=ticket["content"],
            subject=ticket["subject"],
            use_llm=False  # Fast for demo
        )
        
        ticket_analyzer.save_ticket(
            analysis=analysis,
            customer_name=ticket["customer_name"],
            subject=ticket["subject"],
            content=ticket["content"],
            channel=ticket["channel"]
        )
        
        results.append({
            "ticket_id": analysis.ticket_id,
            "customer": ticket["customer_name"],
            "sentiment": analysis.sentiment.value,
            "priority": analysis.priority.value
        })
    
    return {
        "message": f"Created {len(results)} demo tickets",
        "tickets": results
    }


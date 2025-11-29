"""
EBC Customer Care Ticket Analysis Module.

Features:
- Sentiment analysis for support tickets
- Priority classification
- Category detection
- Trend analysis
- Agent performance metrics
"""

from .engine import TicketAnalyzer, TicketAnalysis, TicketPriority, TicketCategory, ticket_analyzer

__all__ = ["TicketAnalyzer", "TicketAnalysis", "TicketPriority", "TicketCategory", "ticket_analyzer"]


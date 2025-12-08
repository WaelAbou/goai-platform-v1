"""
Meeting Notes Summarizer Module

Features:
- Extract action items from meeting notes
- Identify participants and assignments
- Generate executive summaries
- Prioritize tasks automatically
"""

from .engine import (
    MeetingNotesEngine,
    meeting_notes_engine,
    MeetingSummary,
    ActionItem,
    Priority
)

__all__ = [
    "MeetingNotesEngine",
    "meeting_notes_engine",
    "MeetingSummary",
    "ActionItem",
    "Priority"
]


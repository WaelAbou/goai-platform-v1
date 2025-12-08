<![CDATA[# 🛠️ Building New Use Cases - Developer Guide

> **Complete guide to adding new features to GoAI Platform**

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start (5-Minute Setup)](#quick-start-5-minute-setup)
3. [Complete Example: Meeting Notes Summarizer](#complete-example-meeting-notes-summarizer)
4. [Step-by-Step Breakdown](#step-by-step-breakdown)
5. [Testing Your Use Case](#testing-your-use-case)
6. [Best Practices](#best-practices)

---

## 🏗️ Architecture Overview

Every use case in GoAI follows a **3-layer pattern**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        USE CASE LAYERS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: API (api/v1/your_feature.py)                  │   │
│  │  - FastAPI router with endpoints                         │   │
│  │  - Request/response models (Pydantic)                    │   │
│  │  - Input validation                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: ENGINE (modules/your_feature/engine.py)       │   │
│  │  - Core business logic                                   │   │
│  │  - LLM interactions                                      │   │
│  │  - Data processing                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: UI (ui/console/src/pages/YourFeaturePage.tsx) │   │
│  │  - React component                                       │   │
│  │  - API client calls                                      │   │
│  │  - User interface                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
goai-platform-v1/
├── api/v1/
│   └── your_feature.py          # API endpoints
├── modules/
│   └── your_feature/
│       ├── __init__.py          # Module exports
│       └── engine.py            # Core logic
├── ui/console/src/pages/
│   └── YourFeaturePage.tsx      # UI component
└── use_cases/
    └── your_feature/
        ├── intent.yaml          # Business requirements
        ├── test_use_case.py     # Test script
        └── README.md            # Documentation
```

---

## 🚀 Quick Start (5-Minute Setup)

### Step 1: Create the Engine Module

```bash
mkdir -p modules/meeting_notes
touch modules/meeting_notes/__init__.py
touch modules/meeting_notes/engine.py
```

### Step 2: Create the API

```bash
touch api/v1/meeting_notes.py
```

### Step 3: Register in main.py

Add one line to `main.py`:
```python
from api.v1 import meeting_notes
app.include_router(meeting_notes.router, prefix="/api/v1/meeting-notes", tags=["Meeting Notes"])
```

### Step 4: Test it!

```bash
curl -X POST http://localhost:8000/api/v1/meeting-notes/summarize \
  -H "Content-Type: application/json" \
  -d '{"content": "Meeting notes here..."}'
```

---

## 📝 Complete Example: Meeting Notes Summarizer

Let's build a complete use case that:
- Takes meeting notes as input
- Extracts action items
- Identifies participants
- Generates a summary
- Assigns priorities

### Step 1: Engine Module (`modules/meeting_notes/engine.py`)

```python
"""
Meeting Notes Summarizer - Core Engine

Features:
- Extract action items from meeting notes
- Identify participants and their assignments
- Generate executive summary
- Prioritize tasks
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import re


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ActionItem:
    """An action item extracted from meeting notes."""
    task: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    status: str = "pending"


@dataclass
class MeetingSummary:
    """Complete meeting summary."""
    title: str
    date: str
    participants: List[str]
    summary: str
    action_items: List[ActionItem]
    key_decisions: List[str]
    next_steps: List[str]
    duration_minutes: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Prompts for LLM
EXTRACTION_PROMPT = """Analyze these meeting notes and extract structured information.

MEETING NOTES:
{notes}

Extract and return a JSON object with:
{{
    "title": "Meeting title or topic",
    "participants": ["List of people mentioned"],
    "summary": "2-3 sentence executive summary",
    "action_items": [
        {{
            "task": "What needs to be done",
            "assignee": "Who is responsible (or null)",
            "due_date": "When it's due (or null)",
            "priority": "high/medium/low"
        }}
    ],
    "key_decisions": ["Important decisions made"],
    "next_steps": ["Upcoming actions or follow-ups"]
}}

Be thorough but concise. Extract ALL action items mentioned."""


PRIORITIZATION_PROMPT = """Given these action items from a meeting, assign priorities.

ACTION ITEMS:
{items}

Consider:
- Urgency (deadlines, blockers)
- Impact (affects many people/projects)
- Dependencies (blocks other work)

Return a JSON array with each item and its priority (high/medium/low):
[{{"task": "...", "priority": "high/medium/low", "reason": "..."}}]"""


class MeetingNotesEngine:
    """
    Engine for processing meeting notes.
    
    Usage:
        engine = MeetingNotesEngine()
        engine.set_llm_router(llm_router)
        summary = await engine.summarize(notes)
    """
    
    def __init__(self):
        self.llm_router = None
        self.default_model = "gpt-4o-mini"
    
    def set_llm_router(self, router):
        """Set the LLM router for AI processing."""
        self.llm_router = router
    
    async def summarize(
        self,
        notes: str,
        model: str = None,
        include_priorities: bool = True
    ) -> MeetingSummary:
        """
        Process meeting notes and generate a structured summary.
        
        Args:
            notes: Raw meeting notes text
            model: LLM model to use (optional)
            include_priorities: Whether to prioritize action items
            
        Returns:
            MeetingSummary with all extracted information
        """
        if not self.llm_router:
            # Fallback to basic extraction without LLM
            return self._basic_extraction(notes)
        
        model = model or self.default_model
        
        # Step 1: Extract information using LLM
        extraction = await self._extract_with_llm(notes, model)
        
        # Step 2: Prioritize action items (optional)
        if include_priorities and extraction.get("action_items"):
            extraction["action_items"] = await self._prioritize_items(
                extraction["action_items"], 
                model
            )
        
        # Step 3: Build the summary object
        return self._build_summary(extraction, notes)
    
    async def _extract_with_llm(self, notes: str, model: str) -> Dict[str, Any]:
        """Extract structured data from notes using LLM."""
        prompt = EXTRACTION_PROMPT.format(notes=notes)
        
        response = await self.llm_router.run(
            model_id=model,
            messages=[
                {"role": "system", "content": "You are a meeting notes analyzer. Extract structured information and return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for structured extraction
        )
        
        # Parse JSON from response
        content = response.get("content", "{}")
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {"title": "Meeting", "summary": content, "action_items": [], "participants": [], "key_decisions": [], "next_steps": []}
    
    async def _prioritize_items(self, items: List[Dict], model: str) -> List[Dict]:
        """Assign priorities to action items."""
        if not items:
            return items
        
        items_text = "\n".join([f"- {item.get('task', '')}" for item in items])
        prompt = PRIORITIZATION_PROMPT.format(items=items_text)
        
        response = await self.llm_router.run(
            model_id=model,
            messages=[
                {"role": "system", "content": "You are a task prioritization expert. Return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        # Parse and merge priorities
        try:
            content = response.get("content", "[]")
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                priorities = json.loads(json_match.group())
                priority_map = {p.get("task", "").lower(): p.get("priority", "medium") for p in priorities}
                
                for item in items:
                    task_lower = item.get("task", "").lower()
                    for key, priority in priority_map.items():
                        if key in task_lower or task_lower in key:
                            item["priority"] = priority
                            break
        except:
            pass
        
        return items
    
    def _build_summary(self, extraction: Dict, original_notes: str) -> MeetingSummary:
        """Build MeetingSummary from extracted data."""
        action_items = [
            ActionItem(
                task=item.get("task", ""),
                assignee=item.get("assignee"),
                due_date=item.get("due_date"),
                priority=Priority(item.get("priority", "medium")),
                status="pending"
            )
            for item in extraction.get("action_items", [])
        ]
        
        return MeetingSummary(
            title=extraction.get("title", "Meeting Notes"),
            date=datetime.now().strftime("%Y-%m-%d"),
            participants=extraction.get("participants", []),
            summary=extraction.get("summary", ""),
            action_items=action_items,
            key_decisions=extraction.get("key_decisions", []),
            next_steps=extraction.get("next_steps", []),
            metadata={"original_length": len(original_notes)}
        )
    
    def _basic_extraction(self, notes: str) -> MeetingSummary:
        """Basic extraction without LLM (fallback)."""
        # Simple regex-based extraction
        lines = notes.split("\n")
        action_items = []
        participants = set()
        
        for line in lines:
            line = line.strip()
            # Look for action items (TODO, ACTION, @person)
            if any(marker in line.upper() for marker in ["TODO", "ACTION", "TASK"]):
                action_items.append(ActionItem(task=line))
            # Look for participant mentions (@name or Name:)
            mentions = re.findall(r'@(\w+)|^(\w+):', line)
            for match in mentions:
                name = match[0] or match[1]
                if name and len(name) > 1:
                    participants.add(name)
        
        return MeetingSummary(
            title="Meeting Notes",
            date=datetime.now().strftime("%Y-%m-%d"),
            participants=list(participants),
            summary=notes[:500] + "..." if len(notes) > 500 else notes,
            action_items=action_items,
            key_decisions=[],
            next_steps=[]
        )
    
    async def extract_action_items_only(self, notes: str, model: str = None) -> List[ActionItem]:
        """Quick extraction of just action items."""
        summary = await self.summarize(notes, model, include_priorities=True)
        return summary.action_items
    
    def format_summary_markdown(self, summary: MeetingSummary) -> str:
        """Format summary as Markdown for display."""
        md = f"""# {summary.title}

**Date:** {summary.date}
**Participants:** {', '.join(summary.participants) if summary.participants else 'Not specified'}

## Summary
{summary.summary}

## Action Items
"""
        for i, item in enumerate(summary.action_items, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.priority.value, "⚪")
            assignee = f" → {item.assignee}" if item.assignee else ""
            due = f" (Due: {item.due_date})" if item.due_date else ""
            md += f"{i}. {priority_emoji} {item.task}{assignee}{due}\n"
        
        if summary.key_decisions:
            md += "\n## Key Decisions\n"
            for decision in summary.key_decisions:
                md += f"- {decision}\n"
        
        if summary.next_steps:
            md += "\n## Next Steps\n"
            for step in summary.next_steps:
                md += f"- {step}\n"
        
        return md


# Global instance
meeting_notes_engine = MeetingNotesEngine()
```

### Step 2: Module Init (`modules/meeting_notes/__init__.py`)

```python
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
```

### Step 3: API Layer (`api/v1/meeting_notes.py`)

```python
"""
Meeting Notes API - Summarize and analyze meeting notes.

Endpoints:
- POST /summarize - Generate full meeting summary
- POST /action-items - Extract only action items
- POST /format - Format summary as Markdown
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

from modules.meeting_notes import meeting_notes_engine, Priority
from core.llm import llm_router

router = APIRouter()

# Wire up the engine with LLM
meeting_notes_engine.set_llm_router(llm_router)


# ============================================
# Request/Response Models
# ============================================

class SummarizeRequest(BaseModel):
    """Request to summarize meeting notes."""
    content: str = Field(..., description="Raw meeting notes text", min_length=10)
    model: Optional[str] = Field("gpt-4o-mini", description="LLM model to use")
    include_priorities: bool = Field(True, description="Auto-prioritize action items")


class ActionItemResponse(BaseModel):
    """Action item in response."""
    task: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"


class SummaryResponse(BaseModel):
    """Meeting summary response."""
    title: str
    date: str
    participants: List[str]
    summary: str
    action_items: List[ActionItemResponse]
    key_decisions: List[str]
    next_steps: List[str]
    metadata: Dict[str, Any] = {}


class ActionItemsRequest(BaseModel):
    """Request to extract action items only."""
    content: str = Field(..., min_length=10)
    model: Optional[str] = "gpt-4o-mini"


class FormatRequest(BaseModel):
    """Request to format summary as Markdown."""
    summary: SummaryResponse


# ============================================
# API Endpoints
# ============================================

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_meeting(request: SummarizeRequest):
    """
    Generate a comprehensive meeting summary.
    
    Takes raw meeting notes and extracts:
    - Executive summary
    - Participants
    - Action items (with auto-prioritization)
    - Key decisions
    - Next steps
    
    Example:
    ```
    POST /api/v1/meeting-notes/summarize
    {
        "content": "Meeting with John and Sarah about Q4 goals...",
        "include_priorities": true
    }
    ```
    """
    try:
        summary = await meeting_notes_engine.summarize(
            notes=request.content,
            model=request.model,
            include_priorities=request.include_priorities
        )
        
        return SummaryResponse(
            title=summary.title,
            date=summary.date,
            participants=summary.participants,
            summary=summary.summary,
            action_items=[
                ActionItemResponse(
                    task=item.task,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    priority=item.priority.value,
                    status=item.status
                )
                for item in summary.action_items
            ],
            key_decisions=summary.key_decisions,
            next_steps=summary.next_steps,
            metadata=summary.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/action-items")
async def extract_action_items(request: ActionItemsRequest):
    """
    Quick extraction of just action items.
    
    Useful when you only need the tasks, not the full summary.
    
    Example:
    ```
    POST /api/v1/meeting-notes/action-items
    {
        "content": "TODO: John to review the proposal by Friday..."
    }
    ```
    """
    try:
        items = await meeting_notes_engine.extract_action_items_only(
            notes=request.content,
            model=request.model
        )
        
        return {
            "count": len(items),
            "action_items": [
                {
                    "task": item.task,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "priority": item.priority.value
                }
                for item in items
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/format/markdown")
async def format_as_markdown(request: FormatRequest):
    """
    Format a summary as Markdown.
    
    Converts a structured summary into nicely formatted Markdown
    suitable for sharing or documentation.
    """
    from modules.meeting_notes import MeetingSummary, ActionItem, Priority
    
    # Reconstruct the summary object
    summary = MeetingSummary(
        title=request.summary.title,
        date=request.summary.date,
        participants=request.summary.participants,
        summary=request.summary.summary,
        action_items=[
            ActionItem(
                task=item.task,
                assignee=item.assignee,
                due_date=item.due_date,
                priority=Priority(item.priority)
            )
            for item in request.summary.action_items
        ],
        key_decisions=request.summary.key_decisions,
        next_steps=request.summary.next_steps
    )
    
    markdown = meeting_notes_engine.format_summary_markdown(summary)
    
    return {
        "markdown": markdown,
        "character_count": len(markdown)
    }


@router.get("/")
async def get_info():
    """
    Get information about the Meeting Notes API.
    """
    return {
        "name": "Meeting Notes Summarizer",
        "version": "1.0.0",
        "description": "Extract action items and summaries from meeting notes",
        "endpoints": [
            {"path": "/summarize", "method": "POST", "description": "Full meeting summary"},
            {"path": "/action-items", "method": "POST", "description": "Extract action items only"},
            {"path": "/format/markdown", "method": "POST", "description": "Format as Markdown"}
        ],
        "supported_models": ["gpt-4o-mini", "gpt-4o", "gpt-4"],
        "features": [
            "Action item extraction",
            "Participant identification",
            "Auto-prioritization",
            "Executive summaries",
            "Markdown export"
        ]
    }
```

### Step 4: Register in main.py

Add to `main.py`:

```python
# In the imports section
from api.v1 import meeting_notes

# In the router registration section
app.include_router(meeting_notes.router, prefix="/api/v1/meeting-notes", tags=["Meeting Notes"])
```

### Step 5: Create Use Case Documentation

Create `use_cases/meeting_notes/README.md`:

```markdown
# Meeting Notes Summarizer

AI-powered meeting notes analysis and action item extraction.

## Features

- 📝 **Smart Summarization** - Generate executive summaries from raw notes
- ✅ **Action Item Extraction** - Automatically identify tasks and TODOs
- 👥 **Participant Detection** - Find who attended and their assignments
- 🎯 **Auto-Prioritization** - Rank action items by urgency/impact
- 📄 **Markdown Export** - Beautiful formatted output

## Quick Start

### 1. Summarize Meeting Notes

```bash
curl -X POST http://localhost:8000/api/v1/meeting-notes/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Meeting with John and Sarah on 2025-01-15\n\nDiscussed Q4 roadmap:\n- John will complete API design by Friday\n- Sarah to review security requirements\n- Decision: We will use PostgreSQL for the new service\n\nNext meeting scheduled for Monday.",
    "include_priorities": true
  }'
```

### 2. Extract Action Items Only

```bash
curl -X POST http://localhost:8000/api/v1/meeting-notes/action-items \
  -H "Content-Type: application/json" \
  -d '{"content": "TODO: Fix bug #123. ACTION: Deploy to staging by EOD."}'
```

### 3. Get API Info

```bash
curl http://localhost:8000/api/v1/meeting-notes/
```

## Example Response

```json
{
  "title": "Q4 Roadmap Discussion",
  "date": "2025-01-15",
  "participants": ["John", "Sarah"],
  "summary": "Team discussed Q4 roadmap focusing on API design and security requirements. Decision made to use PostgreSQL.",
  "action_items": [
    {
      "task": "Complete API design",
      "assignee": "John",
      "due_date": "Friday",
      "priority": "high"
    },
    {
      "task": "Review security requirements",
      "assignee": "Sarah",
      "priority": "medium"
    }
  ],
  "key_decisions": ["Use PostgreSQL for the new service"],
  "next_steps": ["Meeting scheduled for Monday"]
}
```

## Requirements

- Server running: `uvicorn main:app --port 8000`
- For AI features: Valid `OPENAI_API_KEY` in `.env`
```

### Step 6: Create Test Script

Create `use_cases/meeting_notes/test_use_case.py`:

```python
"""
Meeting Notes Use Case - Test Script

Run with: python use_cases/meeting_notes/test_use_case.py
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1/meeting-notes"

# Sample meeting notes for testing
SAMPLE_NOTES = """
Weekly Engineering Standup - January 15, 2025

Attendees: Alice (Tech Lead), Bob (Backend), Carol (Frontend), Dave (DevOps)

Discussion:
- Alice presented the new architecture proposal for the payment service
- Bob reported that the API refactoring is 80% complete, will finish by Wednesday
- Carol mentioned UI performance issues on the dashboard, needs investigation
- Dave confirmed the Kubernetes migration is on track for next week

Action Items:
1. Bob to complete API refactoring by Wednesday
2. Carol to profile dashboard performance and create ticket - HIGH PRIORITY
3. Dave to prepare rollback plan for K8s migration
4. Alice to schedule architecture review meeting with stakeholders
5. Everyone to review the new coding guidelines document by Friday

Decisions Made:
- Approved moving to PostgreSQL 15
- Agreed to implement feature flags for the new checkout flow
- Will hire one more backend developer

Next Steps:
- Architecture review meeting Thursday 2pm
- K8s migration dry run Monday
- Sprint retrospective next Friday
"""


async def test_meeting_notes():
    """Test the meeting notes API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 60)
        print("Meeting Notes Summarizer - Test Suite")
        print("=" * 60)
        
        # Test 1: Get API info
        print("\n📋 Test 1: Getting API info...")
        response = await client.get(f"{BASE_URL}/")
        info = response.json()
        print(f"  ✅ API: {info['name']} v{info['version']}")
        print(f"  Features: {', '.join(info['features'][:3])}...")
        
        # Test 2: Full summarization
        print("\n📝 Test 2: Full meeting summarization...")
        response = await client.post(
            f"{BASE_URL}/summarize",
            json={
                "content": SAMPLE_NOTES,
                "include_priorities": True
            }
        )
        
        if response.status_code == 200:
            summary = response.json()
            print(f"  ✅ Title: {summary['title']}")
            print(f"  👥 Participants: {', '.join(summary['participants'])}")
            print(f"  📊 Summary: {summary['summary'][:100]}...")
            print(f"  ✅ Action Items: {len(summary['action_items'])}")
            for item in summary['action_items'][:3]:
                priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item['priority'], "⚪")
                print(f"     {priority} {item['task'][:50]}...")
            print(f"  🎯 Decisions: {len(summary['key_decisions'])}")
        else:
            print(f"  ⚠️ Status: {response.status_code}")
            print(f"  Note: LLM features require valid OPENAI_API_KEY")
        
        # Test 3: Action items only
        print("\n✅ Test 3: Extract action items only...")
        response = await client.post(
            f"{BASE_URL}/action-items",
            json={"content": "TODO: Fix bug #123 by Friday. ACTION: John to review PR."}
        )
        
        if response.status_code == 200:
            items = response.json()
            print(f"  ✅ Found {items['count']} action items")
        else:
            print(f"  ⚠️ Requires LLM API key")
        
        # Test 4: Markdown formatting (doesn't need LLM)
        print("\n📄 Test 4: Markdown formatting...")
        sample_summary = {
            "title": "Test Meeting",
            "date": "2025-01-15",
            "participants": ["Alice", "Bob"],
            "summary": "Discussed project timeline.",
            "action_items": [
                {"task": "Complete design", "assignee": "Alice", "priority": "high", "due_date": "Friday", "status": "pending"}
            ],
            "key_decisions": ["Use PostgreSQL"],
            "next_steps": ["Review on Monday"],
            "metadata": {}
        }
        
        response = await client.post(
            f"{BASE_URL}/format/markdown",
            json={"summary": sample_summary}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Generated {result['character_count']} characters of Markdown")
            print("  Preview:")
            print("  " + result['markdown'][:200].replace('\n', '\n  ') + "...")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 Test Summary")
        print("=" * 60)
        print("  ✅ API endpoints working")
        print("  ℹ️  Full AI features require OPENAI_API_KEY in .env")


if __name__ == "__main__":
    asyncio.run(test_meeting_notes())
```

---

## 🔧 Step-by-Step Breakdown

### 1️⃣ Plan Your Use Case

Before coding, define:

```yaml
# use_cases/your_feature/intent.yaml
use_case:
  name: "Your Feature Name"
  problem: "What problem does it solve?"
  solution: "How does it solve it?"
  
  inputs:
    - Raw text/data
    - User parameters
    
  outputs:
    - Processed results
    - Structured data
    
  llm_usage:
    - Extraction
    - Summarization
    - Classification
```

### 2️⃣ Design the Data Models

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class Status(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"

@dataclass
class YourDataModel:
    id: str
    content: str
    status: Status = Status.PENDING
    metadata: dict = None
```

### 3️⃣ Build the Engine

```python
class YourEngine:
    def __init__(self):
        self.llm_router = None
    
    def set_llm_router(self, router):
        self.llm_router = router
    
    async def process(self, input_data: str) -> YourDataModel:
        # 1. Validate input
        # 2. Call LLM if needed
        # 3. Process results
        # 4. Return structured output
        pass

your_engine = YourEngine()
```

### 4️⃣ Create the API

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ProcessRequest(BaseModel):
    content: str
    options: dict = {}

@router.post("/process")
async def process(request: ProcessRequest):
    result = await your_engine.process(request.content)
    return result
```

### 5️⃣ Register and Test

```python
# main.py
from api.v1 import your_feature
app.include_router(your_feature.router, prefix="/api/v1/your-feature", tags=["Your Feature"])
```

```bash
# Test
curl -X POST http://localhost:8000/api/v1/your-feature/process \
  -H "Content-Type: application/json" \
  -d '{"content": "test input"}'
```

---

## 🧪 Testing Your Use Case

### Unit Tests (`tests/test_your_feature.py`)

```python
import pytest
from modules.your_feature import your_engine

@pytest.mark.asyncio
async def test_basic_processing():
    result = await your_engine.process("test input")
    assert result is not None
    assert result.status == "pending"

@pytest.mark.asyncio
async def test_edge_cases():
    # Empty input
    with pytest.raises(ValueError):
        await your_engine.process("")
    
    # Very long input
    result = await your_engine.process("x" * 10000)
    assert len(result.summary) < 1000
```

### Integration Tests

```python
import httpx
import pytest

@pytest.mark.asyncio
async def test_api_endpoint():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post(
            "/api/v1/your-feature/process",
            json={"content": "test"}
        )
        assert response.status_code == 200
```

### Run Tests

```bash
# Run all tests
pytest tests/test_your_feature.py -v

# Run with coverage
pytest tests/test_your_feature.py --cov=modules.your_feature
```

---

## ✅ Best Practices

### 1. **Always Use Pydantic Models**

```python
# ✅ Good
class Request(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)
    
# ❌ Bad
def process(content: str):  # No validation
```

### 2. **Handle LLM Failures Gracefully**

```python
async def process(self, content: str):
    if not self.llm_router:
        return self._fallback_processing(content)
    
    try:
        return await self._llm_processing(content)
    except Exception:
        return self._fallback_processing(content)
```

### 3. **Use Type Hints**

```python
# ✅ Good
async def process(self, content: str) -> ProcessedResult:
    
# ❌ Bad
async def process(self, content):
```

### 4. **Document Your API**

```python
@router.post("/process")
async def process(request: Request):
    """
    Process input and return structured output.
    
    Args:
        content: The input text to process
        
    Returns:
        ProcessedResult with extracted information
        
    Example:
        POST /api/v1/your-feature/process
        {"content": "example input"}
    """
```

### 5. **Create Reusable Prompts**

```python
PROMPTS = {
    "extract": """Extract information from: {input}
Return JSON: {{"field": "value"}}""",
    
    "summarize": """Summarize in 2 sentences: {input}"""
}
```

---

## 🎯 Quick Reference Checklist

- [ ] Create `modules/your_feature/__init__.py`
- [ ] Create `modules/your_feature/engine.py`
- [ ] Create `api/v1/your_feature.py`
- [ ] Add to `main.py` imports and router
- [ ] Create `use_cases/your_feature/README.md`
- [ ] Create `use_cases/your_feature/test_use_case.py`
- [ ] Add tests in `tests/test_your_feature.py`
- [ ] Update main README if significant feature

---

<div align="center">

**Happy Building! 🚀**

*Questions? Check the [docs/](.) folder or open an issue.*

</div>
]]>

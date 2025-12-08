"""
Meeting Notes Summarizer - Core Engine

PLATFORM INTEGRATION:
- LLM Router: AI-powered extraction and summarization
- RAG: Store and search meeting notes
- Memory: Persist action items per user
- Orchestrator: Multi-step workflows
- Sentiment: Analyze meeting tone

Features:
- Extract action items from meeting notes
- Identify participants and their assignments
- Generate executive summary
- Prioritize tasks
- Store in RAG for future search
- Track action items in user memory
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import re
import uuid


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
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class MeetingSummary:
    """Complete meeting summary."""
    id: str
    title: str
    date: str
    participants: List[str]
    summary: str
    action_items: List[ActionItem]
    key_decisions: List[str]
    next_steps: List[str]
    sentiment: Optional[Dict[str, Any]] = None
    duration_minutes: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "participants": self.participants,
            "summary": self.summary,
            "action_items": [
                {
                    "id": item.id,
                    "task": item.task,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "priority": item.priority.value,
                    "status": item.status
                }
                for item in self.action_items
            ],
            "key_decisions": self.key_decisions,
            "next_steps": self.next_steps,
            "sentiment": self.sentiment,
            "metadata": self.metadata
        }


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
    
    INTEGRATES WITH:
    - LLM Router: For AI extraction
    - RAG Engine: For storing/searching meetings
    - Memory Service: For tracking action items
    - Sentiment Engine: For meeting tone analysis
    - Orchestrator: For complex workflows
    
    Usage:
        engine = MeetingNotesEngine()
        engine.set_llm_router(llm_router)
        engine.set_rag_engine(rag_engine)
        engine.set_memory_service(memory_service)
        summary = await engine.summarize(notes, store_in_rag=True)
    """
    
    def __init__(self):
        # Core dependencies
        self.llm_router = None
        self.rag_engine = None
        self.memory_service = None
        self.sentiment_engine = None
        self.orchestrator = None
        
        # Configuration
        self.default_model = "gpt-4o-mini"
        
        # In-memory storage (fallback)
        self.meetings: Dict[str, MeetingSummary] = {}
    
    # ==================== Dependency Injection ====================
    
    def set_llm_router(self, router):
        """Set the LLM router for AI processing."""
        self.llm_router = router
    
    def set_rag_engine(self, engine):
        """Set RAG engine for document storage and search."""
        self.rag_engine = engine
    
    def set_memory_service(self, service):
        """Set memory service for action item persistence."""
        self.memory_service = service
    
    def set_sentiment_engine(self, engine):
        """Set sentiment engine for meeting tone analysis."""
        self.sentiment_engine = engine
    
    def set_orchestrator(self, orchestrator):
        """Set orchestrator for workflow execution."""
        self.orchestrator = orchestrator
    
    # ==================== Core Methods ====================
    
    async def summarize(
        self,
        notes: str,
        model: str = None,
        include_priorities: bool = True,
        analyze_sentiment: bool = False,
        store_in_rag: bool = False,
        save_action_items: bool = False,
        user_id: Optional[str] = None
    ) -> MeetingSummary:
        """
        Process meeting notes and generate a structured summary.
        
        Args:
            notes: Raw meeting notes text
            model: LLM model to use (optional)
            include_priorities: Whether to prioritize action items
            analyze_sentiment: Analyze meeting tone using Sentiment module
            store_in_rag: Store in RAG for future search
            save_action_items: Save to user's memory
            user_id: User ID for memory storage
            
        Returns:
            MeetingSummary with all extracted information
        """
        meeting_id = str(uuid.uuid4())[:12]
        
        if not self.llm_router:
            return self._basic_extraction(notes, meeting_id)
        
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
        summary = self._build_summary(extraction, notes, meeting_id)
        
        # Step 4: Analyze sentiment (INTEGRATION: Sentiment Module)
        if analyze_sentiment and self.sentiment_engine:
            try:
                sentiment_result = await self.sentiment_engine.analyze(notes)
                summary.sentiment = {
                    "overall": sentiment_result.get("sentiment", "neutral"),
                    "score": sentiment_result.get("score", 0),
                    "emotions": sentiment_result.get("emotions", [])
                }
            except Exception:
                summary.sentiment = {"overall": "unknown", "score": 0}
        
        # Step 5: Store in RAG (INTEGRATION: RAG Module)
        if store_in_rag and self.rag_engine:
            await self._store_in_rag(summary, notes)
        
        # Step 6: Save action items to memory (INTEGRATION: Memory Module)
        if save_action_items and self.memory_service and user_id:
            await self._save_action_items_to_memory(summary, user_id)
        
        # Store locally
        self.meetings[meeting_id] = summary
        
        return summary
    
    async def _store_in_rag(self, summary: MeetingSummary, original_notes: str):
        """Store meeting in RAG for future search."""
        if not self.rag_engine:
            return
        
        # Create searchable document
        document = f"""# {summary.title}

Date: {summary.date}
Participants: {', '.join(summary.participants)}

## Summary
{summary.summary}

## Action Items
{chr(10).join([f'- {item.task} ({item.assignee or "Unassigned"})' for item in summary.action_items])}

## Key Decisions
{chr(10).join([f'- {d}' for d in summary.key_decisions])}

## Original Notes
{original_notes}
"""
        
        await self.rag_engine.ingest(
            content=document,
            filename=f"meeting_{summary.id}.md",
            metadata={
                "type": "meeting_notes",
                "meeting_id": summary.id,
                "title": summary.title,
                "date": summary.date,
                "participants": summary.participants,
                "action_item_count": len(summary.action_items)
            }
        )
    
    async def _save_action_items_to_memory(self, summary: MeetingSummary, user_id: str):
        """Save action items to user's memory."""
        if not self.memory_service:
            return
        
        for item in summary.action_items:
            # Create memory entry for each action item
            memory_content = f"Action item from '{summary.title}': {item.task}"
            if item.due_date:
                memory_content += f" (Due: {item.due_date})"
            if item.assignee:
                memory_content += f" - Assigned to: {item.assignee}"
            
            await self.memory_service.create_memory(
                user_id=user_id,
                content=memory_content,
                memory_type="short_term",
                category="tasks",
                metadata={
                    "meeting_id": summary.id,
                    "meeting_title": summary.title,
                    "action_item_id": item.id,
                    "priority": item.priority.value,
                    "status": item.status
                }
            )
    
    async def search_meetings(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search past meetings using RAG.
        
        INTEGRATION: Uses RAG module for semantic search.
        """
        if not self.rag_engine:
            # Fallback to local search
            results = []
            query_lower = query.lower()
            for meeting in self.meetings.values():
                if query_lower in meeting.title.lower() or query_lower in meeting.summary.lower():
                    results.append(meeting.to_dict())
            return results[:top_k]
        
        # Use RAG for semantic search
        try:
            rag_result = await self.rag_engine.query(
                query=f"meeting notes: {query}",
                top_k=top_k
            )
            return rag_result.get("sources", [])
        except Exception:
            # Fallback to local search on error
            results = []
            query_lower = query.lower()
            for meeting in self.meetings.values():
                if query_lower in meeting.title.lower() or query_lower in meeting.summary.lower():
                    results.append(meeting.to_dict())
            return results[:top_k]
    
    async def get_user_action_items(
        self,
        user_id: str,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get action items from user's memory.
        
        INTEGRATION: Uses Memory module.
        """
        if not self.memory_service:
            return []
        
        memories = await self.memory_service.list_memories(
            user_id=user_id,
            category="tasks"
        )
        
        items = []
        for mem in memories:
            if status and mem.get("metadata", {}).get("status") != status:
                continue
            items.append({
                "id": mem.get("id"),
                "content": mem.get("content"),
                "meeting_id": mem.get("metadata", {}).get("meeting_id"),
                "meeting_title": mem.get("metadata", {}).get("meeting_title"),
                "priority": mem.get("metadata", {}).get("priority"),
                "status": mem.get("metadata", {}).get("status", "pending")
            })
        
        return items
    
    async def run_meeting_workflow(
        self,
        notes: str,
        workflow_name: str = "meeting_analysis"
    ) -> Dict[str, Any]:
        """
        Run a complete meeting analysis workflow.
        
        INTEGRATION: Uses Orchestrator module.
        
        Workflow steps:
        1. Extract summary
        2. Analyze sentiment
        3. Store in RAG
        4. Create action items
        5. Send notifications (if configured)
        """
        if not self.orchestrator:
            # Fallback to direct processing
            summary = await self.summarize(
                notes=notes,
                analyze_sentiment=True,
                store_in_rag=True
            )
            return {"result": summary.to_dict(), "workflow": "direct"}
        
        # Define workflow
        workflow = {
            "name": workflow_name,
            "steps": [
                {
                    "id": "extract",
                    "action": "meeting_notes.summarize",
                    "params": {"notes": notes}
                },
                {
                    "id": "sentiment",
                    "action": "sentiment.analyze",
                    "params": {"text": notes},
                    "depends_on": []
                },
                {
                    "id": "store",
                    "action": "rag.ingest",
                    "params": {"content": "${extract.output}"},
                    "depends_on": ["extract"]
                }
            ]
        }
        
        result = await self.orchestrator.execute(workflow)
        return result
    
    # ==================== LLM Methods ====================
    
    async def _extract_with_llm(self, notes: str, model: str) -> Dict[str, Any]:
        """Extract structured data from notes using LLM."""
        prompt = EXTRACTION_PROMPT.format(notes=notes)
        
        response = await self.llm_router.run(
            model_id=model,
            messages=[
                {"role": "system", "content": "You are a meeting notes analyzer. Extract structured information and return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.get("content", "{}")
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {
            "title": "Meeting",
            "summary": content,
            "action_items": [],
            "participants": [],
            "key_decisions": [],
            "next_steps": []
        }
    
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
        except (json.JSONDecodeError, TypeError):
            pass
        
        return items
    
    def _build_summary(self, extraction: Dict, original_notes: str, meeting_id: str) -> MeetingSummary:
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
            id=meeting_id,
            title=extraction.get("title", "Meeting Notes"),
            date=datetime.now().strftime("%Y-%m-%d"),
            participants=extraction.get("participants", []),
            summary=extraction.get("summary", ""),
            action_items=action_items,
            key_decisions=extraction.get("key_decisions", []),
            next_steps=extraction.get("next_steps", []),
            metadata={"original_length": len(original_notes)}
        )
    
    def _basic_extraction(self, notes: str, meeting_id: str) -> MeetingSummary:
        """Basic extraction without LLM (fallback)."""
        lines = notes.split("\n")
        action_items = []
        participants = set()
        
        for line in lines:
            line = line.strip()
            if any(marker in line.upper() for marker in ["TODO", "ACTION", "TASK"]):
                action_items.append(ActionItem(task=line))
            mentions = re.findall(r'@(\w+)|^(\w+):', line)
            for match in mentions:
                name = match[0] or match[1]
                if name and len(name) > 1:
                    participants.add(name)
        
        return MeetingSummary(
            id=meeting_id,
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
"""
        
        if summary.sentiment:
            sentiment_emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(
                summary.sentiment.get("overall", ""), "❓"
            )
            md += f"**Sentiment:** {sentiment_emoji} {summary.sentiment.get('overall', 'unknown')}\n"
        
        md += f"""
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
    
    # ==================== Query Methods ====================
    
    def get_meeting(self, meeting_id: str) -> Optional[MeetingSummary]:
        """Get a meeting by ID."""
        return self.meetings.get(meeting_id)
    
    def list_meetings(self, limit: int = 10) -> List[MeetingSummary]:
        """List recent meetings."""
        meetings = list(self.meetings.values())
        return sorted(meetings, key=lambda m: m.date, reverse=True)[:limit]


# Global instance
meeting_notes_engine = MeetingNotesEngine()

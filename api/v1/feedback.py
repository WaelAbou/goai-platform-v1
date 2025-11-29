"""
Feedback API - Collect user feedback on AI responses.

Features:
- Thumbs up/down rating
- Optional text comments
- Feedback analytics
- Export for training data
- SQLite persistence
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import secrets
import sqlite3
import json
import os

from core.auth import get_user_id_flexible


router = APIRouter()


# SQLite Database Setup
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/feedback.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the feedback database."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            conversation_id TEXT,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            comment TEXT,
            model TEXT,
            sources_count INTEGER,
            latency_ms REAL,
            tags TEXT,
            user_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_model ON feedback(model)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")
    conn.commit()
    conn.close()


# Initialize on module load
init_db()


class FeedbackType(str, Enum):
    POSITIVE = "positive"  # Thumbs up
    NEGATIVE = "negative"  # Thumbs down


class FeedbackCreate(BaseModel):
    """Create feedback for a message."""
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    query: str
    response: str
    feedback_type: FeedbackType
    comment: Optional[str] = None
    model: Optional[str] = None
    sources_count: Optional[int] = None
    latency_ms: Optional[float] = None
    tags: List[str] = []


class Feedback(BaseModel):
    """Stored feedback record."""
    id: str
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    query: str
    response: str
    feedback_type: FeedbackType
    comment: Optional[str] = None
    model: Optional[str] = None
    sources_count: Optional[int] = None
    latency_ms: Optional[float] = None
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None


class FeedbackUpdate(BaseModel):
    """Update feedback."""
    feedback_type: Optional[FeedbackType] = None
    comment: Optional[str] = None
    tags: Optional[List[str]] = None


def row_to_feedback(row: sqlite3.Row) -> Feedback:
    """Convert database row to Feedback model."""
    return Feedback(
        id=row["id"],
        message_id=row["message_id"],
        conversation_id=row["conversation_id"],
        query=row["query"],
        response=row["response"],
        feedback_type=FeedbackType(row["feedback_type"]),
        comment=row["comment"],
        model=row["model"],
        sources_count=row["sources_count"],
        latency_ms=row["latency_ms"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"])
    )


@router.post("")
async def create_feedback(feedback_data: FeedbackCreate, user_id: str = Depends(get_user_id_flexible)):
    """
    Submit feedback for an AI response.
    
    Example:
    ```
    POST /api/v1/feedback
    {
        "query": "What is Python?",
        "response": "Python is a programming language...",
        "feedback_type": "positive",
        "comment": "Very helpful explanation!",
        "model": "gpt-4o-mini"
    }
    ```
    """
    feedback_id = f"fb_{secrets.token_hex(8)}"
    created_at = datetime.now()
    
    conn = get_db()
    conn.execute("""
        INSERT INTO feedback (
            id, message_id, conversation_id, query, response,
            feedback_type, comment, model, sources_count, latency_ms,
            tags, user_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        feedback_id,
        feedback_data.message_id,
        feedback_data.conversation_id,
        feedback_data.query,
        feedback_data.response,
        feedback_data.feedback_type.value,
        feedback_data.comment,
        feedback_data.model,
        feedback_data.sources_count,
        feedback_data.latency_ms,
        json.dumps(feedback_data.tags),
        user_id,  # authenticated user_id
        created_at.isoformat()
    ))
    conn.commit()
    conn.close()
    
    return {
        "id": feedback_id,
        "feedback_type": feedback_data.feedback_type,
        "message": "Feedback submitted successfully",
        "created_at": created_at.isoformat()
    }


@router.get("")
async def list_feedback(
    feedback_type: Optional[FeedbackType] = None,
    model: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List all feedback with optional filters.
    """
    conn = get_db()
    
    # Build query with filters
    query = "SELECT * FROM feedback WHERE 1=1"
    params: List[Any] = []
    
    if feedback_type:
        query += " AND feedback_type = ?"
        params.append(feedback_type.value)
    
    if model:
        query += " AND model = ?"
        params.append(model)
    
    # Get total count
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]
    
    # Add ordering and pagination
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    results = [row_to_feedback(row) for row in rows]
    
    return {
        "feedback": [f.dict() for f in results],
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/stats")
async def feedback_stats():
    """
    Get feedback statistics.
    
    Returns counts and percentages for positive/negative feedback.
    """
    conn = get_db()
    
    # Get total counts
    total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    
    if total == 0:
        conn.close()
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "positive_rate": 0,
            "negative_rate": 0,
            "by_model": {},
            "recent_negative": []
        }
    
    positive = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE feedback_type = ?", 
        (FeedbackType.POSITIVE.value,)
    ).fetchone()[0]
    negative = total - positive
    
    # Stats by model
    model_stats = conn.execute("""
        SELECT 
            COALESCE(model, 'unknown') as model,
            feedback_type,
            COUNT(*) as count
        FROM feedback
        GROUP BY model, feedback_type
    """).fetchall()
    
    by_model: Dict[str, Dict[str, int]] = {}
    for row in model_stats:
        model = row["model"]
        if model not in by_model:
            by_model[model] = {"positive": 0, "negative": 0, "total": 0}
        by_model[model][row["feedback_type"]] = row["count"]
        by_model[model]["total"] += row["count"]
    
    # Recent negative feedback (for review)
    negative_rows = conn.execute("""
        SELECT id, query, response, comment, model, created_at
        FROM feedback
        WHERE feedback_type = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (FeedbackType.NEGATIVE.value,)).fetchall()
    
    conn.close()
    
    recent_negative = [
        {
            "id": row["id"],
            "query": row["query"][:100],
            "response": row["response"][:200],
            "comment": row["comment"],
            "model": row["model"],
            "created_at": row["created_at"]
        }
        for row in negative_rows
    ]
    
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "positive_rate": round(positive / total * 100, 1),
        "negative_rate": round(negative / total * 100, 1),
        "by_model": by_model,
        "recent_negative": recent_negative
    }


@router.get("/{feedback_id}")
async def get_feedback(feedback_id: str):
    """Get a specific feedback record."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM feedback WHERE id = ?", 
        (feedback_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return row_to_feedback(row).dict()


@router.put("/{feedback_id}")
async def update_feedback(feedback_id: str, update_data: FeedbackUpdate):
    """Update feedback (e.g., change rating or add comment)."""
    conn = get_db()
    
    # Check if exists
    row = conn.execute(
        "SELECT * FROM feedback WHERE id = ?", 
        (feedback_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Build update query
    updates = []
    params = []
    
    if update_data.feedback_type is not None:
        updates.append("feedback_type = ?")
        params.append(update_data.feedback_type.value)
    if update_data.comment is not None:
        updates.append("comment = ?")
        params.append(update_data.comment)
    if update_data.tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(update_data.tags))
    
    if updates:
        params.append(feedback_id)
        conn.execute(
            f"UPDATE feedback SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
    
    # Fetch updated record
    row = conn.execute(
        "SELECT * FROM feedback WHERE id = ?", 
        (feedback_id,)
    ).fetchone()
    conn.close()
    
    return {"message": "Feedback updated", "feedback": row_to_feedback(row).dict()}


@router.delete("/{feedback_id}")
async def delete_feedback(feedback_id: str):
    """Delete a feedback record."""
    conn = get_db()
    
    # Check if exists
    row = conn.execute(
        "SELECT id FROM feedback WHERE id = ?", 
        (feedback_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Feedback deleted"}


@router.get("/export/training")
async def export_for_training(
    feedback_type: Optional[FeedbackType] = None,
    export_format: str = "jsonl"
):
    """
    Export feedback data for model training/fine-tuning.
    
    Returns data in a format suitable for training:
    - JSONL format with query/response pairs
    - Optionally filter by positive-only feedback
    """
    conn = get_db()
    
    query = "SELECT * FROM feedback"
    params = []
    
    if feedback_type:
        query += " WHERE feedback_type = ?"
        params.append(feedback_type.value)
    
    query += " ORDER BY created_at DESC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    results = [row_to_feedback(row) for row in rows]
    
    if export_format == "jsonl":
        lines = []
        for f in results:
            entry = {
                "messages": [
                    {"role": "user", "content": f.query},
                    {"role": "assistant", "content": f.response}
                ],
                "feedback": f.feedback_type.value,
                "model": f.model
            }
            lines.append(entry)
        
        return {
            "format": "jsonl",
            "count": len(lines),
            "data": lines
        }
    
    return {"error": "Unsupported format"}


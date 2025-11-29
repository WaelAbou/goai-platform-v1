"""
User Memory API - Short, Medium, and Long-term memory management.

Memory Types:
- Short-term: Current session context, recent messages (auto-managed)
- Medium-term: Session preferences, temporary facts (expires after hours/days)
- Long-term: Persistent user facts, preferences, important information (permanent)

Features:
- Automatic memory extraction from conversations
- Manual memory creation/editing
- Memory search and retrieval
- Memory injection into chat context
- Memory decay/expiration
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import json
import os
import secrets

from core.auth import get_user_id_flexible


router = APIRouter()

# SQLite Database Setup
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/memory.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the memory database."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT 'default',
            memory_type TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            content TEXT NOT NULL,
            context TEXT,
            importance INTEGER DEFAULT 5,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON memories(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_importance ON memories(importance)")
    conn.commit()
    conn.close()


# Initialize on module load
init_db()


class MemoryType(str, Enum):
    SHORT = "short"    # Current session, auto-expires
    MEDIUM = "medium"  # Hours to days
    LONG = "long"      # Permanent


class MemoryCategory(str, Enum):
    PREFERENCE = "preference"      # User preferences
    FACT = "fact"                  # Facts about the user
    CONTEXT = "context"            # Contextual information
    INSTRUCTION = "instruction"    # How user wants to be addressed/helped
    HISTORY = "history"            # Past interactions summary
    SKILL = "skill"                # User's skills/knowledge
    GOAL = "goal"                  # User's goals/objectives
    GENERAL = "general"            # General memories


class MemoryCreate(BaseModel):
    """Create a new memory."""
    content: str = Field(..., description="The memory content")
    memory_type: MemoryType = MemoryType.LONG
    category: MemoryCategory = MemoryCategory.GENERAL
    context: Optional[str] = Field(None, description="Context where this memory was created")
    importance: int = Field(5, ge=1, le=10, description="Importance level 1-10")
    expires_in_hours: Optional[int] = Field(None, description="Hours until expiration (for short/medium)")
    metadata: Optional[Dict[str, Any]] = None


class MemoryUpdate(BaseModel):
    """Update a memory."""
    content: Optional[str] = None
    category: Optional[MemoryCategory] = None
    importance: Optional[int] = Field(None, ge=1, le=10)
    expires_in_hours: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class Memory(BaseModel):
    """Memory record."""
    id: str
    user_id: str
    memory_type: MemoryType
    category: MemoryCategory
    content: str
    context: Optional[str]
    importance: int
    access_count: int
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]


class MemoryExtractRequest(BaseModel):
    """Request to extract memories from text."""
    text: str
    conversation_context: Optional[str] = None
    auto_categorize: bool = True


def row_to_memory(row: sqlite3.Row) -> Memory:
    """Convert database row to Memory model."""
    return Memory(
        id=row["id"],
        user_id=row["user_id"],
        memory_type=MemoryType(row["memory_type"]),
        category=MemoryCategory(row["category"]),
        content=row["content"],
        context=row["context"],
        importance=row["importance"],
        access_count=row["access_count"],
        last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
        expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        metadata=json.loads(row["metadata"]) if row["metadata"] else None
    )


# ==========================================
# Memory CRUD Endpoints
# ==========================================

@router.post("")
async def create_memory(memory_data: MemoryCreate, user_id: str = Depends(get_user_id_flexible)):
    """
    Create a new memory.
    
    Example:
    ```
    POST /api/v1/memory
    {
        "content": "User prefers Python over JavaScript",
        "memory_type": "long",
        "category": "preference",
        "importance": 8
    }
    ```
    """
    memory_id = f"mem_{secrets.token_hex(8)}"
    now = datetime.now()
    
    # Calculate expiration based on memory type
    expires_at = None
    if memory_data.expires_in_hours:
        expires_at = now + timedelta(hours=memory_data.expires_in_hours)
    elif memory_data.memory_type == MemoryType.SHORT:
        expires_at = now + timedelta(hours=1)  # Short memories expire in 1 hour
    elif memory_data.memory_type == MemoryType.MEDIUM:
        expires_at = now + timedelta(days=7)   # Medium memories expire in 7 days
    # Long memories don't expire
    
    conn = get_db()
    conn.execute("""
        INSERT INTO memories (
            id, user_id, memory_type, category, content, context,
            importance, access_count, last_accessed, expires_at,
            created_at, updated_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        memory_id,
        user_id,
        memory_data.memory_type.value,
        memory_data.category.value,
        memory_data.content,
        memory_data.context,
        memory_data.importance,
        0,
        None,
        expires_at.isoformat() if expires_at else None,
        now.isoformat(),
        now.isoformat(),
        json.dumps(memory_data.metadata) if memory_data.metadata else None
    ))
    conn.commit()
    conn.close()
    
    return {
        "id": memory_id,
        "memory_type": memory_data.memory_type,
        "category": memory_data.category,
        "content": memory_data.content,
        "importance": memory_data.importance,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat()
    }


@router.get("")
async def list_memories(
    user_id: str = Depends(get_user_id_flexible),
    memory_type: Optional[MemoryType] = None,
    category: Optional[MemoryCategory] = None,
    min_importance: int = 1,
    include_expired: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """
    List memories with optional filters.
    """
    conn = get_db()
    
    query = "SELECT * FROM memories WHERE user_id = ?"
    params: List[Any] = [user_id]
    
    if memory_type:
        query += " AND memory_type = ?"
        params.append(memory_type.value)
    
    if category:
        query += " AND category = ?"
        params.append(category.value)
    
    query += " AND importance >= ?"
    params.append(min_importance)
    
    if not include_expired:
        query += " AND (expires_at IS NULL OR expires_at > ?)"
        params.append(datetime.now().isoformat())
    
    # Count total
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]
    
    # Add ordering and pagination
    query += " ORDER BY importance DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    memories = [row_to_memory(row) for row in rows]
    
    return {
        "memories": [m.dict() for m in memories],
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/summary")
async def memory_summary(user_id: str = Depends(get_user_id_flexible)):
    """
    Get a summary of user's memories by type and category.
    """
    conn = get_db()
    now = datetime.now().isoformat()
    
    # Count by type
    type_counts = {}
    for mem_type in MemoryType:
        count = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE user_id = ? AND memory_type = ? AND (expires_at IS NULL OR expires_at > ?)",
            (user_id, mem_type.value, now)
        ).fetchone()[0]
        type_counts[mem_type.value] = count
    
    # Count by category
    category_counts = {}
    for cat in MemoryCategory:
        count = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE user_id = ? AND category = ? AND (expires_at IS NULL OR expires_at > ?)",
            (user_id, cat.value, now)
        ).fetchone()[0]
        if count > 0:
            category_counts[cat.value] = count
    
    # Top memories by importance
    top_memories = conn.execute("""
        SELECT content, category, importance FROM memories 
        WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY importance DESC LIMIT 5
    """, (user_id, now)).fetchall()
    
    conn.close()
    
    return {
        "user_id": user_id,
        "by_type": type_counts,
        "by_category": category_counts,
        "total": sum(type_counts.values()),
        "top_memories": [
            {"content": m["content"][:100], "category": m["category"], "importance": m["importance"]}
            for m in top_memories
        ]
    }


@router.get("/context")
async def get_memory_context(
    user_id: str = Depends(get_user_id_flexible),
    max_tokens: int = 1000,
    include_types: Optional[str] = None
):
    """
    Get memories formatted as context for LLM.
    
    Returns memories formatted for injection into system prompts.
    """
    conn = get_db()
    now = datetime.now().isoformat()
    
    # Build query
    query = """
        SELECT * FROM memories 
        WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
    """
    params: List[Any] = [user_id, now]
    
    if include_types:
        types = include_types.split(",")
        placeholders = ",".join(["?" for _ in types])
        query += f" AND memory_type IN ({placeholders})"
        params.extend(types)
    
    query += " ORDER BY importance DESC, access_count DESC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    if not rows:
        return {
            "context": "",
            "memory_count": 0,
            "note": "No memories found for this user"
        }
    
    # Format memories by category
    memories_by_category: Dict[str, List[str]] = {}
    for row in rows:
        cat = row["category"]
        if cat not in memories_by_category:
            memories_by_category[cat] = []
        memories_by_category[cat].append(row["content"])
    
    # Build context string
    context_parts = ["## User Memory Context\n"]
    
    category_labels = {
        "preference": "🎯 User Preferences",
        "fact": "📋 User Facts",
        "instruction": "📝 Instructions",
        "skill": "💡 Skills & Knowledge",
        "goal": "🎯 Goals",
        "context": "📌 Context",
        "history": "📜 History",
        "general": "💭 General"
    }
    
    char_count = 0
    for cat, memories in memories_by_category.items():
        label = category_labels.get(cat, cat.title())
        section = f"\n### {label}\n"
        for mem in memories[:5]:  # Limit per category
            section += f"- {mem}\n"
        
        if char_count + len(section) > max_tokens * 4:  # Rough char estimate
            break
        context_parts.append(section)
        char_count += len(section)
    
    context = "".join(context_parts)
    
    return {
        "context": context,
        "memory_count": len(rows),
        "categories": list(memories_by_category.keys())
    }


@router.get("/{memory_id}")
async def get_memory(memory_id: str):
    """Get a specific memory."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM memories WHERE id = ?",
        (memory_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # Update access count
    conn.execute(
        "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
        (datetime.now().isoformat(), memory_id)
    )
    conn.commit()
    conn.close()
    
    return row_to_memory(row).dict()


@router.put("/{memory_id}")
async def update_memory(memory_id: str, update_data: MemoryUpdate):
    """Update a memory."""
    conn = get_db()
    
    # Check if exists
    row = conn.execute(
        "SELECT * FROM memories WHERE id = ?",
        (memory_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # Build update
    updates = ["updated_at = ?"]
    params = [datetime.now().isoformat()]
    
    if update_data.content is not None:
        updates.append("content = ?")
        params.append(update_data.content)
    
    if update_data.category is not None:
        updates.append("category = ?")
        params.append(update_data.category.value)
    
    if update_data.importance is not None:
        updates.append("importance = ?")
        params.append(update_data.importance)
    
    if update_data.expires_in_hours is not None:
        expires_at = datetime.now() + timedelta(hours=update_data.expires_in_hours)
        updates.append("expires_at = ?")
        params.append(expires_at.isoformat())
    
    params.append(memory_id)
    
    conn.execute(
        f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    
    # Fetch updated
    row = conn.execute(
        "SELECT * FROM memories WHERE id = ?",
        (memory_id,)
    ).fetchone()
    conn.close()
    
    return {"message": "Memory updated", "memory": row_to_memory(row).dict()}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory."""
    conn = get_db()
    
    row = conn.execute(
        "SELECT id FROM memories WHERE id = ?",
        (memory_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Memory not found")
    
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Memory deleted"}


@router.delete("")
async def clear_memories(
    user_id: str = Depends(get_user_id_flexible),
    memory_type: Optional[MemoryType] = None,
    category: Optional[MemoryCategory] = None
):
    """Clear memories with optional filters."""
    conn = get_db()
    
    query = "DELETE FROM memories WHERE user_id = ?"
    params: List[Any] = [user_id]
    
    if memory_type:
        query += " AND memory_type = ?"
        params.append(memory_type.value)
    
    if category:
        query += " AND category = ?"
        params.append(category.value)
    
    result = conn.execute(query, params)
    deleted = result.rowcount
    conn.commit()
    conn.close()
    
    return {"message": f"Deleted {deleted} memories"}


@router.post("/cleanup")
async def cleanup_expired(user_id: str = Depends(get_user_id_flexible)):
    """Remove expired memories."""
    conn = get_db()
    
    result = conn.execute(
        "DELETE FROM memories WHERE user_id = ? AND expires_at IS NOT NULL AND expires_at < ?",
        (user_id, datetime.now().isoformat())
    )
    deleted = result.rowcount
    conn.commit()
    conn.close()
    
    return {"message": f"Cleaned up {deleted} expired memories"}


# ==========================================
# Memory Extraction (AI-powered)
# ==========================================

@router.post("/extract")
async def extract_memories(request: MemoryExtractRequest, user_id: str = Depends(get_user_id_flexible)):
    """
    Extract memories from text using LLM.
    
    Analyzes conversation/text and extracts:
    - User preferences
    - Facts about the user
    - Instructions/preferences for interaction
    """
    from core.llm import llm_router
    
    extraction_prompt = f"""Analyze this text and extract any important information that should be remembered about the user.

Text to analyze:
{request.text}

{f"Conversation context: {request.conversation_context}" if request.conversation_context else ""}

Extract memories in the following JSON format:
{{
    "memories": [
        {{
            "content": "The specific memory to store",
            "category": "preference|fact|instruction|skill|goal|context|general",
            "importance": 1-10,
            "memory_type": "short|medium|long"
        }}
    ]
}}

Guidelines:
- preference: User preferences (likes/dislikes, preferred styles)
- fact: Facts about the user (name, job, location, etc.)
- instruction: How user wants to be addressed or helped
- skill: User's skills or knowledge areas
- goal: User's goals or objectives
- context: Temporary contextual information
- general: Other noteworthy information

Only extract genuinely useful information. If nothing notable, return empty memories array.
Return ONLY valid JSON, no other text."""

    try:
        response = await llm_router.run(
            model_id="gpt-4o-mini",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.3
        )
        
        content = response.get("content", "{}")
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"memories": []}
        
        # Create extracted memories
        created = []
        for mem in data.get("memories", []):
            if not mem.get("content"):
                continue
                
            memory_data = MemoryCreate(
                content=mem["content"],
                memory_type=MemoryType(mem.get("memory_type", "long")),
                category=MemoryCategory(mem.get("category", "general")),
                importance=mem.get("importance", 5),
                context=request.conversation_context
            )
            
            result = await create_memory(memory_data, user_id)
            created.append(result)
        
        return {
            "extracted": len(created),
            "memories": created
        }
        
    except Exception as e:
        return {
            "extracted": 0,
            "memories": [],
            "error": str(e)
        }


# ==========================================
# Seed Example Memories
# ==========================================

@router.post("/seed-examples")
async def seed_example_memories(user_id: str = Depends(get_user_id_flexible)):
    """Seed some example memories for demo purposes."""
    examples = [
        {
            "content": "User prefers concise, bullet-point responses over long paragraphs",
            "category": "preference",
            "memory_type": "long",
            "importance": 8
        },
        {
            "content": "User is a Python developer with 5 years of experience",
            "category": "fact",
            "memory_type": "long",
            "importance": 9
        },
        {
            "content": "User is working on a FastAPI project",
            "category": "context",
            "memory_type": "medium",
            "importance": 7
        },
        {
            "content": "Always include code examples when explaining technical concepts",
            "category": "instruction",
            "memory_type": "long",
            "importance": 8
        },
        {
            "content": "User is learning about machine learning and RAG systems",
            "category": "goal",
            "memory_type": "long",
            "importance": 7
        }
    ]
    
    created = []
    for ex in examples:
        memory_data = MemoryCreate(**ex)
        result = await create_memory(memory_data, user_id)
        created.append(result)
    
    return {
        "message": f"Created {len(created)} example memories",
        "memories": created
    }


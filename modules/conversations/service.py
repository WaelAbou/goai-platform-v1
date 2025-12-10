"""
Platform Conversation Service

A centralized service for managing conversations across ALL use cases.
Any agent or module can use this to persist chat history.

Supported Agent Types:
- esg_companion: ESG/Sustainability chatbot
- meeting_notes: Meeting notes assistant  
- research_agent: Research/analysis agent
- customer_support: Customer support agent
- code_reviewer: Code review assistant
- custom: Any custom agent

Usage:
    from modules.conversations import conversation_service
    
    # Create conversation for any agent type
    conv_id = conversation_service.create_conversation(
        user_id="user@example.com",
        agent_type="meeting_notes",
        context_data={"meeting_id": "mtg_123"}
    )
    
    # Save messages
    conversation_service.save_message(conv_id, "user", "Summarize the meeting")
    conversation_service.save_message(conv_id, "assistant", "Here's the summary...")
    
    # Get conversations by agent type
    convs = conversation_service.get_conversations(
        user_id="user@example.com",
        agent_type="meeting_notes"
    )
"""

import json
import sqlite3
import secrets
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


# Central conversation database
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/platform_conversations.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@dataclass
class Message:
    """A message in a conversation."""
    id: str
    conversation_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    tool_results: Optional[Dict] = None
    attachments: Optional[List[str]] = None
    created_at: Optional[datetime] = None


@dataclass
class Conversation:
    """A conversation with an agent."""
    id: str
    user_id: str
    agent_type: str
    title: str
    company_id: Optional[str] = None
    context_data: Optional[Dict] = None
    tags: Optional[List[str]] = None
    message_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationService:
    """
    Platform-level service for managing conversations across all use cases.
    """
    
    AGENT_TYPES = [
        "esg_companion",
        "meeting_notes", 
        "research_agent",
        "customer_support",
        "code_reviewer",
        "data_analyst",
        "sql_expert",
        "project_planner",
        "custom"
    ]
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                company_id TEXT,
                agent_type TEXT NOT NULL DEFAULT 'custom',
                title TEXT,
                context_data TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_results TEXT,
                attachments TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_agent ON conversations(agent_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_company ON conversations(company_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_created ON messages(created_at)")
        
        conn.commit()
        conn.close()
    
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== CONVERSATION MANAGEMENT ====================
    
    def create_conversation(
        self,
        user_id: str,
        agent_type: str = "custom",
        title: str = None,
        company_id: str = None,
        context_data: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> str:
        """
        Create a new conversation.
        
        Args:
            user_id: User identifier
            agent_type: Type of agent (esg_companion, meeting_notes, etc.)
            title: Conversation title (auto-generated from first message if None)
            company_id: Optional company identifier
            context_data: Use-case specific context (e.g., meeting_id, document_id)
            tags: Optional tags for filtering
            
        Returns:
            Conversation ID
        """
        conv_id = f"conv_{secrets.token_hex(8)}"
        now = datetime.now().isoformat()
        
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO conversations 
            (id, user_id, company_id, agent_type, title, context_data, tags, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            conv_id,
            user_id,
            company_id,
            agent_type,
            title or "New Conversation",
            json.dumps(context_data) if context_data else None,
            json.dumps(tags) if tags else None,
            now,
            now
        ))
        conn.commit()
        conn.close()
        
        return conv_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        ).fetchone()
        conn.close()
        
        if not row:
            return None
            
        return Conversation(
            id=row["id"],
            user_id=row["user_id"],
            agent_type=row["agent_type"],
            title=row["title"],
            company_id=row["company_id"],
            context_data=json.loads(row["context_data"]) if row["context_data"] else None,
            tags=json.loads(row["tags"]) if row["tags"] else None,
            message_count=row["message_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def get_conversations(
        self,
        user_id: str,
        agent_type: str = None,
        company_id: str = None,
        tags: List[str] = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get conversations with optional filters.
        
        Args:
            user_id: Filter by user
            agent_type: Filter by agent type
            company_id: Filter by company
            tags: Filter by tags (any match)
            include_archived: Include archived conversations
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of conversation dicts with last message preview
        """
        conn = self._get_conn()
        
        query = """
            SELECT c.*, 
                   (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c
            WHERE user_id = ?
        """
        params: List[Any] = [user_id]
        
        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)
        
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        
        if not include_archived:
            query += " AND is_archived = 0"
        
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "agent_type": row["agent_type"],
                "title": row["title"],
                "company_id": row["company_id"],
                "context_data": json.loads(row["context_data"]) if row["context_data"] else None,
                "tags": json.loads(row["tags"]) if row["tags"] else None,
                "message_count": row["message_count"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "last_message": (row["last_message"][:100] + "...") if row["last_message"] and len(row["last_message"]) > 100 else row["last_message"]
            }
            for row in rows
        ]
    
    def update_conversation(
        self,
        conversation_id: str,
        title: str = None,
        context_data: Dict = None,
        tags: List[str] = None
    ) -> bool:
        """Update conversation metadata."""
        conn = self._get_conn()
        
        updates = ["updated_at = ?"]
        params = [datetime.now().isoformat()]
        
        if title:
            updates.append("title = ?")
            params.append(title)
        if context_data is not None:
            updates.append("context_data = ?")
            params.append(json.dumps(context_data))
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        
        params.append(conversation_id)
        
        result = conn.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
        conn.close()
        
        return result.rowcount > 0
    
    def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation (soft delete)."""
        conn = self._get_conn()
        result = conn.execute(
            "UPDATE conversations SET is_archived = 1, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), conversation_id)
        )
        conn.commit()
        conn.close()
        return result.rowcount > 0
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Permanently delete a conversation and all its messages."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        result = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        deleted = result.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    # ==================== MESSAGE MANAGEMENT ====================
    
    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_results: Dict = None,
        attachments: List[str] = None,
        metadata: Dict = None
    ) -> str:
        """
        Save a message to a conversation.
        
        Args:
            conversation_id: The conversation to add to
            role: 'user', 'assistant', or 'system'
            content: Message content
            tool_results: Results from tool calls (optional)
            attachments: List of attachment IDs/URLs (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Message ID
        """
        msg_id = f"msg_{secrets.token_hex(8)}"
        now = datetime.now().isoformat()
        
        conn = self._get_conn()
        
        conn.execute("""
            INSERT INTO messages (id, conversation_id, role, content, tool_results, attachments, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            conversation_id,
            role,
            content,
            json.dumps(tool_results) if tool_results else None,
            json.dumps(attachments) if attachments else None,
            json.dumps(metadata) if metadata else None,
            now
        ))
        
        # Update conversation
        conn.execute("""
            UPDATE conversations 
            SET updated_at = ?, message_count = message_count + 1
            WHERE id = ?
        """, (now, conversation_id))
        
        # Auto-set title from first user message
        if role == "user":
            conn.execute("""
                UPDATE conversations 
                SET title = CASE WHEN message_count <= 2 THEN ? ELSE title END
                WHERE id = ?
            """, (content[:50] + "..." if len(content) > 50 else content, conversation_id))
        
        conn.commit()
        conn.close()
        
        return msg_id
    
    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        before_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get messages from a conversation."""
        conn = self._get_conn()
        
        query = "SELECT * FROM messages WHERE conversation_id = ?"
        params: List[Any] = [conversation_id]
        
        if before_id:
            query += " AND created_at < (SELECT created_at FROM messages WHERE id = ?)"
            params.append(before_id)
        
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "conversation_id": row["conversation_id"],
                "role": row["role"],
                "content": row["content"],
                "tool_results": json.loads(row["tool_results"]) if row["tool_results"] else None,
                "attachments": json.loads(row["attachments"]) if row["attachments"] else None,
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    
    # ==================== STATISTICS ====================
    
    def get_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get conversation statistics."""
        conn = self._get_conn()
        
        base_query = "FROM conversations WHERE is_archived = 0"
        params = []
        if user_id:
            base_query += " AND user_id = ?"
            params = [user_id]
        
        # Total conversations
        total = conn.execute(f"SELECT COUNT(*) {base_query}", params).fetchone()[0]
        
        # By agent type
        by_agent = {}
        rows = conn.execute(f"""
            SELECT agent_type, COUNT(*) as count, SUM(message_count) as messages
            {base_query}
            GROUP BY agent_type
        """, params).fetchall()
        for row in rows:
            by_agent[row["agent_type"]] = {
                "conversations": row["count"],
                "messages": row["messages"] or 0
            }
        
        # Total messages
        if user_id:
            total_messages = conn.execute("""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ?
            """, [user_id]).fetchone()[0]
        else:
            total_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        
        conn.close()
        
        return {
            "total_conversations": total,
            "total_messages": total_messages,
            "by_agent_type": by_agent
        }


# Singleton instance
conversation_service = ConversationService()


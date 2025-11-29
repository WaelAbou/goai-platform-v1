"""
Database Service Layer - CRUD operations for all models.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import hashlib
import json
import numpy as np

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import Session

from .models import (
    User, APIKey, Document, DocumentChunk, Conversation, Message,
    DatabaseSchema, SQLQuery, Workflow, WorkflowRun, AuditLog,
    UsageMetric, SystemConfig, DocumentStatus, ConversationStatus,
    MessageRole, UserRole
)


# ============================================
# DOCUMENT SERVICE
# ============================================

class DocumentService:
    """Service for document operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        filename: str,
        content: str,
        owner_id: Optional[UUID] = None,
        file_type: str = "txt",
        metadata: Optional[Dict] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Document:
        """Create a new document."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        doc = Document(
            owner_id=owner_id,
            filename=filename,
            content=content,
            content_hash=content_hash,
            file_type=file_type,
            file_size=len(content.encode()),
            extra_data=metadata or {},
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            status=DocumentStatus.PENDING
        )
        
        self.session.add(doc)
        self.session.flush()
        return doc
    
    def get(self, doc_id: UUID) -> Optional[Document]:
        """Get document by ID."""
        return self.session.get(Document, doc_id)
    
    def get_by_hash(self, content_hash: str) -> Optional[Document]:
        """Get document by content hash."""
        return self.session.execute(
            select(Document).where(Document.content_hash == content_hash)
        ).scalar_one_or_none()
    
    def list(
        self,
        owner_id: Optional[UUID] = None,
        status: Optional[DocumentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Document]:
        """List documents with filters."""
        query = select(Document)
        
        if owner_id:
            query = query.where(Document.owner_id == owner_id)
        if status:
            query = query.where(Document.status == status)
        
        query = query.order_by(Document.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return list(self.session.execute(query).scalars().all())
    
    def update_status(
        self,
        doc_id: UUID,
        status: DocumentStatus,
        error_message: Optional[str] = None,
        chunk_count: Optional[int] = None
    ) -> Optional[Document]:
        """Update document processing status."""
        doc = self.get(doc_id)
        if doc:
            doc.status = status
            doc.error_message = error_message
            if chunk_count is not None:
                doc.chunk_count = chunk_count
            if status == DocumentStatus.COMPLETED:
                doc.processed_at = datetime.utcnow()
            self.session.flush()
        return doc
    
    def delete(self, doc_id: UUID) -> bool:
        """Delete a document and its chunks."""
        doc = self.get(doc_id)
        if doc:
            self.session.delete(doc)
            return True
        return False
    
    def count(self, owner_id: Optional[UUID] = None) -> int:
        """Count documents."""
        query = select(func.count(Document.id))
        if owner_id:
            query = query.where(Document.owner_id == owner_id)
        return self.session.execute(query).scalar_one()


# ============================================
# CHUNK SERVICE
# ============================================

class ChunkService:
    """Service for document chunk operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_many(
        self,
        document_id: UUID,
        chunks: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Create multiple chunks for a document."""
        chunk_models = []
        
        for chunk_data in chunks:
            chunk = DocumentChunk(
                document_id=document_id,
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                start_char=chunk_data.get("start_char"),
                end_char=chunk_data.get("end_char"),
                metadata=chunk_data.get("metadata", {})
            )
            
            # Store embedding if provided
            if "embedding" in chunk_data and chunk_data["embedding"]:
                embedding = np.array(chunk_data["embedding"], dtype=np.float32)
                chunk.embedding = embedding.tobytes()
                chunk.embedding_dimension = len(chunk_data["embedding"])
                chunk.embedding_model = chunk_data.get("embedding_model", "unknown")
            
            chunk_models.append(chunk)
        
        self.session.add_all(chunk_models)
        self.session.flush()
        return chunk_models
    
    def get_by_document(self, document_id: UUID) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        return list(self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).scalars().all())
    
    def get_with_embeddings(self, chunk_ids: List[UUID]) -> List[DocumentChunk]:
        """Get chunks with their embeddings."""
        return list(self.session.execute(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        ).scalars().all())
    
    def count(self, document_id: Optional[UUID] = None) -> int:
        """Count chunks."""
        query = select(func.count(DocumentChunk.id))
        if document_id:
            query = query.where(DocumentChunk.document_id == document_id)
        return self.session.execute(query).scalar_one()
    
    def search_all(self, limit: int = 1000) -> List[DocumentChunk]:
        """Get all chunks (for loading into memory)."""
        return list(self.session.execute(
            select(DocumentChunk).limit(limit)
        ).scalars().all())


# ============================================
# CONVERSATION SERVICE
# ============================================

class ConversationService:
    """Service for conversation operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        user_id: Optional[UUID] = None,
        title: Optional[str] = None,
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(
            user_id=user_id,
            title=title,
            model=model,
            system_prompt=system_prompt
        )
        self.session.add(conv)
        self.session.flush()
        return conv
    
    def get(self, conv_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.session.get(Conversation, conv_id)
    
    def list(
        self,
        user_id: Optional[UUID] = None,
        status: ConversationStatus = ConversationStatus.ACTIVE,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """List conversations."""
        query = select(Conversation).where(Conversation.status == status)
        
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        
        query = query.order_by(Conversation.updated_at.desc())
        query = query.limit(limit).offset(offset)
        
        return list(self.session.execute(query).scalars().all())
    
    def add_message(
        self,
        conv_id: UUID,
        role: MessageRole,
        content: str,
        model: Optional[str] = None,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        latency_ms: float = 0,
        sources: Optional[List] = None
    ) -> Message:
        """Add a message to conversation."""
        msg = Message(
            conversation_id=conv_id,
            role=role,
            content=content,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            latency_ms=latency_ms,
            sources=sources or []
        )
        self.session.add(msg)
        
        # Update conversation stats
        conv = self.get(conv_id)
        if conv:
            conv.message_count = (conv.message_count or 0) + 1
            conv.total_tokens = (conv.total_tokens or 0) + tokens_prompt + tokens_completion
            conv.last_message_at = datetime.utcnow()
        
        self.session.flush()
        return msg
    
    def get_messages(self, conv_id: UUID, limit: int = 100) -> List[Message]:
        """Get messages in a conversation."""
        return list(self.session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
            .limit(limit)
        ).scalars().all())
    
    def archive(self, conv_id: UUID) -> bool:
        """Archive a conversation."""
        conv = self.get(conv_id)
        if conv:
            conv.status = ConversationStatus.ARCHIVED
            return True
        return False
    
    def delete(self, conv_id: UUID) -> bool:
        """Delete a conversation."""
        conv = self.get(conv_id)
        if conv:
            self.session.delete(conv)
            return True
        return False


# ============================================
# SCHEMA SERVICE (SQL Agent)
# ============================================

class SchemaService:
    """Service for database schema operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        name: str,
        db_type: str,
        schema_json: Dict,
        description: Optional[str] = None
    ) -> DatabaseSchema:
        """Register a database schema."""
        schema = DatabaseSchema(
            name=name,
            db_type=db_type,
            schema_json=schema_json,
            description=description
        )
        self.session.add(schema)
        self.session.flush()
        return schema
    
    def get(self, name: str) -> Optional[DatabaseSchema]:
        """Get schema by name."""
        return self.session.execute(
            select(DatabaseSchema).where(DatabaseSchema.name == name)
        ).scalar_one_or_none()
    
    def list(self) -> List[DatabaseSchema]:
        """List all schemas."""
        return list(self.session.execute(
            select(DatabaseSchema).where(DatabaseSchema.is_active == True)
        ).scalars().all())
    
    def log_query(
        self,
        schema_name: str,
        question: str,
        generated_sql: str,
        explanation: str,
        tables_used: List[str],
        model: str
    ) -> SQLQuery:
        """Log a generated SQL query."""
        schema = self.get(schema_name)
        query = SQLQuery(
            schema_id=schema.id if schema else None,
            question=question,
            generated_sql=generated_sql,
            explanation=explanation,
            tables_used=tables_used,
            model=model
        )
        self.session.add(query)
        self.session.flush()
        return query


# ============================================
# AUDIT SERVICE
# ============================================

class AuditService:
    """Service for audit logging."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def log(
        self,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            request_method=request_method,
            request_path=request_path,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        self.session.add(log)
        self.session.flush()
        return log
    
    def get_recent(self, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs."""
        return list(self.session.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).scalars().all())


# ============================================
# USAGE METRICS SERVICE
# ============================================

class UsageService:
    """Service for usage metrics."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def record(
        self,
        metric_type: str,
        metric_value: float,
        unit: str,
        user_id: Optional[UUID] = None,
        model: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> UsageMetric:
        """Record a usage metric."""
        now = datetime.utcnow()
        metric = UsageMetric(
            user_id=user_id,
            metric_type=metric_type,
            metric_value=metric_value,
            unit=unit,
            model=model,
            endpoint=endpoint,
            period_start=now,
            period_end=now
        )
        self.session.add(metric)
        self.session.flush()
        return metric
    
    def get_summary(
        self,
        user_id: Optional[UUID] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Get usage summary."""
        query = select(
            UsageMetric.metric_type,
            func.sum(UsageMetric.metric_value).label("total")
        ).group_by(UsageMetric.metric_type)
        
        if user_id:
            query = query.where(UsageMetric.user_id == user_id)
        if since:
            query = query.where(UsageMetric.created_at >= since)
        
        results = self.session.execute(query).all()
        return {row.metric_type: row.total for row in results}


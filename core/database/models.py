"""
Database Models - SQLAlchemy ORM models for GoAI Platform.
Supports PostgreSQL with pgvector extension for embeddings.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, 
    ForeignKey, JSON, Index, Enum as SQLEnum, LargeBinary
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

Base = declarative_base()


# Enums
class DocumentStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# ============================================
# USER & AUTH MODELS
# ============================================

class User(Base):
    """User account for authentication and authorization."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Settings
    settings = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    documents = relationship("Document", back_populates="owner")
    conversations = relationship("Conversation", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"


class APIKey(Base):
    """API keys for programmatic access."""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    
    # Permissions
    scopes = Column(JSON, default=["read", "write"])
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey {self.key_prefix}...>"


# ============================================
# DOCUMENT & KNOWLEDGE BASE MODELS
# ============================================

class Document(Base):
    """Source document metadata and content."""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Document info
    filename = Column(String(500), nullable=False, index=True)
    title = Column(String(500))
    description = Column(Text)
    file_type = Column(String(50))  # txt, md, pdf, etc.
    file_size = Column(Integer)  # bytes
    
    # Content
    content = Column(Text)  # Raw content
    content_hash = Column(String(64), index=True)  # SHA256 for deduplication
    
    # Processing
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(Text)
    chunk_count = Column(Integer, default=0)
    
    # Chunking config used
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    
    # Extra metadata
    extra_data = Column(JSON, default={})
    tags = Column(JSON, default=[])  # ARRAY not supported in SQLite
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_documents_owner_created", "owner_id", "created_at"),
        Index("idx_documents_status", "status"),
    )
    
    def __repr__(self):
        return f"<Document {self.filename}>"


class DocumentChunk(Base):
    """Document chunks with embeddings for vector search."""
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    
    # Chunk content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    start_char = Column(Integer)  # Character offset in original
    end_char = Column(Integer)
    
    # Embedding (stored as binary for efficiency, or use pgvector)
    embedding = Column(LargeBinary)  # Serialized numpy array
    embedding_model = Column(String(100))  # e.g., "text-embedding-3-small"
    embedding_dimension = Column(Integer)
    
    # Extra metadata
    extra_data = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index("idx_chunks_document", "document_id", "chunk_index"),
    )
    
    def __repr__(self):
        return f"<DocumentChunk {self.document_id}:{self.chunk_index}>"


# ============================================
# CONVERSATION & CHAT MODELS
# ============================================

class Conversation(Base):
    """Chat conversation container."""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Conversation info
    title = Column(String(500))
    description = Column(Text)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    
    # Settings
    model = Column(String(100), default="gpt-4o-mini")
    system_prompt = Column(Text)
    temperature = Column(Float, default=0.7)
    top_k = Column(Integer, default=5)
    
    # Stats
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Extra metadata
    extra_data = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    
    def __repr__(self):
        return f"<Conversation {self.id}>"


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    
    # Message content
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # For assistant messages
    model = Column(String(100))
    tokens_prompt = Column(Integer)
    tokens_completion = Column(Integer)
    latency_ms = Column(Float)
    
    # Sources (for RAG responses)
    sources = Column(JSON, default=[])  # List of chunk IDs and scores
    
    # Extra metadata
    extra_data = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.role.value}: {self.content[:50]}...>"


# ============================================
# SQL AGENT MODELS
# ============================================

class DatabaseSchema(Base):
    """Registered database schemas for SQL Agent."""
    __tablename__ = "database_schemas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Database info
    name = Column(String(100), unique=True, nullable=False, index=True)
    db_type = Column(String(50), nullable=False)  # postgresql, mysql, sqlite
    description = Column(Text)
    
    # Connection (encrypted in production)
    connection_string = Column(String(500))  # Optional for actual execution
    
    # Schema definition
    schema_json = Column(JSON, nullable=False)  # Tables, columns, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    queries = relationship("SQLQuery", back_populates="schema")
    
    def __repr__(self):
        return f"<DatabaseSchema {self.name}>"


class SQLQuery(Base):
    """Generated SQL queries history."""
    __tablename__ = "sql_queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schema_id = Column(UUID(as_uuid=True), ForeignKey("database_schemas.id"), nullable=True)
    
    # Query
    question = Column(Text, nullable=False)
    generated_sql = Column(Text)
    explanation = Column(Text)
    
    # Execution
    executed = Column(Boolean, default=False)
    execution_time_ms = Column(Float)
    row_count = Column(Integer)
    error = Column(Text)
    
    # Metadata
    tables_used = Column(JSON, default=[])  # ARRAY not supported in SQLite
    model = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    schema = relationship("DatabaseSchema", back_populates="queries")
    
    def __repr__(self):
        return f"<SQLQuery {self.question[:50]}...>"


# ============================================
# WORKFLOW MODELS
# ============================================

class Workflow(Base):
    """Workflow definitions."""
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Workflow info
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text)
    version = Column(String(20), default="1.0")
    
    # Definition
    definition_yaml = Column(Text)  # YAML source
    definition_json = Column(JSON)  # Parsed structure
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Stats
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    avg_duration_ms = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workflow {self.name}>"


class WorkflowRun(Base):
    """Workflow execution history."""
    __tablename__ = "workflow_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    
    # Execution
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    input_payload = Column(JSON, default={})
    output_result = Column(JSON)
    error = Column(Text)
    
    # Progress
    steps_total = Column(Integer, default=0)
    steps_completed = Column(Integer, default=0)
    current_step = Column(String(200))
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="runs")
    
    def __repr__(self):
        return f"<WorkflowRun {self.workflow_id}:{self.status}>"


# ============================================
# AUDIT & LOGGING MODELS
# ============================================

class AuditLog(Base):
    """Audit trail for all actions."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Who
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # What
    action = Column(String(100), nullable=False, index=True)  # e.g., "document.create"
    resource_type = Column(String(100))  # e.g., "document"
    resource_id = Column(String(100))
    
    # Details
    request_method = Column(String(10))
    request_path = Column(String(500))
    request_body = Column(JSON)
    response_status = Column(Integer)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timing
    duration_ms = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.action}>"


class UsageMetric(Base):
    """Usage metrics for billing and analytics."""
    __tablename__ = "usage_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Metric
    metric_type = Column(String(100), nullable=False, index=True)  # e.g., "llm_tokens"
    metric_value = Column(Float, nullable=False)
    unit = Column(String(50))  # e.g., "tokens", "requests", "bytes"
    
    # Context
    model = Column(String(100))
    endpoint = Column(String(200))
    extra_data = Column(JSON, default={})
    
    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UsageMetric {self.metric_type}: {self.metric_value}>"


# ============================================
# SETTINGS & CONFIG MODELS
# ============================================

class SystemConfig(Base):
    """System-wide configuration settings."""
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    
    # Type hint for UI
    value_type = Column(String(50), default="string")  # string, number, boolean, json
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemConfig {self.key}>"


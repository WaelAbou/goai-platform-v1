"""
RAG Persistent Storage - Database-backed storage for documents and conversations.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import numpy as np
import pickle

from core.database import (
    db, DocumentService, ChunkService, ConversationService,
    Document, DocumentChunk, Conversation, Message,
    DocumentStatus, MessageRole
)
from core.database.config import Database


class PersistentDocumentStore:
    """
    Persistent document storage using SQLAlchemy.
    Stores documents and chunks in the database.
    """
    
    def __init__(self, database: Optional[Database] = None):
        self.db = database or db
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure database tables exist."""
        try:
            self.db.create_tables()
        except Exception as e:
            print(f"Warning: Could not create tables: {e}")
    
    def add_document(
        self,
        content: str,
        filename: str,
        chunks: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a document with its chunks to the database.
        
        Returns:
            Document ID
        """
        with self.db.session() as session:
            doc_service = DocumentService(session)
            chunk_service = ChunkService(session)
            
            # Create document
            doc = doc_service.create(
                filename=filename,
                content=content,
                metadata=metadata or {}
            )
            
            # Prepare chunk data with embeddings
            chunk_data = []
            for i, chunk in enumerate(chunks):
                data = {
                    "content": chunk.get("content", chunk) if isinstance(chunk, dict) else chunk,
                    "chunk_index": i,
                    "start_char": chunk.get("start_char", 0) if isinstance(chunk, dict) else 0,
                    "end_char": chunk.get("end_char", 0) if isinstance(chunk, dict) else 0,
                    "metadata": chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
                }
                
                if embeddings and i < len(embeddings):
                    data["embedding"] = embeddings[i]
                    data["embedding_model"] = metadata.get("embedding_model", "unknown") if metadata else "unknown"
                
                chunk_data.append(data)
            
            # Create chunks
            chunk_service.create_many(doc.id, chunk_data)
            
            # Update document status
            doc_service.update_status(
                doc.id,
                DocumentStatus.COMPLETED,
                chunk_count=len(chunks)
            )
            
            return str(doc.id)
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        with self.db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.get(UUID(doc_id))
            
            if doc:
                return {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "content": doc.content,
                    "status": doc.status.value,
                    "chunk_count": doc.chunk_count,
                    "metadata": doc.extra_data,
                    "created_at": doc.created_at.isoformat()
                }
            return None
    
    def list_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all documents."""
        with self.db.session() as session:
            doc_service = DocumentService(session)
            docs = doc_service.list(limit=limit)
            
            return [
                {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "status": doc.status.value,
                    "chunk_count": doc.chunk_count,
                    "file_size": doc.file_size,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in docs
            ]
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its chunks."""
        with self.db.session() as session:
            doc_service = DocumentService(session)
            return doc_service.delete(UUID(doc_id))
    
    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Get all chunks for loading into vector store."""
        with self.db.session() as session:
            chunk_service = ChunkService(session)
            chunks = chunk_service.search_all(limit=10000)
            
            result = []
            for chunk in chunks:
                embedding = None
                if chunk.embedding:
                    # Deserialize numpy array
                    embedding = np.frombuffer(chunk.embedding, dtype=np.float32).tolist()
                
                result.append({
                    "id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "embedding": embedding,
                    "metadata": chunk.extra_data or {}
                })
            
            return result
    
    def count_documents(self) -> int:
        """Count total documents."""
        with self.db.session() as session:
            doc_service = DocumentService(session)
            return doc_service.count()
    
    def count_chunks(self) -> int:
        """Count total chunks."""
        with self.db.session() as session:
            chunk_service = ChunkService(session)
            return chunk_service.count()


class PersistentConversationStore:
    """
    Persistent conversation storage using SQLAlchemy.
    """
    
    def __init__(self, database: Optional[Database] = None):
        self.db = database or db
    
    def create_conversation(
        self,
        title: Optional[str] = None,
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None
    ) -> str:
        """Create a new conversation."""
        with self.db.session() as session:
            conv_service = ConversationService(session)
            conv = conv_service.create(
                title=title,
                model=model,
                system_prompt=system_prompt
            )
            return str(conv.id)
    
    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID."""
        with self.db.session() as session:
            conv_service = ConversationService(session)
            conv = conv_service.get(UUID(conv_id))
            
            if conv:
                messages = conv_service.get_messages(conv.id)
                return {
                    "id": str(conv.id),
                    "title": conv.title,
                    "model": conv.model,
                    "status": conv.status.value,
                    "message_count": conv.message_count,
                    "messages": [
                        {
                            "role": msg.role.value,
                            "content": msg.content,
                            "sources": msg.sources,
                            "created_at": msg.created_at.isoformat()
                        }
                        for msg in messages
                    ],
                    "created_at": conv.created_at.isoformat()
                }
            return None
    
    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        sources: Optional[List] = None,
        model: Optional[str] = None,
        tokens: int = 0,
        latency_ms: float = 0
    ) -> str:
        """Add a message to a conversation."""
        with self.db.session() as session:
            conv_service = ConversationService(session)
            msg_role = MessageRole.USER if role == "user" else MessageRole.ASSISTANT
            
            msg = conv_service.add_message(
                conv_id=UUID(conv_id),
                role=msg_role,
                content=content,
                model=model,
                tokens_completion=tokens,
                latency_ms=latency_ms,
                sources=sources
            )
            return str(msg.id)
    
    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all conversations."""
        with self.db.session() as session:
            conv_service = ConversationService(session)
            convs = conv_service.list(limit=limit)
            
            return [
                {
                    "id": str(conv.id),
                    "title": conv.title,
                    "status": conv.status.value,
                    "message_count": conv.message_count,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
                }
                for conv in convs
            ]
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation."""
        with self.db.session() as session:
            conv_service = ConversationService(session)
            return conv_service.delete(UUID(conv_id))


# Singleton instances
document_store = PersistentDocumentStore()
conversation_store = PersistentConversationStore()


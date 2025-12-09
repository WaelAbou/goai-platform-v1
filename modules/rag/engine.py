"""
RAG Engine - Retrieval-Augmented Generation Pipeline.
Combines document ingestion, vector search, and LLM generation.
"""

import hashlib
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RAGMode(Enum):
    SIMPLE = "simple"           # Basic retrieval + generation
    CONVERSATIONAL = "conv"     # With chat history
    MULTI_QUERY = "multi"       # Query expansion
    STEP_BACK = "step_back"     # Step-back prompting
    HYDE = "hyde"               # Hypothetical document embeddings


@dataclass
class Source:
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class RAGResponse:
    answer: str
    sources: List[Source]
    query: str
    model: str
    mode: RAGMode
    tokens_used: int = 0
    latency_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: List[Source] = field(default_factory=list)


@dataclass
class Conversation:
    id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class RAGEngine:
    """
    Complete RAG pipeline with multiple retrieval strategies.
    """

    # System prompts for different modes
    SYSTEM_PROMPTS = {
        "default": """You are a helpful AI assistant. Answer the user's question based on the provided context.
If the context doesn't contain relevant information, say so honestly.
Always cite your sources by referencing the source numbers [1], [2], etc.
Be concise but thorough.""",
        
        "conversational": """You are a helpful AI assistant engaged in a conversation.
Use the provided context and conversation history to answer questions.
Maintain continuity with previous messages.
Cite sources using [1], [2], etc. when referencing the context.""",
        
        "technical": """You are a technical expert assistant.
Provide detailed, accurate answers based on the provided documentation.
Include code examples when relevant.
Always cite your sources [1], [2], etc.""",
        
        "summary": """You are a summarization assistant.
Synthesize the provided context into a clear, comprehensive answer.
Organize information logically.
Cite all sources used [1], [2], etc."""
    }

    QUERY_EXPANSION_PROMPT = """Given the user's question, generate 3 alternative search queries that might help find relevant information.
Return only the queries, one per line.

Question: {query}

Alternative queries:"""

    HYDE_PROMPT = """Given the question, write a hypothetical passage that would perfectly answer it.
This passage will be used to find similar real documents.

Question: {query}

Hypothetical answer passage:"""

    STEP_BACK_PROMPT = """Given the specific question, generate a more general "step-back" question that would provide broader context.

Specific question: {query}

Step-back question:"""

    def __init__(self, use_persistent_storage: bool = True):
        self.llm_router = None
        self.vector_retriever = None
        self.ingestion_engine = None
        self.conversations: Dict[str, Conversation] = {}
        self.default_model = "gpt-4o-mini"
        self.default_top_k = 5
        self.default_mode = RAGMode.SIMPLE
        
        # Persistent storage
        self.use_persistent_storage = use_persistent_storage
        self.document_store = None
        self.conversation_store = None
        
        if use_persistent_storage:
            self._init_persistent_storage()
    
    def _init_persistent_storage(self):
        """Initialize persistent storage."""
        try:
            from .storage import document_store, conversation_store
            self.document_store = document_store
            self.conversation_store = conversation_store
            print("✅ Persistent storage initialized (SQLite)")
        except Exception as e:
            print(f"⚠️ Could not initialize persistent storage: {e}")
            self.use_persistent_storage = False
    
    def load_from_database(self):
        """Load documents from database into vector store."""
        if not self.document_store or not self.vector_retriever:
            return {"loaded": 0, "error": "Storage not configured"}
        
        try:
            chunks = self.document_store.get_all_chunks()
            loaded = 0
            
            for chunk in chunks:
                # Add to vector retriever's in-memory store
                if chunk["content"] and chunk["id"]:
                    self.vector_retriever.documents[chunk["id"]] = type('Document', (), {
                        'id': chunk["id"],
                        'content': chunk["content"],
                        'metadata': chunk.get("metadata", {}),
                        'chunk_index': chunk.get("chunk_index", 0)
                    })()
                    self.vector_retriever.id_to_idx[chunk["id"]] = loaded
                    self.vector_retriever.idx_to_id[loaded] = chunk["id"]
                    loaded += 1
            
            self.vector_retriever.current_idx = loaded
            return {"loaded": loaded, "success": True}
        except Exception as e:
            return {"loaded": 0, "error": str(e)}

    def set_llm_router(self, router):
        """Set the LLM router"""
        self.llm_router = router

    def set_vector_retriever(self, retriever):
        """Set the vector retriever (only loads from DB once)"""
        if self.vector_retriever is retriever:
            return  # Already set to same retriever, skip
        
        self.vector_retriever = retriever
        
        # Load existing documents from database (only if not already loaded)
        if self.use_persistent_storage and not getattr(self, '_db_loaded', False):
            result = self.load_from_database()
            if result.get("loaded", 0) > 0:
                print(f"📚 Loaded {result['loaded']} chunks from database")
            self._db_loaded = True

    def set_ingestion_engine(self, engine):
        """Set the ingestion engine"""
        self.ingestion_engine = engine

    async def ingest(
        self,
        content: str,
        filename: str = "document",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a document into the RAG knowledge base.
        
        Args:
            content: Document text content
            filename: Document identifier
            metadata: Optional metadata
            
        Returns:
            Ingestion result with chunk count
        """
        if self.ingestion_engine is None:
            return {"error": "Ingestion engine not configured", "success": False}

        result = await self.ingestion_engine.ingest_text(
            text=content,
            filename=filename,
            metadata=metadata
        )

        # Store chunks in vector retriever (in-memory)
        if self.vector_retriever and result.chunks:
            # Pass pre-computed embeddings if ALL chunks have them (avoid mixed None values)
            embeddings = None
            all_have_embeddings = all(c.embedding is not None for c in result.chunks)
            if all_have_embeddings:
                embeddings = [c.embedding for c in result.chunks]
            
            await self.vector_retriever.add_documents(
                documents=[c.content for c in result.chunks],
                embeddings=embeddings,
                ids=[c.id for c in result.chunks],
                metadata=[{
                    **c.metadata,
                    "doc_id": result.id,
                    "filename": filename,
                    "chunk_index": c.chunk_index
                } for c in result.chunks]
            )
        
        # Persist to database
        if self.use_persistent_storage and self.document_store and result.chunks:
            try:
                chunk_data = [
                    {
                        "content": c.content,
                        "chunk_index": c.chunk_index,
                        "start_char": c.start_char,
                        "end_char": c.end_char,
                        "metadata": c.metadata
                    }
                    for c in result.chunks
                ]
                
                # Get embeddings if available
                embeddings = [c.embedding for c in result.chunks if c.embedding]
                
                doc_id = self.document_store.add_document(
                    content=content,
                    filename=filename,
                    chunks=chunk_data,
                    embeddings=embeddings if embeddings else None,
                    metadata=metadata
                )
                print(f"💾 Saved to database: {filename} ({len(chunk_data)} chunks)")
            except Exception as e:
                print(f"⚠️ Failed to persist: {e}")

        return {
            "success": result.status == "completed",
            "doc_id": result.id,
            "filename": result.filename,
            "chunks": result.total_chunks,
            "status": result.status,
            "error": result.error
        }

    async def _retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Source]:
        """Retrieve relevant documents for a query"""
        if self.vector_retriever is None:
            return []

        results = await self.vector_retriever.search(
            query=query,
            top_k=top_k,
            filters=filters
        )

        return [
            Source(
                id=r.id,
                content=r.content,
                score=r.score,
                metadata=r.metadata
            )
            for r in results
        ]

    async def _expand_query(self, query: str) -> List[str]:
        """Expand query into multiple search queries"""
        if self.llm_router is None:
            return [query]

        prompt = self.QUERY_EXPANSION_PROMPT.format(query=query)
        
        try:
            response = await self.llm_router.run(
                model_id=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            expanded = response.get("content", "").strip().split("\n")
            queries = [q.strip() for q in expanded if q.strip()]
            return [query] + queries[:3]
        except Exception:
            return [query]

    async def _generate_hyde(self, query: str) -> str:
        """Generate hypothetical document for HyDE retrieval"""
        if self.llm_router is None:
            return query

        prompt = self.HYDE_PROMPT.format(query=query)
        
        try:
            response = await self.llm_router.run(
                model_id=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.get("content", query)
        except Exception:
            return query

    async def _step_back_query(self, query: str) -> str:
        """Generate step-back question"""
        if self.llm_router is None:
            return query

        prompt = self.STEP_BACK_PROMPT.format(query=query)
        
        try:
            response = await self.llm_router.run(
                model_id=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.get("content", query).strip()
        except Exception:
            return query

    def _build_context(self, sources: List[Source]) -> str:
        """Build context string from sources"""
        if not sources:
            return "No relevant context found."
        
        context_parts = []
        for i, source in enumerate(sources, 1):
            # Include metadata if available
            meta_str = ""
            if source.metadata.get("filename"):
                meta_str = f" (from: {source.metadata['filename']})"
            
            context_parts.append(f"[{i}]{meta_str}:\n{source.content}")
        
        return "\n\n".join(context_parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        system_prompt: str,
        history: Optional[List[ConversationMessage]] = None
    ) -> List[Dict[str, str]]:
        """Build message list for LLM"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if present
        if history:
            for msg in history[-6:]:  # Last 6 messages for context
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add current query with context
        user_message = f"""Context:
{context}

Question: {query}

Please answer based on the context provided. Cite sources using [1], [2], etc."""
        
        messages.append({"role": "user", "content": user_message})
        
        return messages

    async def query(
        self,
        query: str,
        mode: Optional[RAGMode] = None,
        top_k: Optional[int] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        temperature: float = 0.7
    ) -> RAGResponse:
        """
        Query the RAG system.
        
        Args:
            query: User's question
            mode: RAG mode (simple, conversational, multi, step_back, hyde)
            top_k: Number of documents to retrieve
            model: LLM model to use
            system_prompt: Custom system prompt
            filters: Metadata filters for retrieval
            conversation_id: ID for conversational mode
            temperature: LLM temperature
            
        Returns:
            RAGResponse with answer and sources
        """
        import time
        start_time = time.time()
        
        mode = mode or self.default_mode
        top_k = top_k or self.default_top_k
        model = model or self.default_model
        
        # Get system prompt
        if system_prompt is None:
            if mode == RAGMode.CONVERSATIONAL:
                system_prompt = self.SYSTEM_PROMPTS["conversational"]
            else:
                system_prompt = self.SYSTEM_PROMPTS["default"]
        
        # Get conversation history if conversational mode
        history = None
        if mode == RAGMode.CONVERSATIONAL and conversation_id:
            conv = self.conversations.get(conversation_id)
            if conv:
                history = conv.messages
        
        # Retrieve based on mode
        sources = []
        
        if mode == RAGMode.MULTI_QUERY:
            # Expand query and retrieve for each
            queries = await self._expand_query(query)
            all_sources = {}
            for q in queries:
                q_sources = await self._retrieve(q, top_k=top_k, filters=filters)
                for s in q_sources:
                    if s.id not in all_sources:
                        all_sources[s.id] = s
                    else:
                        # Boost score for documents found by multiple queries
                        all_sources[s.id].score += s.score
            
            sources = sorted(all_sources.values(), key=lambda x: x.score, reverse=True)[:top_k]
        
        elif mode == RAGMode.HYDE:
            # Generate hypothetical document and use it for retrieval
            hyde_doc = await self._generate_hyde(query)
            sources = await self._retrieve(hyde_doc, top_k=top_k, filters=filters)
        
        elif mode == RAGMode.STEP_BACK:
            # Get step-back question for broader context
            step_back_q = await self._step_back_query(query)
            # Retrieve for both original and step-back
            sources1 = await self._retrieve(query, top_k=top_k // 2 + 1, filters=filters)
            sources2 = await self._retrieve(step_back_q, top_k=top_k // 2 + 1, filters=filters)
            
            # Combine and deduplicate
            seen = set()
            sources = []
            for s in sources1 + sources2:
                if s.id not in seen:
                    seen.add(s.id)
                    sources.append(s)
            sources = sources[:top_k]
        
        else:  # SIMPLE or CONVERSATIONAL
            sources = await self._retrieve(query, top_k=top_k, filters=filters)
        
        # Build context and messages
        context = self._build_context(sources)
        messages = self._build_messages(query, context, system_prompt, history)
        
        # Generate response
        if self.llm_router is None:
            return RAGResponse(
                answer="LLM router not configured",
                sources=sources,
                query=query,
                model=model,
                mode=mode,
                metadata={"error": "LLM not configured"}
            )
        
        try:
            response = await self.llm_router.run(
                model_id=model,
                messages=messages,
                temperature=temperature
            )
            
            answer = response.get("content", "")
            tokens = response.get("usage", {}).get("total_tokens", 0)
            
            latency = (time.time() - start_time) * 1000
            
            # Store in conversation if conversational mode
            if mode == RAGMode.CONVERSATIONAL and conversation_id:
                self._add_to_conversation(
                    conversation_id,
                    query,
                    answer,
                    sources
                )
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                query=query,
                model=response.get("model", model),
                mode=mode,
                tokens_used=tokens,
                latency_ms=latency,
                metadata={
                    "context_length": len(context),
                    "sources_count": len(sources)
                }
            )
        
        except Exception as e:
            return RAGResponse(
                answer=f"Error generating response: {str(e)}",
                sources=sources,
                query=query,
                model=model,
                mode=mode,
                metadata={"error": str(e)}
            )

    async def stream_query(
        self,
        query: str,
        mode: Optional[RAGMode] = None,
        top_k: Optional[int] = None,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        system_prompt_prefix: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream RAG response with conversation history and document awareness.
        
        Args:
            query: The user's question
            mode: RAG mode to use
            top_k: Number of sources to retrieve
            model: LLM model to use
            conversation_id: Optional conversation ID for history
            document_ids: Optional list of document IDs to filter sources
            system_prompt_prefix: Optional prefix to add to system prompt (e.g., document awareness)
        
        Yields:
            Dict with 'type' (sources, chunk, done) and 'data'
        """
        mode = mode or self.default_mode
        top_k = top_k or self.default_top_k
        model = model or self.default_model
        
        # Get conversation history if available
        history = None
        if conversation_id and conversation_id in self.conversations:
            history = self.conversations[conversation_id].messages
        
        # First, retrieve sources
        sources = await self._retrieve(query, top_k=top_k)
        
        # Filter by document_ids if specified (check filename, document_id, and chunk id prefix)
        if document_ids:
            doc_id_set = set(document_ids)
            filtered_sources = []
            for s in sources:
                # Check various metadata fields
                doc_id = s.metadata.get("document_id") or s.metadata.get("filename")
                if doc_id and doc_id in doc_id_set:
                    filtered_sources.append(s)
                    continue
                # Also check if source id starts with any of the document ids
                for did in document_ids:
                    if s.id.startswith(did) or did in s.id:
                        filtered_sources.append(s)
                        break
            sources = filtered_sources
        
        # Yield sources first
        yield {
            "type": "sources",
            "data": [
                {
                    "id": s.id,
                    "content": s.content[:200] + "..." if len(s.content) > 200 else s.content,
                    "score": s.score,
                    "metadata": s.metadata
                }
                for s in sources
            ]
        }
        
        # Build context and messages with history
        context = self._build_context(sources)
        base_system_prompt = self.SYSTEM_PROMPTS["default"]
        
        # Combine document awareness prefix with default system prompt
        if system_prompt_prefix:
            system_prompt = f"{system_prompt_prefix}\n\n{base_system_prompt}"
        else:
            system_prompt = base_system_prompt
        
        messages = self._build_messages(query, context, system_prompt, history)
        
        # Collect full response for conversation storage
        full_response = ""
        
        # Stream LLM response
        if self.llm_router:
            try:
                async for chunk in self.llm_router.stream(
                    model_id=model,
                    messages=messages
                ):
                    if chunk.get("chunk"):
                        full_response += chunk["chunk"]
                        yield {"type": "chunk", "data": chunk["chunk"]}
                    if chunk.get("done"):
                        # Store in conversation history
                        if conversation_id:
                            self._add_to_conversation(
                                conversation_id,
                                query,
                                full_response,
                                sources
                            )
                        yield {"type": "done", "data": {"model": model}}
            except Exception as e:
                yield {"type": "error", "data": str(e)}
        else:
            yield {"type": "error", "data": "LLM router not configured"}

    def _add_to_conversation(
        self,
        conversation_id: str,
        query: str,
        answer: str,
        sources: List[Source]
    ):
        """Add messages to conversation history"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = Conversation(id=conversation_id)
        
        conv = self.conversations[conversation_id]
        conv.messages.append(ConversationMessage(role="user", content=query))
        conv.messages.append(ConversationMessage(role="assistant", content=answer, sources=sources))

    def create_conversation(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new conversation"""
        conv_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12]
        self.conversations[conv_id] = Conversation(
            id=conv_id,
            metadata=metadata or {}
        )
        return conv_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        return self.conversations.get(conversation_id)

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        vector_stats = {}
        if self.vector_retriever:
            vector_stats = self.vector_retriever.get_stats()
        
        # Get database stats if persistent storage is enabled
        db_stats = {}
        if self.use_persistent_storage and self.document_store:
            try:
                db_stats = {
                    "documents": self.document_store.count_documents(),
                    "chunks": self.document_store.count_chunks(),
                    "persistent": True
                }
            except Exception:
                db_stats = {"persistent": False, "error": "Could not connect"}
        else:
            db_stats = {"persistent": False}
        
        return {
            "vector_store": vector_stats,
            "database": db_stats,
            "conversations": len(self.conversations),
            "llm_configured": self.llm_router is not None,
            "ingestion_configured": self.ingestion_engine is not None,
            "default_model": self.default_model,
            "default_top_k": self.default_top_k
        }

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the knowledge base.
        
        Returns:
            List of document info dicts with id, filename, chunk_count
        """
        documents = []
        
        # Try to get from database if persistent storage is enabled
        if self.use_persistent_storage and self.document_store:
            try:
                db_docs = self.document_store.list_documents(limit=1000)
                for doc in db_docs:
                    documents.append({
                        "id": doc.get("id", ""),
                        "filename": doc.get("filename", doc.get("id", "unknown")),
                        "chunk_count": doc.get("chunk_count", 0),
                        "created_at": doc.get("created_at")
                    })
            except Exception:
                pass
        
        # Also get from vector store metadata
        if self.vector_retriever and hasattr(self.vector_retriever, 'documents'):
            seen_ids = {d["id"] for d in documents}
            try:
                for doc_id, doc_info in getattr(self.vector_retriever, 'documents', {}).items():
                    if doc_id not in seen_ids:
                        if isinstance(doc_info, dict):
                            documents.append({
                                "id": doc_id,
                                "filename": doc_info.get("filename", doc_id),
                                "chunk_count": doc_info.get("chunk_count", 0)
                            })
                        else:
                            documents.append({
                                "id": doc_id,
                                "filename": str(doc_info) if doc_info else doc_id,
                                "chunk_count": 0
                            })
            except Exception:
                pass
        
        # Fallback: extract from vector store chunks
        if not documents and self.vector_retriever:
            try:
                doc_chunks = {}
                for chunk_id, metadata in getattr(self.vector_retriever, 'metadata', {}).items():
                    if isinstance(metadata, dict):
                        doc_id = metadata.get("document_id", chunk_id.split("_")[0] if "_" in chunk_id else chunk_id)
                        filename = metadata.get("filename", doc_id)
                    else:
                        doc_id = chunk_id.split("_")[0] if "_" in chunk_id else chunk_id
                        filename = doc_id
                    if doc_id not in doc_chunks:
                        doc_chunks[doc_id] = {"id": doc_id, "filename": filename, "chunk_count": 0}
                    doc_chunks[doc_id]["chunk_count"] += 1
                documents = list(doc_chunks.values())
            except Exception:
                pass
        
        return documents


# Singleton instance
rag_engine = RAGEngine()


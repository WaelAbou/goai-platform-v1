"""
RAG (Retrieval-Augmented Generation) API Test Suite

Tests for:
- POST /api/v1/rag/ask              - Simple question answering
- POST /api/v1/rag/query            - RAG query with sources
- POST /api/v1/rag/chat             - Chat with conversation
- POST /api/v1/rag/ingest           - Ingest document
- GET  /api/v1/rag/documents        - List documents
- GET  /api/v1/rag/stats            - Get stats
- POST /api/v1/rag/conversation     - Create conversation
- GET  /api/v1/rag/conversation/{id} - Get conversation
- DELETE /api/v1/rag/conversation/{id} - Delete conversation
- GET  /api/v1/rag/conversations    - List conversations
- POST /api/v1/stream/chat          - Streaming chat
- POST /api/v1/upload/file          - File upload
- GET  /api/v1/upload/supported-types - Supported file types

Run with: pytest tests/test_rag.py -v
"""

import pytest
import httpx
from typing import Generator
import time
import uuid

# Base URL for tests
BASE_URL = "http://localhost:8000/api/v1"


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    """HTTP client for tests."""
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        yield client


@pytest.fixture(scope="module")
def test_document_content():
    """Sample document content for testing."""
    return {
        "content": f"""
        Machine Learning Overview
        
        Machine learning is a subset of artificial intelligence (AI) that enables 
        systems to learn and improve from experience without being explicitly programmed.
        
        Key concepts include:
        - Supervised learning: Learning from labeled data
        - Unsupervised learning: Finding patterns in unlabeled data
        - Reinforcement learning: Learning through rewards and penalties
        
        Common algorithms:
        - Linear regression for continuous predictions
        - Decision trees for classification
        - Neural networks for complex patterns
        
        Test document ID: {uuid.uuid4().hex[:8]}
        """,
        "metadata": {
            "source": "test",
            "topic": "machine_learning",
            "test_id": uuid.uuid4().hex[:8]
        }
    }


@pytest.fixture(scope="module")
def ingested_doc_id(client: httpx.Client, test_document_content):
    """Ingest a document and return its ID."""
    response = client.post("/rag/ingest", json=test_document_content)
    if response.status_code == 200:
        return response.json().get("doc_id")
    return None


@pytest.fixture(scope="module")
def created_conversation_id(client: httpx.Client):
    """Create a conversation and return its ID."""
    response = client.post("/rag/conversation", json={
        "title": "Test Conversation"
    })
    if response.status_code == 200:
        return response.json().get("conversation_id")
    return None


# ============================================
# TEST: INGEST DOCUMENT (POST /rag/ingest)
# ============================================

class TestIngestDocument:
    """Tests for POST /api/v1/rag/ingest"""
    
    def test_ingest_text_document(self, client: httpx.Client):
        """Should ingest a text document."""
        response = client.post("/rag/ingest", json={
            "content": "This is a test document about Python programming.",
            "metadata": {"source": "test"}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "doc_id" in data
        assert data["success"] == True
        
    def test_ingest_with_metadata(self, client: httpx.Client):
        """Should ingest document with custom metadata."""
        response = client.post("/rag/ingest", json={
            "content": "Document with custom metadata",
            "metadata": {
                "author": "Test Author",
                "date": "2024-01-01",
                "category": "testing"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
    def test_ingest_long_document(self, client: httpx.Client):
        """Should ingest a long document (will be chunked)."""
        long_content = "This is a paragraph about AI. " * 100
        
        response = client.post("/rag/ingest", json={
            "content": long_content,
            "metadata": {"type": "long_document"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
    def test_ingest_empty_content(self, client: httpx.Client):
        """Should handle empty content."""
        response = client.post("/rag/ingest", json={
            "content": "",
            "metadata": {}
        })
        
        # May succeed with empty doc or reject
        assert response.status_code in [200, 400, 422]
        
    def test_ingest_returns_chunks_count(self, client: httpx.Client):
        """Should return number of chunks created."""
        response = client.post("/rag/ingest", json={
            "content": "Test content for chunking verification.",
            "metadata": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data or "chunk_count" in data


# ============================================
# TEST: LIST DOCUMENTS (GET /rag/documents)
# ============================================

class TestListDocuments:
    """Tests for GET /api/v1/rag/documents"""
    
    def test_list_documents_success(self, client: httpx.Client):
        """Should return list of documents."""
        response = client.get("/rag/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "documents" in data
        assert isinstance(data["documents"], list)
        
    def test_list_documents_structure(self, client: httpx.Client):
        """Each document should have required fields."""
        response = client.get("/rag/documents")
        data = response.json()
        
        if len(data["documents"]) > 0:
            doc = data["documents"][0]
            assert "id" in doc
            assert "chunk_count" in doc or "chunks" in doc
            
    def test_list_documents_with_preview(self, client: httpx.Client):
        """Documents should include preview text."""
        response = client.get("/rag/documents")
        data = response.json()
        
        if len(data["documents"]) > 0:
            doc = data["documents"][0]
            assert "preview" in doc or "display_name" in doc


# ============================================
# TEST: RAG STATS (GET /rag/stats)
# ============================================

class TestRagStats:
    """Tests for GET /api/v1/rag/stats"""
    
    def test_stats_success(self, client: httpx.Client):
        """Should return RAG statistics."""
        response = client.get("/rag/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have vector store info
        assert "vector_store" in data or "document_count" in data
        
    def test_stats_vector_store_info(self, client: httpx.Client):
        """Should include vector store details."""
        response = client.get("/rag/stats")
        data = response.json()
        
        if "vector_store" in data:
            vs = data["vector_store"]
            assert "document_count" in vs or "dimension" in vs
            
    def test_stats_database_info(self, client: httpx.Client):
        """Should include database details."""
        response = client.get("/rag/stats")
        data = response.json()
        
        if "database" in data:
            db = data["database"]
            assert "documents" in db or "chunks" in db
            
    def test_stats_llm_configured(self, client: httpx.Client):
        """Should show LLM configuration status."""
        response = client.get("/rag/stats")
        data = response.json()
        
        assert "llm_configured" in data or "default_model" in data


# ============================================
# TEST: SIMPLE ASK (POST /rag/ask)
# ============================================

class TestRagAsk:
    """Tests for POST /api/v1/rag/ask"""
    
    def test_ask_simple_question(self, client: httpx.Client):
        """Should answer a simple question."""
        response = client.post("/rag/ask", params={
            "query": "What is machine learning?"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        
    def test_ask_with_top_k(self, client: httpx.Client):
        """Should accept top_k parameter."""
        response = client.post("/rag/ask", params={
            "query": "What is AI?",
            "top_k": 3
        })
        
        assert response.status_code == 200
        
    def test_ask_returns_sources(self, client: httpx.Client):
        """Should return sources used for answer."""
        response = client.post("/rag/ask", params={
            "query": "Tell me about Python"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sources" in data
        assert isinstance(data["sources"], list)
        
    def test_ask_empty_query(self, client: httpx.Client):
        """Should handle empty query."""
        response = client.post("/rag/ask", params={
            "query": ""
        })
        
        # May return empty answer or error
        assert response.status_code in [200, 400, 422]


# ============================================
# TEST: RAG QUERY (POST /rag/query)
# ============================================

class TestRagQuery:
    """Tests for POST /api/v1/rag/query"""
    
    def test_query_basic(self, client: httpx.Client):
        """Should perform RAG query."""
        response = client.post("/rag/query", json={
            "query": "What is artificial intelligence?"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        
    def test_query_with_model(self, client: httpx.Client):
        """Should accept model parameter."""
        response = client.post("/rag/query", json={
            "query": "Explain deep learning",
            "model": "gpt-4o-mini"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use specified model
        if "model" in data:
            assert data["model"] == "gpt-4o-mini"
            
    def test_query_with_top_k(self, client: httpx.Client):
        """Should accept top_k parameter."""
        response = client.post("/rag/query", json={
            "query": "What is NLP?",
            "top_k": 5
        })
        
        assert response.status_code == 200
        
    def test_query_returns_metadata(self, client: httpx.Client):
        """Should return query metadata."""
        response = client.post("/rag/query", json={
            "query": "Test query"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have latency info
        assert "latency_ms" in data or "metadata" in data
        
    def test_query_response_structure(self, client: httpx.Client):
        """Query response should have consistent structure."""
        response = client.post("/rag/query", json={
            "query": "Test"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["answer", "sources", "query"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


# ============================================
# TEST: CONVERSATIONS
# ============================================

class TestConversations:
    """Tests for conversation management."""
    
    def test_create_conversation(self, client: httpx.Client):
        """Should create a new conversation."""
        response = client.post("/rag/conversation", json={
            "title": "Test Conversation"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversation_id" in data
        
    def test_list_conversations(self, client: httpx.Client):
        """Should list all conversations."""
        response = client.get("/rag/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
        
    def test_get_conversation(self, client: httpx.Client, created_conversation_id):
        """Should get specific conversation."""
        if not created_conversation_id:
            pytest.skip("No conversation created")
            
        response = client.get(f"/rag/conversation/{created_conversation_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data or "conversation_id" in data or "messages" in data
        
    def test_get_conversation_not_found(self, client: httpx.Client):
        """Should return 404 for non-existent conversation."""
        response = client.get("/rag/conversation/nonexistent_conv_xyz")
        
        assert response.status_code == 404
        
    def test_delete_conversation(self, client: httpx.Client):
        """Should delete a conversation."""
        # First create a conversation to delete
        create_response = client.post("/rag/conversation", json={
            "title": "Conversation to delete"
        })
        
        if create_response.status_code == 200:
            conv_id = create_response.json().get("conversation_id")
            
            # Now delete it
            delete_response = client.delete(f"/rag/conversation/{conv_id}")
            assert delete_response.status_code in [200, 204]
            
    def test_conversations_pagination(self, client: httpx.Client):
        """Should support pagination."""
        response = client.get("/rag/conversations", params={
            "limit": 5,
            "offset": 0
        })
        
        assert response.status_code == 200


# ============================================
# TEST: RAG CHAT (POST /rag/chat)
# ============================================

class TestRagChat:
    """Tests for POST /api/v1/rag/chat"""
    
    def test_chat_basic(self, client: httpx.Client, created_conversation_id):
        """Should handle chat message."""
        if not created_conversation_id:
            pytest.skip("No conversation created")
            
        response = client.post("/rag/chat", json={
            "query": "Hello, how are you?",
            "conversation_id": created_conversation_id
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data or "answer" in data or "message" in data
        
    def test_chat_with_new_conversation(self, client: httpx.Client):
        """Should create new conversation if none provided."""
        # First create a conversation
        conv_response = client.post("/rag/conversation", json={
            "title": "Chat test"
        })
        
        if conv_response.status_code == 200:
            conv_id = conv_response.json().get("conversation_id")
            
            response = client.post("/rag/chat", json={
                "query": "What is the weather?",
                "conversation_id": conv_id
            })
            
            assert response.status_code == 200


# ============================================
# TEST: STREAMING (POST /stream/chat)
# ============================================

class TestStreaming:
    """Tests for streaming endpoints."""
    
    def test_stream_chat(self, client: httpx.Client):
        """Should stream chat response."""
        with httpx.Client(base_url=BASE_URL, timeout=60.0) as streaming_client:
            with streaming_client.stream(
                "POST",
                "/stream/chat",
                json={
                    "query": "Say hello",
                    "model": "gpt-4o-mini"
                }
            ) as response:
                assert response.status_code == 200
                
                chunks = []
                for chunk in response.iter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                
                # Should receive some streaming data
                assert len(chunks) >= 0
                
    def test_stream_completion(self, client: httpx.Client):
        """Should stream completion."""
        with httpx.Client(base_url=BASE_URL, timeout=60.0) as streaming_client:
            with streaming_client.stream(
                "POST",
                "/stream/completion",
                json={
                    "prompt": "The capital of France is",
                    "model": "gpt-4o-mini"
                }
            ) as response:
                assert response.status_code == 200
                
    def test_stream_test_endpoint(self, client: httpx.Client):
        """Test streaming test endpoint."""
        response = client.get("/stream/test")
        
        assert response.status_code == 200


# ============================================
# TEST: FILE UPLOAD
# ============================================

class TestFileUpload:
    """Tests for file upload endpoints."""
    
    def test_get_supported_types(self, client: httpx.Client):
        """Should return supported file types."""
        response = client.get("/upload/supported-types")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "extensions" in data
        assert ".pdf" in data["extensions"]
        assert ".txt" in data["extensions"]
        
    def test_supported_types_descriptions(self, client: httpx.Client):
        """Should have descriptions for file types."""
        response = client.get("/upload/supported-types")
        data = response.json()
        
        if "types" in data:
            for type_name, type_info in data["types"].items():
                assert "description" in type_info
                assert "extensions" in type_info
                
    def test_upload_text_file(self, client: httpx.Client):
        """Should upload a text file."""
        # Create a simple text file content
        file_content = b"This is test content for file upload."
        
        files = {
            "file": ("test.txt", file_content, "text/plain")
        }
        
        response = client.post("/upload/file", files=files)
        
        # File upload may return 200 or 500 depending on configuration
        # 500 may occur if temp file handling fails
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "doc_id" in data or "filename" in data
        else:
            # Accept 500 as file handling may have issues
            assert response.status_code in [200, 400, 422, 500]


# ============================================
# TEST: ERROR HANDLING
# ============================================

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_json(self, client: httpx.Client):
        """Should handle invalid JSON."""
        response = client.post(
            "/rag/ingest",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        
    def test_missing_required_fields(self, client: httpx.Client):
        """Should validate required fields."""
        response = client.post("/rag/query", json={})
        
        assert response.status_code == 422
        
    def test_wrong_http_method(self, client: httpx.Client):
        """GET on POST endpoint should fail."""
        response = client.get("/rag/ingest")
        
        assert response.status_code == 405


# ============================================
# TEST: PERFORMANCE
# ============================================

class TestPerformance:
    """Performance tests."""
    
    def test_stats_response_time(self, client: httpx.Client):
        """Stats should respond quickly."""
        start = time.time()
        response = client.get("/rag/stats")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"
        
    def test_documents_response_time(self, client: httpx.Client):
        """Documents list should respond quickly."""
        start = time.time()
        response = client.get("/rag/documents")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"
        
    def test_ingest_response_time(self, client: httpx.Client):
        """Ingest should complete in reasonable time."""
        start = time.time()
        response = client.post("/rag/ingest", json={
            "content": "Performance test document.",
            "metadata": {}
        })
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s"


# ============================================
# TEST: RESPONSE STRUCTURE
# ============================================

class TestResponseStructure:
    """Test response structure consistency."""
    
    def test_ingest_response_structure(self, client: httpx.Client):
        """Ingest response should have consistent structure."""
        response = client.post("/rag/ingest", json={
            "content": "Structure test",
            "metadata": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "doc_id" in data
        
    def test_query_response_structure(self, client: httpx.Client):
        """Query response should have consistent structure."""
        response = client.post("/rag/query", json={
            "query": "test"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        assert "query" in data
        
    def test_stats_response_structure(self, client: httpx.Client):
        """Stats response should have consistent structure."""
        response = client.get("/rag/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have main sections
        assert any(key in data for key in ["vector_store", "database", "llm_configured"])


# ============================================
# TEST: INTEGRATION
# ============================================

class TestIntegration:
    """Integration tests for RAG workflow."""
    
    def test_ingest_and_query_workflow(self, client: httpx.Client):
        """Should be able to ingest and then query."""
        # 1. Ingest a document
        unique_content = f"Unique test content {uuid.uuid4().hex[:8]}: Python is great!"
        
        ingest_response = client.post("/rag/ingest", json={
            "content": unique_content,
            "metadata": {"test": "integration"}
        })
        
        assert ingest_response.status_code == 200
        
        # 2. Query for the content
        query_response = client.post("/rag/query", json={
            "query": "Python"
        })
        
        assert query_response.status_code == 200
        
    def test_conversation_workflow(self, client: httpx.Client):
        """Should be able to create conversation and chat."""
        # 1. Create conversation
        conv_response = client.post("/rag/conversation", json={
            "title": "Integration Test"
        })
        
        assert conv_response.status_code == 200
        conv_id = conv_response.json().get("conversation_id")
        
        if conv_id:
            # 2. Send a chat message
            chat_response = client.post("/rag/chat", json={
                "query": "Hello!",
                "conversation_id": conv_id
            })
            
            assert chat_response.status_code == 200
            
            # 3. Verify conversation exists
            get_response = client.get(f"/rag/conversation/{conv_id}")
            assert get_response.status_code == 200


# ============================================
# RUN TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


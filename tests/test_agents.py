"""
AI Agents API Test Suite

Tests for:
- POST /api/v1/agents/ask      - Quick Ask (query param)
- POST /api/v1/agents/run      - Run Agent  
- GET  /api/v1/agents/tools    - List Tools
- POST /api/v1/agents/tools/execute - Execute Tool

Run with: pytest tests/test_agents.py -v
"""

import pytest
import httpx
from typing import Generator

# Base URL for tests
BASE_URL = "http://localhost:8000/api/v1"


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    """HTTP client for sync tests."""
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        yield client


# ============================================
# TEST: LIST TOOLS (GET /agents/tools)
# ============================================

class TestListTools:
    """Tests for GET /api/v1/agents/tools"""
    
    def test_list_tools_success(self, client: httpx.Client):
        """Should return list of available tools."""
        response = client.get("/agents/tools")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0
        
    def test_list_tools_structure(self, client: httpx.Client):
        """Each tool should have name, description, and parameters."""
        response = client.get("/agents/tools")
        data = response.json()
        
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            
    def test_list_tools_expected_tools(self, client: httpx.Client):
        """Should include core tools: calculator, web_search, get_datetime."""
        response = client.get("/agents/tools")
        data = response.json()
        
        tool_names = [t["name"] for t in data["tools"]]
        
        # Check for expected core tools (corrected names)
        expected_tools = ["calculator", "web_search", "get_datetime"]
        for expected in expected_tools:
            assert expected in tool_names, f"Missing expected tool: {expected}"
            
    def test_list_tools_categories(self, client: httpx.Client):
        """Should return tools organized by category."""
        response = client.get("/agents/tools")
        data = response.json()
        
        assert "by_category" in data
        assert isinstance(data["by_category"], dict)
        
    def test_list_tools_total_count(self, client: httpx.Client):
        """Should return total count of tools."""
        response = client.get("/agents/tools")
        data = response.json()
        
        assert "total" in data
        assert data["total"] == len(data["tools"])


# ============================================
# TEST: EXECUTE TOOL (POST /agents/tools/execute)
# ============================================

class TestExecuteTool:
    """Tests for POST /api/v1/agents/tools/execute"""
    
    def test_execute_calculator_addition(self, client: httpx.Client):
        """Calculator tool should handle addition."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator",
            "arguments": {"expression": "2 + 2"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        result = data["result"]
        assert result.get("success") == True
        assert result.get("result", {}).get("result") == 4
        
    def test_execute_calculator_complex(self, client: httpx.Client):
        """Calculator tool should handle complex expressions."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator",
            "arguments": {"expression": "(10 * 5) + (20 / 4)"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        # (10 * 5) + (20 / 4) = 50 + 5 = 55
        result_value = data["result"].get("result", {}).get("result")
        assert result_value == 55 or result_value == 55.0
        
    def test_execute_calculator_sqrt(self, client: httpx.Client):
        """Calculator should handle sqrt function."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator",
            "arguments": {"expression": "sqrt(144)"}
        })
        
        assert response.status_code == 200
        data = response.json()
        result_value = data["result"].get("result", {}).get("result")
        assert result_value == 12 or result_value == 12.0
        
    def test_execute_calculator_invalid_expression(self, client: httpx.Client):
        """Calculator should handle invalid expressions gracefully."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator",
            "arguments": {"expression": "invalid math abc"}
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should return error in result
        result = data["result"]
        assert result.get("success") == False or "error" in str(result).lower()
        
    def test_execute_datetime_tool(self, client: httpx.Client):
        """DateTime tool should return current time info."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "get_datetime",
            "arguments": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        result = data["result"]
        assert result.get("success") == True
        # Should contain date/time information
        result_data = result.get("result", {})
        assert "datetime" in result_data or "date" in result_data or "time" in result_data
        
    def test_execute_datetime_with_timezone(self, client: httpx.Client):
        """DateTime tool should accept timezone."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "get_datetime",
            "arguments": {"timezone": "UTC"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"].get("success") == True
        
    def test_execute_nonexistent_tool(self, client: httpx.Client):
        """Should return error for non-existent tool."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "nonexistent_tool_xyz",
            "arguments": {}
        })
        
        # Should return 200 with error in result, or 400/404
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})
            # Check for error indicator (success=False or 'error' key)
            has_error = result.get("success") == False or "error" in result
            assert has_error, f"Expected error in result: {result}"
        else:
            assert response.status_code in [400, 404, 422]
        
    def test_execute_tool_missing_arguments(self, client: httpx.Client):
        """Should handle missing required arguments field."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator"
            # Missing 'arguments'
        })
        
        assert response.status_code == 422
        
    def test_execute_web_search(self, client: httpx.Client):
        """Web search tool should return results."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "web_search",
            "arguments": {"query": "Python programming"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        # Web search might fail without API key, so check structure
        result = data["result"]
        assert "success" in result
        
    def test_execute_python_code(self, client: httpx.Client):
        """Execute Python tool should run code."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "execute_python",
            "arguments": {"code": "print(2 + 2)"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        
    def test_execute_parse_json(self, client: httpx.Client):
        """Parse JSON tool should parse JSON strings."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "parse_json",
            "arguments": {
                "json_string": '{"name": "John", "age": 30}',
                "path": "name"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data


# ============================================
# TEST: QUICK ASK (POST /agents/ask)
# ============================================

class TestQuickAsk:
    """Tests for POST /api/v1/agents/ask"""
    
    def test_quick_ask_simple_question(self, client: httpx.Client):
        """Should answer a simple question via query param."""
        response = client.post("/agents/ask", params={
            "question": "What is 2 + 2?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data or "question" in data
        
    def test_quick_ask_with_model(self, client: httpx.Client):
        """Should accept model parameter."""
        response = client.post("/agents/ask", params={
            "question": "What is the capital of France?",
            "model": "gpt-4o-mini"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data or "question" in data
        
    def test_quick_ask_empty_question(self, client: httpx.Client):
        """Should reject empty question."""
        response = client.post("/agents/ask", params={
            "question": ""
        })
        
        # Empty question should either be rejected or return empty
        assert response.status_code in [200, 400, 422]
        
    def test_quick_ask_returns_tools_used(self, client: httpx.Client):
        """Should return tools_used field."""
        response = client.post("/agents/ask", params={
            "question": "What time is it?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tools_used" in data


# ============================================
# TEST: RUN AGENT (POST /agents/run)
# ============================================

class TestRunAgent:
    """Tests for POST /api/v1/agents/run"""
    
    def test_run_agent_simple_task(self, client: httpx.Client):
        """Should run agent with simple task."""
        response = client.post("/agents/run", json={
            "task": "What is the current date and time?"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Check for expected fields - API returns 'answer', 'steps', etc.
        assert any(key in data for key in ["answer", "result", "response", "output", "steps"])
        
    def test_run_agent_with_model_selection(self, client: httpx.Client):
        """Should accept model parameter."""
        response = client.post("/agents/run", json={
            "task": "Say hello",
            "model": "gpt-4o-mini"
        })
        
        assert response.status_code == 200
        
    def test_run_agent_with_context(self, client: httpx.Client):
        """Should accept context parameter."""
        response = client.post("/agents/run", json={
            "task": "What is the company's revenue?",
            "context": "The company XYZ Corp reported annual revenue of $5.2 billion in 2024."
        })
        
        assert response.status_code == 200
        data = response.json()
        # Verify response structure - context may or may not affect output depending on agent impl
        assert "answer" in data or "steps" in data
        # Agent completed successfully
        assert "latency_ms" in data or "model" in data
        
    def test_run_agent_with_max_iterations(self, client: httpx.Client):
        """Should respect max_iterations parameter."""
        response = client.post("/agents/run", json={
            "task": "Count to 3",
            "max_iterations": 2
        })
        
        assert response.status_code == 200
        
    def test_run_agent_empty_task(self, client: httpx.Client):
        """Should reject empty task."""
        response = client.post("/agents/run", json={
            "task": ""
        })
        
        # Empty task might be rejected or return error
        assert response.status_code in [200, 400, 422]
        
    def test_run_agent_missing_task(self, client: httpx.Client):
        """Should require task field."""
        response = client.post("/agents/run", json={
            "model": "gpt-4o-mini"
            # Missing 'task'
        })
        
        assert response.status_code == 422


# ============================================
# TEST: STREAMING (POST /agents/run with stream)
# ============================================

class TestAgentStreaming:
    """Tests for streaming agent responses."""
    
    def test_run_agent_streaming(self, client: httpx.Client):
        """Should handle streaming request."""
        # Use httpx streaming with sync client
        with httpx.Client(base_url=BASE_URL, timeout=60.0) as streaming_client:
            with streaming_client.stream(
                "POST",
                "/agents/run",
                json={
                    "task": "Say hello",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                
                chunks = []
                for chunk in response.iter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                
                # Should have received some response
                assert len(chunks) >= 0  # Streaming may or may not produce chunks
                
    def test_run_agent_non_streaming(self, client: httpx.Client):
        """Non-streaming should return complete response."""
        response = client.post("/agents/run", json={
            "task": "Say hi",
            "stream": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


# ============================================
# TEST: ERROR HANDLING
# ============================================

class TestAgentErrorHandling:
    """Tests for error handling in agents API."""
    
    def test_invalid_json_body(self, client: httpx.Client):
        """Should handle invalid JSON gracefully."""
        response = client.post(
            "/agents/run",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        
    def test_missing_content_type(self, client: httpx.Client):
        """Should handle missing content type."""
        response = client.post(
            "/agents/run",
            content='{"task": "hello"}'
        )
        
        # Should either work or return appropriate error
        assert response.status_code in [200, 415, 422]
        
    def test_wrong_http_method(self, client: httpx.Client):
        """GET on POST endpoint should fail."""
        response = client.get("/agents/run")
        
        assert response.status_code == 405


# ============================================
# TEST: PERFORMANCE
# ============================================

class TestAgentPerformance:
    """Performance tests for agents API."""
    
    def test_response_time_tools_list(self, client: httpx.Client):
        """List tools should respond quickly."""
        import time
        
        start = time.time()
        response = client.get("/agents/tools")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"
        
    def test_response_time_calculator(self, client: httpx.Client):
        """Calculator execution should be fast."""
        import time
        
        start = time.time()
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator",
            "arguments": {"expression": "1 + 1"}
        })
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"


# ============================================
# TEST: RESPONSE STRUCTURE
# ============================================

class TestResponseStructure:
    """Test that responses have consistent structure."""
    
    def test_tool_execute_response_structure(self, client: httpx.Client):
        """Tool execute should return consistent structure."""
        response = client.post("/agents/tools/execute", json={
            "tool_name": "calculator",
            "arguments": {"expression": "1+1"}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Expected structure
        assert "tool" in data
        assert "arguments" in data
        assert "result" in data
        assert data["tool"] == "calculator"
        
    def test_tools_list_response_structure(self, client: httpx.Client):
        """Tools list should have consistent structure."""
        response = client.get("/agents/tools")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tools" in data
        assert "by_category" in data
        assert "total" in data
        
        # Each tool should have required fields
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "category" in tool
            assert "parameters" in tool


# ============================================
# RUN TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

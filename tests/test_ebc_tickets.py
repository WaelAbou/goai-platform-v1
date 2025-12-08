"""
EBC Tickets API Test Suite

Tests for:
- POST /api/v1/ebc-tickets/analyze           - Analyze single ticket
- POST /api/v1/ebc-tickets/analyze/bulk      - Analyze multiple tickets  
- GET  /api/v1/ebc-tickets/tickets           - List tickets
- GET  /api/v1/ebc-tickets/tickets/{id}      - Get specific ticket
- PUT  /api/v1/ebc-tickets/tickets/{id}      - Update ticket
- GET  /api/v1/ebc-tickets/dashboard         - Dashboard stats
- GET  /api/v1/ebc-tickets/analytics         - Analytics data
- POST /api/v1/ebc-tickets/demo/seed         - Seed demo data

Run with: pytest tests/test_ebc_tickets.py -v
"""

import pytest
import httpx
from typing import Generator
import time

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
def sample_ticket():
    """Sample ticket data for testing."""
    return {
        "subject": "Internet Connection Issues",
        "content": "My internet has been very slow for the past week. I've tried restarting my router but the problem persists. Please help!",
        "customer_id": "CUST001",
        "customer_name": "John Smith",
        "channel": "email",
        "use_llm": False,
        "save_ticket": False
    }


@pytest.fixture(scope="module")
def angry_ticket():
    """Angry/negative sentiment ticket."""
    return {
        "subject": "URGENT: Service Down!!!",
        "content": "This is absolutely unacceptable! My service has been down for 3 days and no one is helping. I am FURIOUS and will cancel immediately if this isn't fixed TODAY!",
        "customer_name": "Angry Customer",
        "channel": "phone",
        "use_llm": False,
        "save_ticket": False
    }


@pytest.fixture(scope="module")
def positive_ticket():
    """Positive sentiment ticket."""
    return {
        "subject": "Thank you for excellent service",
        "content": "I just wanted to say thank you for the amazing support I received yesterday. The technician was very helpful and resolved my issue quickly. Great job!",
        "customer_name": "Happy Customer",
        "channel": "chat",
        "use_llm": False,
        "save_ticket": False
    }


@pytest.fixture(scope="module")
def created_ticket_id(client: httpx.Client, sample_ticket):
    """Create a ticket and return its ID for other tests."""
    ticket_data = sample_ticket.copy()
    ticket_data["save_ticket"] = True
    response = client.post("/ebc-tickets/analyze", json=ticket_data)
    if response.status_code == 200:
        return response.json().get("ticket_id")
    return None


# ============================================
# TEST: ANALYZE TICKET (POST /ebc-tickets/analyze)
# ============================================

class TestAnalyzeTicket:
    """Tests for POST /api/v1/ebc-tickets/analyze"""
    
    def test_analyze_ticket_basic(self, client: httpx.Client, sample_ticket):
        """Should analyze a basic ticket."""
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "ticket_id" in data
        assert "sentiment" in data
        assert "priority" in data
        assert "category" in data
        
    def test_analyze_ticket_sentiment_negative(self, client: httpx.Client, angry_ticket):
        """Should detect negative sentiment."""
        response = client.post("/ebc-tickets/analyze", json=angry_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sentiment"] == "negative"
        assert data["sentiment_score"] < 0
        
    def test_analyze_ticket_sentiment_positive(self, client: httpx.Client, positive_ticket):
        """Should detect positive sentiment."""
        response = client.post("/ebc-tickets/analyze", json=positive_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sentiment"] == "positive"
        assert data["sentiment_score"] > 0
        
    def test_analyze_ticket_priority_critical(self, client: httpx.Client):
        """Critical tickets should get high priority."""
        critical_ticket = {
            "subject": "URGENT: Complete outage",
            "content": "Everything is down! This is critical - we're losing money every minute. Cancel my service if not fixed immediately!",
            "customer_name": "Business Customer",
            "use_llm": False
        }
        response = client.post("/ebc-tickets/analyze", json=critical_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be high or critical priority
        assert data["priority"] in ["high", "critical"]
        
    def test_analyze_ticket_category_billing(self, client: httpx.Client):
        """Should categorize billing issues."""
        billing_ticket = {
            "subject": "Wrong charge on my bill",
            "content": "I was charged $50 extra on my last invoice. This is a billing error and I need a refund for the overcharge.",
            "customer_name": "Test Customer",
            "use_llm": False
        }
        response = client.post("/ebc-tickets/analyze", json=billing_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be billing or account related
        assert data["category"] in ["billing", "account", "payment", "inquiry"]
        
    def test_analyze_ticket_category_technical(self, client: httpx.Client):
        """Should categorize technical issues."""
        tech_ticket = {
            "subject": "Router not connecting",
            "content": "My router won't connect to the network. I've tried restarting it multiple times. The lights are blinking red.",
            "customer_name": "Test Customer",
            "use_llm": False
        }
        response = client.post("/ebc-tickets/analyze", json=tech_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a valid category (may be technical, support, or other)
        valid_categories = ["technical", "support", "network", "connectivity", "other", "inquiry"]
        assert data["category"] in valid_categories
        
    def test_analyze_ticket_keywords_extracted(self, client: httpx.Client, sample_ticket):
        """Should extract keywords from ticket."""
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "keywords" in data
        # Keywords should be a list
        keywords = data["keywords"]
        if isinstance(keywords, str):
            keywords = eval(keywords) if keywords.startswith("[") else []
        assert isinstance(keywords, list)
        
    def test_analyze_ticket_urgency_indicators(self, client: httpx.Client, angry_ticket):
        """Should detect urgency indicators."""
        response = client.post("/ebc-tickets/analyze", json=angry_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "urgency_indicators" in data
        # Should have urgency indicators for angry ticket
        indicators = data["urgency_indicators"]
        assert len(indicators) > 0 or data["escalation_needed"] == True
        
    def test_analyze_ticket_escalation_needed(self, client: httpx.Client, angry_ticket):
        """Should flag tickets needing escalation."""
        response = client.post("/ebc-tickets/analyze", json=angry_ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "escalation_needed" in data
        # Angry ticket should need escalation
        assert data["escalation_needed"] == True
        
    def test_analyze_ticket_with_channel(self, client: httpx.Client):
        """Should accept different channels."""
        channels = ["email", "phone", "chat", "social"]
        
        for channel in channels:
            ticket = {
                "subject": "Test ticket",
                "content": "This is a test ticket.",
                "channel": channel,
                "use_llm": False
            }
            response = client.post("/ebc-tickets/analyze", json=ticket)
            assert response.status_code == 200
            
    def test_analyze_ticket_save_option(self, client: httpx.Client):
        """Should save ticket when save_ticket=True."""
        ticket = {
            "subject": "Ticket to save",
            "content": "This ticket should be saved to the database.",
            "customer_name": "Save Test",
            "save_ticket": True,
            "use_llm": False
        }
        response = client.post("/ebc-tickets/analyze", json=ticket)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have a ticket_id
        ticket_id = data.get("ticket_id")
        assert ticket_id is not None
        
        # Verify ticket was saved by fetching it
        get_response = client.get(f"/ebc-tickets/tickets/{ticket_id}")
        assert get_response.status_code == 200
        
    def test_analyze_ticket_empty_content(self, client: httpx.Client):
        """Should handle empty content."""
        ticket = {
            "subject": "Empty content test",
            "content": "",
            "use_llm": False
        }
        response = client.post("/ebc-tickets/analyze", json=ticket)
        
        # Should either work or return validation error
        assert response.status_code in [200, 400, 422]
        
    def test_analyze_ticket_missing_subject(self, client: httpx.Client):
        """Should handle missing subject field."""
        ticket = {
            "content": "Some content without subject"
        }
        response = client.post("/ebc-tickets/analyze", json=ticket)
        
        # API may accept missing subject or validate it
        assert response.status_code in [200, 422]


# ============================================
# TEST: BULK ANALYZE (POST /ebc-tickets/analyze/bulk)
# ============================================

class TestBulkAnalyze:
    """Tests for POST /api/v1/ebc-tickets/analyze/bulk"""
    
    def test_bulk_analyze_multiple_tickets(self, client: httpx.Client):
        """Should analyze multiple tickets at once."""
        tickets = [
            {"subject": "Issue 1", "content": "First ticket content"},
            {"subject": "Issue 2", "content": "Second ticket content"},
            {"subject": "Issue 3", "content": "Third ticket content"}
        ]
        response = client.post("/ebc-tickets/analyze/bulk", json={"tickets": tickets})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return results for all tickets
        assert "results" in data
        assert len(data["results"]) == 3
        
    def test_bulk_analyze_empty_list(self, client: httpx.Client):
        """Should handle empty ticket list."""
        response = client.post("/ebc-tickets/analyze/bulk", json={"tickets": []})
        
        # Should either return empty results or validation error
        assert response.status_code in [200, 400, 422]
        
    def test_bulk_analyze_mixed_sentiments(self, client: httpx.Client):
        """Should correctly analyze mixed sentiment tickets."""
        tickets = [
            {"subject": "Great!", "content": "Amazing service, thank you so much!"},
            {"subject": "Terrible!", "content": "Worst service ever, I'm so angry!"},
            {"subject": "Question", "content": "How do I reset my password?"}
        ]
        response = client.post("/ebc-tickets/analyze/bulk", json={"tickets": tickets})
        
        assert response.status_code == 200
        data = response.json()
        
        results = data.get("results", [])
        sentiments = [r.get("sentiment") for r in results]
        
        # Should have different sentiments
        assert "positive" in sentiments or any(r.get("sentiment_score", 0) > 0 for r in results)
        assert "negative" in sentiments or any(r.get("sentiment_score", 0) < 0 for r in results)


# ============================================
# TEST: LIST TICKETS (GET /ebc-tickets/tickets)
# ============================================

class TestListTickets:
    """Tests for GET /api/v1/ebc-tickets/tickets"""
    
    def test_list_tickets_success(self, client: httpx.Client):
        """Should return list of tickets."""
        response = client.get("/ebc-tickets/tickets")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tickets" in data
        assert isinstance(data["tickets"], list)
        
    def test_list_tickets_structure(self, client: httpx.Client):
        """Each ticket should have required fields."""
        response = client.get("/ebc-tickets/tickets")
        data = response.json()
        
        if len(data["tickets"]) > 0:
            ticket = data["tickets"][0]
            assert "id" in ticket
            assert "subject" in ticket
            assert "content" in ticket
            assert "status" in ticket
            assert "sentiment" in ticket
            assert "priority" in ticket
            
    def test_list_tickets_pagination(self, client: httpx.Client):
        """Should support pagination."""
        response = client.get("/ebc-tickets/tickets", params={"limit": 2, "offset": 0})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return at most 2 tickets
        assert len(data["tickets"]) <= 2
        
    def test_list_tickets_filter_by_status(self, client: httpx.Client):
        """Should filter by status."""
        response = client.get("/ebc-tickets/tickets", params={"status": "open"})
        
        assert response.status_code == 200
        data = response.json()
        
        # All tickets should have status=open
        for ticket in data["tickets"]:
            assert ticket["status"] == "open"
            
    def test_list_tickets_filter_by_priority(self, client: httpx.Client):
        """Should filter by priority."""
        response = client.get("/ebc-tickets/tickets", params={"priority": "high"})
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned tickets should have high priority
        for ticket in data["tickets"]:
            assert ticket["priority"] == "high"
            
    def test_list_tickets_filter_by_sentiment(self, client: httpx.Client):
        """Should filter by sentiment."""
        response = client.get("/ebc-tickets/tickets", params={"sentiment": "negative"})
        
        assert response.status_code == 200


# ============================================
# TEST: GET TICKET (GET /ebc-tickets/tickets/{id})
# ============================================

class TestGetTicket:
    """Tests for GET /api/v1/ebc-tickets/tickets/{ticket_id}"""
    
    def test_get_ticket_success(self, client: httpx.Client, created_ticket_id):
        """Should get specific ticket by ID."""
        if not created_ticket_id:
            pytest.skip("No ticket created")
            
        response = client.get(f"/ebc-tickets/tickets/{created_ticket_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == created_ticket_id
        
    def test_get_ticket_not_found(self, client: httpx.Client):
        """Should return 404 for non-existent ticket."""
        response = client.get("/ebc-tickets/tickets/nonexistent_ticket_xyz")
        
        assert response.status_code == 404
        
    def test_get_ticket_includes_all_fields(self, client: httpx.Client, created_ticket_id):
        """Returned ticket should have all fields."""
        if not created_ticket_id:
            pytest.skip("No ticket created")
            
        response = client.get(f"/ebc-tickets/tickets/{created_ticket_id}")
        data = response.json()
        
        expected_fields = ["id", "subject", "content", "status", "sentiment", 
                         "sentiment_score", "priority", "category", "created_at"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


# ============================================
# TEST: UPDATE TICKET (PUT /ebc-tickets/tickets/{id})
# ============================================

class TestUpdateTicket:
    """Tests for PUT /api/v1/ebc-tickets/tickets/{ticket_id}"""
    
    def test_update_ticket_status(self, client: httpx.Client, created_ticket_id):
        """Should update ticket status."""
        if not created_ticket_id:
            pytest.skip("No ticket created")
            
        response = client.put(f"/ebc-tickets/tickets/{created_ticket_id}", json={
            "status": "in_progress"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Response may contain message or updated ticket
        assert "message" in data or "ticket_id" in data
        
        # Verify the update by fetching the ticket
        get_response = client.get(f"/ebc-tickets/tickets/{created_ticket_id}")
        if get_response.status_code == 200:
            ticket_data = get_response.json()
            assert ticket_data["status"] == "in_progress"
        
    def test_update_ticket_assign_agent(self, client: httpx.Client, created_ticket_id):
        """Should assign agent to ticket."""
        if not created_ticket_id:
            pytest.skip("No ticket created")
            
        response = client.put(f"/ebc-tickets/tickets/{created_ticket_id}", json={
            "agent_id": "agent_123"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Response may contain message or updated ticket
        assert "message" in data or "ticket_id" in data
        
        # Verify the update by fetching the ticket
        get_response = client.get(f"/ebc-tickets/tickets/{created_ticket_id}")
        if get_response.status_code == 200:
            ticket_data = get_response.json()
            assert ticket_data.get("agent_id") == "agent_123"
        
    def test_update_ticket_resolution_notes(self, client: httpx.Client, created_ticket_id):
        """Should add resolution notes."""
        if not created_ticket_id:
            pytest.skip("No ticket created")
            
        response = client.put(f"/ebc-tickets/tickets/{created_ticket_id}", json={
            "status": "resolved",
            "resolution_notes": "Issue resolved by restarting the router."
        })
        
        assert response.status_code == 200
        
    def test_update_ticket_not_found(self, client: httpx.Client):
        """Should return 404 for non-existent ticket."""
        response = client.put("/ebc-tickets/tickets/nonexistent_xyz", json={
            "status": "closed"
        })
        
        assert response.status_code == 404


# ============================================
# TEST: DASHBOARD (GET /ebc-tickets/dashboard)
# ============================================

class TestDashboard:
    """Tests for GET /api/v1/ebc-tickets/dashboard"""
    
    def test_dashboard_success(self, client: httpx.Client):
        """Should return dashboard data."""
        response = client.get("/ebc-tickets/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "analytics" in data or "total_tickets" in data
        
    def test_dashboard_analytics_structure(self, client: httpx.Client):
        """Dashboard should have analytics breakdown."""
        response = client.get("/ebc-tickets/dashboard")
        data = response.json()
        
        analytics = data.get("analytics", data)
        
        # Should have breakdowns
        assert "by_sentiment" in analytics or "total_tickets" in analytics
        
    def test_dashboard_sentiment_breakdown(self, client: httpx.Client):
        """Should have sentiment distribution."""
        response = client.get("/ebc-tickets/dashboard")
        data = response.json()
        
        analytics = data.get("analytics", data)
        
        if "by_sentiment" in analytics:
            sentiment = analytics["by_sentiment"]
            expected_sentiments = ["positive", "negative", "neutral"]
            for s in expected_sentiments:
                assert s in sentiment
                
    def test_dashboard_priority_breakdown(self, client: httpx.Client):
        """Should have priority distribution."""
        response = client.get("/ebc-tickets/dashboard")
        data = response.json()
        
        analytics = data.get("analytics", data)
        
        if "by_priority" in analytics:
            priority = analytics["by_priority"]
            expected_priorities = ["critical", "high", "medium", "low"]
            for p in expected_priorities:
                assert p in priority


# ============================================
# TEST: ANALYTICS (GET /ebc-tickets/analytics)
# ============================================

class TestAnalytics:
    """Tests for GET /api/v1/ebc-tickets/analytics"""
    
    def test_analytics_success(self, client: httpx.Client):
        """Should return analytics data."""
        response = client.get("/ebc-tickets/analytics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have some analytics data
        assert isinstance(data, dict)
        
    def test_analytics_time_filter(self, client: httpx.Client):
        """Should filter by time period."""
        response = client.get("/ebc-tickets/analytics", params={"period": "day"})
        
        assert response.status_code == 200


# ============================================
# TEST: SEED DEMO DATA (POST /ebc-tickets/demo/seed)
# ============================================

class TestSeedDemo:
    """Tests for POST /api/v1/ebc-tickets/demo/seed"""
    
    def test_seed_demo_data(self, client: httpx.Client):
        """Should seed demo data."""
        response = client.post("/ebc-tickets/demo/seed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data or "seeded" in data or "count" in str(data)


# ============================================
# TEST: ERROR HANDLING
# ============================================

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_json(self, client: httpx.Client):
        """Should handle invalid JSON."""
        response = client.post(
            "/ebc-tickets/analyze",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        
    def test_missing_required_fields(self, client: httpx.Client):
        """Should validate required fields."""
        response = client.post("/ebc-tickets/analyze", json={})
        
        assert response.status_code == 422
        
    def test_wrong_http_method(self, client: httpx.Client):
        """GET on POST endpoint should fail."""
        response = client.get("/ebc-tickets/analyze")
        
        assert response.status_code == 405


# ============================================
# TEST: PERFORMANCE
# ============================================

class TestPerformance:
    """Performance tests."""
    
    def test_analyze_response_time(self, client: httpx.Client, sample_ticket):
        """Analyze should respond within reasonable time."""
        start = time.time()
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s"
        
    def test_list_response_time(self, client: httpx.Client):
        """List should respond quickly."""
        start = time.time()
        response = client.get("/ebc-tickets/tickets")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"
        
    def test_dashboard_response_time(self, client: httpx.Client):
        """Dashboard should respond quickly."""
        start = time.time()
        response = client.get("/ebc-tickets/dashboard")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"


# ============================================
# TEST: RESPONSE STRUCTURE
# ============================================

class TestResponseStructure:
    """Test response structure consistency."""
    
    def test_analyze_response_structure(self, client: httpx.Client, sample_ticket):
        """Analyze response should have consistent structure."""
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        data = response.json()
        
        expected_fields = [
            "ticket_id",
            "sentiment",
            "sentiment_score",
            "priority",
            "category",
            "keywords",
            "escalation_needed"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
            
    def test_sentiment_score_range(self, client: httpx.Client, sample_ticket):
        """Sentiment score should be between -1 and 1."""
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        data = response.json()
        
        score = data["sentiment_score"]
        assert -1 <= score <= 1, f"Score out of range: {score}"
        
    def test_priority_values(self, client: httpx.Client, sample_ticket):
        """Priority should be valid value."""
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        data = response.json()
        
        valid_priorities = ["low", "medium", "high", "critical"]
        assert data["priority"] in valid_priorities
        
    def test_sentiment_values(self, client: httpx.Client, sample_ticket):
        """Sentiment should be valid value."""
        response = client.post("/ebc-tickets/analyze", json=sample_ticket)
        data = response.json()
        
        valid_sentiments = ["positive", "negative", "neutral", "mixed"]
        assert data["sentiment"] in valid_sentiments


# ============================================
# RUN TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


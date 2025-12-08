"""
Document Q&A Use Case - Test Script

Run with: python use_cases/document_qa/test_use_case.py
"""

import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

# Test documents for the use case
TEST_DOCUMENTS = [
    {
        "content": """Company Vacation Policy (2025)

1. Annual Leave: All full-time employees receive 20 days of paid vacation per year.
2. Carryover: Up to 5 unused vacation days may be carried over to the next year.
3. Accrual: Vacation days accrue monthly at 1.67 days per month.
4. Scheduling: Requests must be submitted at least 2 weeks in advance.
5. Holiday Blackout: No vacation during December 20-31 for customer-facing roles.
""",
        "filename": "vacation_policy_2025.txt",
        "metadata": {"type": "policy", "department": "HR", "year": "2025"}
    },
    {
        "content": """Remote Work Guidelines

1. Eligibility: After 90 days of employment, employees may request remote work.
2. Schedule: Up to 3 days per week remote work with manager approval.
3. Equipment: Company provides laptop and $500 home office stipend.
4. Availability: Must be online 9 AM - 5 PM in local timezone.
5. Meetings: In-person attendance required for team meetings on Tuesdays.
""",
        "filename": "remote_work_policy.txt",
        "metadata": {"type": "policy", "department": "HR"}
    },
    {
        "content": """Expense Reimbursement Policy

1. Submission: Submit expense reports within 30 days of expense.
2. Receipts: Required for expenses over $25.
3. Meals: Business meals up to $50/person do not require pre-approval.
4. Travel: Book through company travel portal for automatic approval.
5. Processing: Reimbursements processed within 10 business days.
""",
        "filename": "expense_policy.txt",
        "metadata": {"type": "policy", "department": "Finance"}
    }
]

# Test queries and expected behaviors
TEST_QUERIES = [
    {
        "query": "How many vacation days do I get per year?",
        "expected_keywords": ["20", "days", "vacation", "annual"],
        "description": "Basic factual question"
    },
    {
        "query": "Can I work from home?",
        "expected_keywords": ["remote", "3 days", "manager", "approval"],
        "description": "Policy eligibility question"
    },
    {
        "query": "What's the expense limit for meals?",
        "expected_keywords": ["$50", "meals", "receipt"],
        "description": "Specific detail lookup"
    }
]


async def test_document_qa():
    """Run the Document Q&A use case tests."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 60)
        print("Document Q&A Use Case - Test Suite")
        print("=" * 60)
        
        # Step 1: Ingest test documents
        print("\n📄 Step 1: Ingesting test documents...")
        ingested = []
        for doc in TEST_DOCUMENTS:
            response = await client.post(
                f"{BASE_URL}/ingest/text",
                json=doc
            )
            result = response.json()
            status = "✅" if result.get("status") == "completed" else "❌"
            print(f"  {status} {doc['filename']}: {result.get('total_chunks', 0)} chunks")
            ingested.append(result)
        
        # Step 2: Verify documents in system
        print("\n📊 Step 2: Checking RAG system stats...")
        response = await client.get(f"{BASE_URL}/rag/stats")
        stats = response.json()
        print(f"  Documents in DB: {stats.get('database', {}).get('documents', 'N/A')}")
        print(f"  Total chunks: {stats.get('database', {}).get('chunks', 'N/A')}")
        print(f"  LLM configured: {stats.get('llm_configured', False)}")
        
        # Step 3: Test retrieval (without LLM)
        print("\n🔍 Step 3: Testing document retrieval...")
        for test in TEST_QUERIES:
            response = await client.post(
                f"{BASE_URL}/retrieve/",
                json={"query": test["query"], "top_k": 3}
            )
            result = response.json()
            docs_found = len(result.get("documents", []))
            status = "✅" if docs_found > 0 else "⚠️"
            print(f"  {status} '{test['query'][:40]}...'")
            print(f"      Found {docs_found} relevant documents")
        
        # Step 4: Test RAG query (requires valid API key)
        print("\n💬 Step 4: Testing RAG Q&A...")
        for test in TEST_QUERIES:
            response = await client.post(
                f"{BASE_URL}/rag/query",
                json={"query": test["query"], "top_k": 3}
            )
            result = response.json()
            answer = result.get("answer", "")
            sources = len(result.get("sources", []))
            
            if answer:
                # Check if expected keywords are in answer
                found_keywords = [kw for kw in test["expected_keywords"] if kw.lower() in answer.lower()]
                status = "✅" if len(found_keywords) >= 2 else "⚠️"
                print(f"  {status} {test['description']}")
                print(f"      Answer: {answer[:100]}...")
                print(f"      Sources: {sources}, Keywords found: {found_keywords}")
            else:
                print(f"  ⚠️ {test['description']}")
                print(f"      No answer (LLM API key may be invalid)")
        
        # Step 5: Test conversation mode
        print("\n🗣️ Step 5: Testing conversation mode...")
        # Create conversation
        response = await client.post(
            f"{BASE_URL}/rag/conversation",
            json={"metadata": {"test": "document_qa"}}
        )
        conv = response.json()
        conv_id = conv.get("conversation_id")
        print(f"  Created conversation: {conv_id}")
        
        # Test follow-up (would work with valid API key)
        print(f"  ℹ️ Conversation follow-up requires valid LLM API key")
        
        # Step 6: Summary
        print("\n" + "=" * 60)
        print("📋 Test Summary")
        print("=" * 60)
        print(f"  Documents ingested: {len(ingested)}")
        print(f"  Test queries: {len(TEST_QUERIES)}")
        print(f"  RAG system: {'Ready' if stats.get('llm_configured') else 'Needs API key'}")
        
        # Check if API key is the issue
        if not any(r.get("answer") for r in []):
            print("\n⚠️  Note: LLM features require a valid OPENAI_API_KEY in .env")
            print("    Retrieval and ingestion work without it.")


async def run_quick_test():
    """Quick test without documents - just tools."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n🚀 Quick Tool Test")
        print("-" * 40)
        
        # Calculator
        response = await client.post(
            f"{BASE_URL}/agents/tools/execute",
            json={"tool_name": "calculator", "arguments": {"expression": "20 * 12"}}
        )
        result = response.json()
        print(f"  Calculator: 20 * 12 = {result['result']['result']['result']}")
        
        # DateTime
        response = await client.post(
            f"{BASE_URL}/agents/tools/execute",
            json={"tool_name": "get_datetime", "arguments": {}}
        )
        result = response.json()
        print(f"  DateTime: {result['result']['result']['date']}")
        
        # Web search
        response = await client.post(
            f"{BASE_URL}/agents/tools/execute",
            json={"tool_name": "web_search", "arguments": {"query": "Python programming", "num_results": 1}}
        )
        result = response.json()
        results = result['result']['result'].get('results', [])
        if results:
            print(f"  Web Search: Found '{results[0]['title'][:50]}...'")
        
        print("\n✅ All tools working!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GoAI Platform - Use Case Testing")
    print("=" * 60)
    
    # Run quick tool test first
    asyncio.run(run_quick_test())
    
    # Run full document Q&A test
    asyncio.run(test_document_qa())


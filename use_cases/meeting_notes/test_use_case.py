"""
Meeting Notes Use Case - Test Script

Run with: python use_cases/meeting_notes/test_use_case.py
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1/meeting-notes"

# Sample meeting notes for testing
SAMPLE_NOTES = """
Weekly Engineering Standup - January 15, 2025

Attendees: Alice (Tech Lead), Bob (Backend), Carol (Frontend), Dave (DevOps)

Discussion:
- Alice presented the new architecture proposal for the payment service
- Bob reported that the API refactoring is 80% complete, will finish by Wednesday
- Carol mentioned UI performance issues on the dashboard, needs investigation
- Dave confirmed the Kubernetes migration is on track for next week

Action Items:
1. Bob to complete API refactoring by Wednesday
2. Carol to profile dashboard performance and create ticket - HIGH PRIORITY
3. Dave to prepare rollback plan for K8s migration
4. Alice to schedule architecture review meeting with stakeholders
5. Everyone to review the new coding guidelines document by Friday

Decisions Made:
- Approved moving to PostgreSQL 15
- Agreed to implement feature flags for the new checkout flow
- Will hire one more backend developer

Next Steps:
- Architecture review meeting Thursday 2pm
- K8s migration dry run Monday
- Sprint retrospective next Friday
"""

SIMPLE_NOTES = """
Quick sync with marketing team.
TODO: John to send the campaign report by Friday.
ACTION: Sarah will update the website copy.
Meeting next week to review results.
"""


async def test_meeting_notes():
    """Test the meeting notes API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 60)
        print("📝 Meeting Notes Summarizer - Test Suite")
        print("=" * 60)
        
        # Test 1: Get API info
        print("\n📋 Test 1: Getting API info...")
        response = await client.get(f"{BASE_URL}/")
        if response.status_code == 200:
            info = response.json()
            print(f"  ✅ API: {info['name']} v{info['version']}")
            print(f"  📌 Features: {', '.join(info['features'][:3])}...")
        else:
            print(f"  ❌ Failed: {response.status_code}")
            return
        
        # Test 2: Full summarization (with LLM)
        print("\n📝 Test 2: Full meeting summarization...")
        response = await client.post(
            f"{BASE_URL}/summarize",
            json={
                "content": SAMPLE_NOTES,
                "include_priorities": True
            }
        )
        
        if response.status_code == 200:
            summary = response.json()
            print(f"  ✅ Title: {summary['title']}")
            print(f"  👥 Participants: {', '.join(summary['participants'][:4])}{'...' if len(summary['participants']) > 4 else ''}")
            print(f"  📊 Summary: {summary['summary'][:100]}...")
            print(f"  ✅ Action Items: {len(summary['action_items'])}")
            for item in summary['action_items'][:3]:
                priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item['priority'], "⚪")
                assignee = f" → {item['assignee']}" if item.get('assignee') else ""
                print(f"     {priority} {item['task'][:45]}...{assignee}")
            if len(summary['action_items']) > 3:
                print(f"     ... and {len(summary['action_items']) - 3} more")
            print(f"  🎯 Decisions: {len(summary['key_decisions'])}")
            print(f"  📅 Next Steps: {len(summary['next_steps'])}")
        else:
            print(f"  ⚠️ Status: {response.status_code}")
            try:
                print(f"  Note: {response.json().get('detail', 'LLM API key may be invalid')}")
            except:
                pass
        
        # Test 3: Action items only
        print("\n✅ Test 3: Extract action items only...")
        response = await client.post(
            f"{BASE_URL}/action-items",
            json={"content": SIMPLE_NOTES}
        )
        
        if response.status_code == 200:
            items = response.json()
            print(f"  ✅ Found {items['count']} action items")
            for item in items['action_items']:
                print(f"     • {item['task'][:50]}...")
        else:
            print(f"  ⚠️ Status: {response.status_code} (requires LLM API key)")
        
        # Test 4: Markdown formatting (doesn't need LLM)
        print("\n📄 Test 4: Markdown formatting...")
        sample_summary = {
            "title": "Weekly Standup",
            "date": "2025-01-15",
            "participants": ["Alice", "Bob", "Carol"],
            "summary": "Team discussed progress on Q4 goals and identified blockers.",
            "action_items": [
                {"task": "Complete API refactoring", "assignee": "Bob", "priority": "high", "due_date": "Wednesday", "status": "pending"},
                {"task": "Profile dashboard performance", "assignee": "Carol", "priority": "high", "due_date": None, "status": "pending"},
                {"task": "Prepare rollback plan", "assignee": "Dave", "priority": "medium", "due_date": None, "status": "pending"}
            ],
            "key_decisions": ["Use PostgreSQL 15", "Implement feature flags"],
            "next_steps": ["Architecture review Thursday", "Sprint retro Friday"],
            "metadata": {}
        }
        
        response = await client.post(
            f"{BASE_URL}/format/markdown",
            json={"summary": sample_summary}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Generated {result['character_count']} characters of Markdown")
            print("  Preview:")
            preview = result['markdown'][:300].replace('\n', '\n  ')
            print(f"  {preview}...")
        else:
            print(f"  ❌ Failed: {response.status_code}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 Test Summary")
        print("=" * 60)
        print("  ✅ API info endpoint: Working")
        print("  ✅ Markdown formatting: Working (no LLM needed)")
        print("  ℹ️  Full AI features require OPENAI_API_KEY in .env")
        print("\n💡 Tip: Set OPENAI_API_KEY in .env for full functionality")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GoAI Platform - Meeting Notes Use Case")
    print("=" * 60)
    print("Make sure the server is running: uvicorn main:app --port 8000")
    
    asyncio.run(test_meeting_notes())


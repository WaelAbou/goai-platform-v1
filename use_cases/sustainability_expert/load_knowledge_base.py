#!/usr/bin/env python3
"""
Load Sustainability Knowledge Base

This script loads the sustainability knowledge base documents
into the RAG system via the API.

Run with: python use_cases/sustainability_expert/load_knowledge_base.py
"""

import asyncio
import httpx
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

# Knowledge base documents with metadata
DOCUMENTS = [
    {
        "file": "gri_305_emissions.txt",
        "title": "GRI 305: Emissions Standard 2016",
        "category": "standards",
        "source": "Global Reporting Initiative",
        "tags": ["GRI", "emissions", "scope1", "scope2", "scope3", "ghg"]
    },
    {
        "file": "tcfd_recommendations.txt", 
        "title": "TCFD Recommendations - Climate Financial Disclosures",
        "category": "standards",
        "source": "Task Force on Climate-related Financial Disclosures",
        "tags": ["TCFD", "climate-risk", "disclosure", "governance", "strategy"]
    },
    {
        "file": "sbti_guidance.txt",
        "title": "Science Based Targets Initiative (SBTi) Guide",
        "category": "standards",
        "source": "Science Based Targets initiative",
        "tags": ["SBTi", "targets", "net-zero", "paris-agreement", "1.5C"]
    },
    {
        "file": "carbon_reduction_strategies.txt",
        "title": "Carbon Reduction Strategies for Business",
        "category": "best_practices",
        "source": "Sustainability Expert Knowledge Base",
        "tags": ["reduction", "efficiency", "renewable", "offset", "strategies"]
    }
]


async def load_documents():
    """Load all knowledge base documents."""
    
    kb_dir = Path(__file__).parent / "knowledge_base"
    
    print("=" * 60)
    print("🌱 LOADING SUSTAINABILITY KNOWLEDGE BASE")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check server health
        try:
            health = await client.get(f"{BASE_URL}/health")
            if health.status_code != 200:
                print("❌ Server not running. Start with: uvicorn main:app --port 8000")
                return
        except httpx.ConnectError:
            print("❌ Cannot connect to server at", BASE_URL)
            print("   Start with: uvicorn main:app --port 8000")
            return
        
        print(f"\n📁 Knowledge base directory: {kb_dir}")
        print(f"📄 Documents to load: {len(DOCUMENTS)}\n")
        
        loaded = 0
        failed = 0
        
        for doc_info in DOCUMENTS:
            file_path = kb_dir / doc_info["file"]
            
            if not file_path.exists():
                print(f"⚠️  File not found: {doc_info['file']}")
                failed += 1
                continue
            
            content = file_path.read_text()
            
            payload = {
                "content": content,
                "title": doc_info["title"],
                "category": doc_info["category"],
                "source": doc_info["source"],
                "tags": doc_info["tags"]
            }
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/sustainability/knowledge/ingest",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {doc_info['title']}")
                    print(f"   └─ Chunks: {result.get('chunks', 'N/A')} | Category: {doc_info['category']}")
                    loaded += 1
                else:
                    print(f"❌ {doc_info['title']}: {response.text}")
                    failed += 1
                    
            except Exception as e:
                print(f"❌ {doc_info['title']}: {str(e)}")
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 SUMMARY: {loaded} loaded, {failed} failed")
        print("=" * 60)
        
        # Test the knowledge base
        if loaded > 0:
            print("\n🔍 Testing knowledge base search...")
            
            test_query = "How do I calculate Scope 1 emissions?"
            response = await client.post(
                f"{BASE_URL}/api/v1/sustainability/knowledge/search",
                params={"query": test_query, "top_k": 3}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n   Query: '{test_query}'")
                print(f"   Results: {result.get('total', 0)} documents found")
                
                for i, doc in enumerate(result.get("results", [])[:2], 1):
                    score = doc.get("score", 0)
                    title = doc.get("metadata", {}).get("filename", "Unknown")
                    print(f"   {i}. {title} (relevance: {score:.2f})")


async def main():
    """Main entry point."""
    await load_documents()


if __name__ == "__main__":
    asyncio.run(main())


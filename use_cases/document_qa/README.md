# Document Q&A Use Case

AI-powered document search and question answering system.

## Quick Start

### 1. Run the Test Script
```bash
cd goai-platform-v1
python use_cases/document_qa/test_use_case.py
```

### 2. Test via API

**Ingest a document:**
```bash
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content": "Your document text here", "filename": "doc.txt"}'
```

**Query the document:**
```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the document say about X?", "top_k": 5}'
```

### 3. Create Evaluation Dataset
```bash
curl -X POST http://localhost:8000/api/v1/evals/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Document Q&A Tests",
    "test_cases": [
      {"query": "Your question?", "expected": "Expected answer"}
    ]
  }'
```

## Files

- `intent.yaml` - Business requirements and scope
- `test_use_case.py` - Automated test script
- `README.md` - This file

## Requirements

- Server running: `uvicorn main:app --port 8000`
- For LLM features: Valid `OPENAI_API_KEY` in `.env`


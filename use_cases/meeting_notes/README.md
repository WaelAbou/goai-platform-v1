# 📝 Meeting Notes Summarizer

AI-powered meeting notes analysis and action item extraction.

## Features

- 📝 **Smart Summarization** - Generate executive summaries from raw notes
- ✅ **Action Item Extraction** - Automatically identify tasks and TODOs
- 👥 **Participant Detection** - Find who attended and their assignments
- 🎯 **Auto-Prioritization** - Rank action items by urgency/impact
- 📄 **Markdown Export** - Beautiful formatted output

---

## Quick Start

### 1. Get API Info

```bash
curl http://localhost:8000/api/v1/meeting-notes/
```

### 2. Summarize Meeting Notes

```bash
curl -X POST http://localhost:8000/api/v1/meeting-notes/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Meeting with John and Sarah on 2025-01-15\n\nDiscussed Q4 roadmap:\n- John will complete API design by Friday\n- Sarah to review security requirements\n- Decision: We will use PostgreSQL for the new service\n\nNext meeting scheduled for Monday.",
    "include_priorities": true
  }'
```

### 3. Extract Action Items Only

```bash
curl -X POST http://localhost:8000/api/v1/meeting-notes/action-items \
  -H "Content-Type: application/json" \
  -d '{"content": "TODO: Fix bug #123. ACTION: Deploy to staging by EOD."}'
```

### 4. Run Test Script

```bash
python use_cases/meeting_notes/test_use_case.py
```

---

## Example Response

```json
{
  "title": "Q4 Roadmap Discussion",
  "date": "2025-01-15",
  "participants": ["John", "Sarah"],
  "summary": "Team discussed Q4 roadmap focusing on API design and security requirements. Decision made to use PostgreSQL.",
  "action_items": [
    {
      "task": "Complete API design",
      "assignee": "John",
      "due_date": "Friday",
      "priority": "high"
    },
    {
      "task": "Review security requirements",
      "assignee": "Sarah",
      "priority": "medium"
    }
  ],
  "key_decisions": ["Use PostgreSQL for the new service"],
  "next_steps": ["Meeting scheduled for Monday"]
}
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/meeting-notes/` | GET | API info and capabilities |
| `/api/v1/meeting-notes/summarize` | POST | Full meeting summary |
| `/api/v1/meeting-notes/action-items` | POST | Extract action items only |
| `/api/v1/meeting-notes/format/markdown` | POST | Convert summary to Markdown |

---

## Requirements

- Server running: `uvicorn main:app --port 8000`
- For AI features: Valid `OPENAI_API_KEY` in `.env`

---

## Files

```
use_cases/meeting_notes/
├── README.md           # This file
├── test_use_case.py    # Automated tests
└── intent.yaml         # Business requirements (optional)
```


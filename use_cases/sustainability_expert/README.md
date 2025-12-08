# 🌱 Sustainability Expert Bot

An AI-powered sustainability advisor that helps organizations and individuals make environmentally conscious decisions.

## Overview

The Sustainability Expert Bot provides:
- **Carbon Footprint Calculation** - Estimate emissions from activities, products, and operations
- **ESG Analysis** - Environmental, Social, and Governance scoring and recommendations
- **Sustainability Best Practices** - Industry-specific guidance and standards
- **Regulatory Compliance** - Help navigate environmental regulations (GRI, TCFD, CDP)
- **Green Alternatives** - Suggest sustainable alternatives to current practices

## Quick Start

### 1. Test via API

**Ask a sustainability question:**
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How can my company reduce its carbon footprint?",
    "context": {"industry": "manufacturing", "company_size": "medium"}
  }'
```

**Calculate carbon footprint:**
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/carbon-footprint \
  -H "Content-Type: application/json" \
  -d '{
    "activity": "business_travel",
    "details": {
      "flights_per_year": 20,
      "average_distance_km": 1500,
      "class": "economy"
    }
  }'
```

**Get ESG score:**
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/esg-score \
  -H "Content-Type: application/json" \
  -d '{
    "company_data": {
      "renewable_energy_percent": 30,
      "waste_recycled_percent": 45,
      "employee_diversity_score": 7,
      "board_independence_percent": 60
    }
  }'
```

### 2. Run Test Script
```bash
cd goai-platform-v1
python use_cases/sustainability_expert/test_use_case.py
```

## Features

### 🔢 Carbon Calculator
Calculate emissions for various activities:
- Transportation (flights, vehicles, shipping)
- Energy consumption (electricity, heating, cooling)
- Business operations (data centers, offices)
- Supply chain (manufacturing, logistics)

### 📊 ESG Scoring
Evaluate sustainability across three dimensions:
- **Environmental** (E): Carbon emissions, waste, water usage, biodiversity
- **Social** (S): Employee welfare, community impact, diversity, human rights
- **Governance** (G): Board structure, ethics, transparency, risk management

### 📚 Knowledge Base
Built-in expertise on:
- UN Sustainable Development Goals (SDGs)
- GRI Standards (Global Reporting Initiative)
- TCFD Recommendations (Task Force on Climate-related Financial Disclosures)
- Science Based Targets initiative (SBTi)
- Carbon Disclosure Project (CDP)
- ISO 14001 Environmental Management

### 💡 Recommendations Engine
Industry-specific sustainability advice:
- Technology & IT
- Manufacturing
- Retail & Consumer Goods
- Finance & Banking
- Healthcare
- Construction & Real Estate

## Platform Integration

This use case leverages:

| Component | Usage |
|-----------|-------|
| **LLM Router** | Powers conversational interface |
| **RAG Engine** | Retrieves relevant sustainability standards |
| **Agent Tools** | Carbon calculator, ESG scorer, recommendations |
| **Memory** | Maintains conversation context |
| **Guardrails** | Ensures factual, responsible advice |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sustainability/chat` | POST | Conversational sustainability advice |
| `/api/v1/sustainability/carbon-footprint` | POST | Calculate carbon emissions |
| `/api/v1/sustainability/esg-score` | POST | Calculate ESG score |
| `/api/v1/sustainability/recommendations` | POST | Get industry recommendations |
| `/api/v1/sustainability/standards` | GET | List supported standards |
| `/api/v1/sustainability/sdgs` | GET | UN Sustainable Development Goals info |

## Example Conversations

**User:** "What's the carbon footprint of a round-trip flight from NYC to London?"

**Bot:** "A round-trip economy flight from NYC to London (approximately 11,200 km total) produces roughly **1.6 tonnes of CO2e** per passenger. This is equivalent to:
- 🚗 Driving 6,400 km in an average car
- 💡 Powering a home for 3 months
- 🌳 What 80 trees absorb in a year

**To offset this:** Consider investing in verified carbon credits (~$25-50) or switching to video conferencing for some meetings."

---

**User:** "How does my company compare on ESG?"

**Bot:** "Based on your data, here's your ESG breakdown:

| Dimension | Score | Rating |
|-----------|-------|--------|
| Environmental | 62/100 | ⭐⭐⭐ Good |
| Social | 71/100 | ⭐⭐⭐⭐ Very Good |
| Governance | 55/100 | ⭐⭐ Fair |
| **Overall** | **63/100** | ⭐⭐⭐ Good |

**Top Recommendations:**
1. 🔋 Increase renewable energy from 30% to 50%
2. ♻️ Implement circular economy practices
3. 📋 Add independent board members"

## Requirements

- Server running: `uvicorn main:app --port 8000`
- For LLM features: Valid `OPENAI_API_KEY` in `.env`
- Optional: Sustainability knowledge base documents in RAG

## Files

```
use_cases/sustainability_expert/
├── README.md           # This file
├── intent.yaml         # Business requirements
├── engine.py           # Core sustainability logic
└── test_use_case.py    # Automated tests
```

## Future Enhancements

- [ ] Supply chain emissions tracking (Scope 3)
- [ ] Life Cycle Assessment (LCA) calculator
- [ ] Sustainability report generator
- [ ] Real-time carbon market prices
- [ ] Integration with IoT sensors for energy monitoring
- [ ] Benchmarking against industry peers


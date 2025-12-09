# Demo Data for Sustainability Expert Bot

This folder contains sample company data for demonstrating the Sustainability Expert Bot.

## Files

| File | Description |
|------|-------------|
| `xyz_corporation.json` | Complete sustainability profile for fictional XYZ Corp |

## XYZ Corporation Profile

A fictional mid-sized technology company used to demonstrate all features:

```
Company:        XYZ Corporation (SaaS)
Employees:      500
Revenue:        $75M
Locations:      San Francisco (HQ), Austin, London
Total CO2e:     1,146 tonnes/year
ESG Rating:     A (74.5/100)
```

## Using Demo Data

### Load and Display Summary

```python
import json

with open('demo_data/xyz_corporation.json') as f:
    company = json.load(f)

print(f"Company: {company['company']['name']}")
print(f"Total Emissions: {company['carbon_footprint']['total_co2e_tonnes']} tonnes")
print(f"ESG Rating: {company['esg_score']['rating']}")
```

### Test with API

```bash
# Use the company's ESG data to calculate score
curl -X POST http://localhost:8000/api/v1/sustainability/esg-score \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "environmental_data": {
    "renewable_energy_percent": 55,
    "waste_recycled_percent": 72,
    "carbon_intensity": 15
  },
  "social_data": {
    "employee_satisfaction": 82,
    "diversity_score": 71
  },
  "governance_data": {
    "board_independence_percent": 67,
    "transparency_score": 82
  },
  "industry": "technology"
}
EOF
```

## Data Structure

The JSON files contain:

```
{
  "company": {                    # Company profile
    "name", "industry", "employees", "locations"
  },
  "carbon_footprint": {           # Emissions data
    "total_co2e_kg", "breakdown": { ... }
  },
  "esg_score": {                  # ESG assessment
    "overall_score", "rating", "environmental", "social", "governance"
  },
  "reduction_plan": {             # Improvement roadmap
    "initiatives": [...], "projected_results"
  },
  "net_zero_pathway": {           # Long-term targets
    "milestones": [...], "target_year"
  },
  "metadata": {                   # Data provenance
    "created_at", "data_sources", "methodology"
  }
}
```

## Adding New Demo Companies

Create a new JSON file following the same structure. Required fields:

1. **company** - Basic info
2. **carbon_footprint** - At least `total_co2e_kg`
3. **esg_score** - At least `overall_score`

Optional but recommended:
- Detailed breakdown by category
- Reduction plan with initiatives
- Net zero pathway milestones


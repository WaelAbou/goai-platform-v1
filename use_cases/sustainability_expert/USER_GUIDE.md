# 🌱 Sustainability Expert - User Guide

## Complete Workflow: From Data Entry to ESG Report

This guide walks you through setting up your company profile and generating your first ESG report.

---

## 📋 Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    YOUR ESG REPORTING JOURNEY                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1          Step 2           Step 3          Step 4            │
│  ┌──────┐       ┌──────┐        ┌──────┐        ┌──────┐           │
│  │Create│  ──►  │ Add  │  ──►   │Record│  ──►   │ Get  │           │
│  │Company│      │Data  │        │ ESG  │        │Report│           │
│  └──────┘       └──────┘        └──────┘        └──────┘           │
│                                                                      │
│  Profile &      Carbon          ESG Score       Dashboard &         │
│  Locations      Footprint       Assessment      Benchmarks          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Create Your Company Profile

### 1.1 Register Your Company

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "industry": "manufacturing",
    "sub_industry": "electronics",
    "employees": 1200,
    "revenue_usd": 150000000,
    "headquarters": "Detroit, MI",
    "description": "Consumer electronics manufacturer"
  }'
```

**Response:**
```json
{
  "status": "success",
  "company_id": "abc123-def456",
  "message": "Company 'Acme Corporation' created successfully"
}
```

> 📝 **Save your `company_id`** - you'll need it for all subsequent operations.

### 1.2 Add Your Locations/Facilities

Add each office, factory, or warehouse:

```bash
# Add headquarters
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/locations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Detroit Headquarters",
    "location_type": "headquarters",
    "country": "USA",
    "city": "Detroit",
    "employees": 500,
    "sqft": 100000,
    "renewable_energy_percent": 25
  }'

# Add manufacturing plant
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/locations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Austin Manufacturing",
    "location_type": "factory",
    "country": "USA", 
    "city": "Austin",
    "employees": 600,
    "sqft": 250000,
    "renewable_energy_percent": 0
  }'

# Add distribution center
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/locations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chicago Distribution",
    "location_type": "warehouse",
    "country": "USA",
    "city": "Chicago",
    "employees": 100,
    "sqft": 75000,
    "renewable_energy_percent": 50
  }'
```

---

## Step 2: Calculate Your Carbon Footprint

### 2.1 Gather Your Data

You'll need data for each emission category:

| Category | Data Needed |
|----------|-------------|
| **Scope 1** (Direct) | Natural gas usage, company vehicles, refrigerants |
| **Scope 2** (Energy) | Electricity bills (kWh) per location |
| **Scope 3** (Indirect) | Business travel, commuting, shipping |

### 2.2 Calculate Individual Emissions

#### Business Travel (Flights)
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/flight-emissions \
  -H "Content-Type: application/json" \
  -d '{
    "distance_km": 3500,
    "travel_class": "economy",
    "round_trip": true,
    "passengers": 50
  }'
```

**Response:**
```json
{
  "emissions": {
    "co2e_kg": 27300,
    "co2e_tonnes": 27.3,
    "scope": 3
  },
  "equivalents": {
    "trees_needed": 1365,
    "car_km": 109200,
    "home_energy_months": 5.46
  }
}
```

#### Office Energy
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/electricity-emissions \
  -H "Content-Type: application/json" \
  -d '{
    "kwh": 500000,
    "grid": "us_avg",
    "renewable_percent": 25
  }'
```

#### Natural Gas (Heating)
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/natural-gas-emissions \
  -H "Content-Type: application/json" \
  -d '{
    "therms": 15000
  }'
```

#### Company Vehicles
```bash
curl -X POST http://localhost:8000/api/v1/sustainability/vehicle-emissions \
  -H "Content-Type: application/json" \
  -d '{
    "distance_km": 500000,
    "vehicle_type": "van_diesel"
  }'
```

### 2.3 Record Your Annual Footprint

Once you've calculated all categories, record your total:

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/footprints \
  -H "Content-Type: application/json" \
  -d '{
    "year": 2024,
    "scope_1_kg": 156000,
    "scope_2_kg": 312000,
    "scope_3_kg": 890000,
    "methodology": "GHG Protocol",
    "verification_status": "self-reported",
    "breakdown": {
      "business_travel": {"co2e_kg": 340000, "percent": 25.0, "scope": 3},
      "employee_commuting": {"co2e_kg": 280000, "percent": 20.6, "scope": 3},
      "office_energy": {"co2e_kg": 312000, "percent": 23.0, "scope": 2},
      "manufacturing": {"co2e_kg": 270000, "percent": 19.9, "scope": 3},
      "heating": {"co2e_kg": 86000, "percent": 6.3, "scope": 1},
      "fleet_vehicles": {"co2e_kg": 70000, "percent": 5.2, "scope": 1}
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "footprint_id": "fp-2024-abc123",
  "year": 2024,
  "total_kg": 1358000,
  "total_tonnes": 1358.0
}
```

---

## Step 3: Record Your ESG Assessment

### 3.1 Gather ESG Metrics

Collect data across all three pillars:

#### Environmental Metrics
| Metric | Example Value | How to Get |
|--------|---------------|------------|
| Renewable energy % | 25% | Energy bills / contracts |
| Waste recycled % | 60% | Waste management reports |
| Water efficiency | 72 | Water audit |
| Carbon intensity | 9.05 tCO2e/$M | Emissions / Revenue |

#### Social Metrics
| Metric | Example Value | How to Get |
|--------|---------------|------------|
| Employee satisfaction | 78 | Survey results |
| Diversity score | 65 | HR demographics |
| Safety incident rate | 1.2 | Safety reports |
| Community investment % | 0.8% | CSR budget / Revenue |

#### Governance Metrics
| Metric | Example Value | How to Get |
|--------|---------------|------------|
| Board independence % | 55% | Board composition |
| Ethics violations | 2 | Compliance records |
| Transparency score | 70 | Disclosure assessment |

### 3.2 Calculate ESG Score

Get your ESG score calculated automatically:

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/esg-score \
  -H "Content-Type: application/json" \
  -d '{
    "company_data": {
      "renewable_energy_percent": 25,
      "waste_recycled_percent": 60,
      "carbon_intensity": 9.05,
      "water_efficiency_score": 72,
      "employee_satisfaction": 78,
      "diversity_score": 65,
      "safety_incident_rate": 1.2,
      "community_investment_percent": 0.8,
      "board_independence_percent": 55,
      "ethics_violations": 2,
      "transparency_score": 70
    }
  }'
```

**Response:**
```json
{
  "overall_score": 68.2,
  "rating": "BBB",
  "environmental": {
    "score": 64.5,
    "strengths": ["Strong Waste Management (60/100)"],
    "weaknesses": ["Below Average Renewable Energy (25/100)"]
  },
  "social": {
    "score": 70.8,
    "strengths": ["Strong Employee Welfare (78/100)"],
    "weaknesses": ["Below Average Community Impact (8/100)"]
  },
  "governance": {
    "score": 69.3,
    "strengths": ["Good Transparency (70/100)"],
    "weaknesses": ["Ethics Violations Detected (2)"]
  },
  "recommendations": [
    "Increase renewable energy from 25% to 50%",
    "Improve community investment (target: 1.5%)",
    "Address ethics violations with training program",
    "Add more independent board members"
  ]
}
```

### 3.3 Record ESG Score in Database

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/esg \
  -H "Content-Type: application/json" \
  -d '{
    "overall_score": 68.2,
    "rating": "BBB",
    "environmental_score": 64.5,
    "social_score": 70.8,
    "governance_score": 69.3,
    "environmental_metrics": {
      "renewable_energy_percent": 25,
      "waste_recycled_percent": 60,
      "carbon_intensity": 9.05,
      "water_efficiency_score": 72
    },
    "social_metrics": {
      "employee_satisfaction": 78,
      "diversity_score": 65,
      "safety_incident_rate": 1.2,
      "community_investment_percent": 0.8
    },
    "governance_metrics": {
      "board_independence_percent": 55,
      "ethics_violations": 2,
      "transparency_score": 70
    },
    "strengths": [
      "Strong Waste Management",
      "Strong Employee Welfare"
    ],
    "weaknesses": [
      "Below Average Renewable Energy",
      "Ethics Violations Detected"
    ],
    "industry_percentile": 62
  }'
```

---

## Step 4: Get Your ESG Report

### 4.1 View Full Dashboard

Get your complete sustainability dashboard:

```bash
curl http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/dashboard
```

**Response (Summary):**
```json
{
  "company": {
    "name": "Acme Corporation",
    "industry": "manufacturing",
    "employees": 1200,
    "revenue_usd": 150000000
  },
  "locations": [
    {"name": "Detroit Headquarters", "type": "headquarters"},
    {"name": "Austin Manufacturing", "type": "factory"},
    {"name": "Chicago Distribution", "type": "warehouse"}
  ],
  "carbon_footprint": {
    "current": {
      "year": 2024,
      "total_kg": 1358000,
      "scope_1_kg": 156000,
      "scope_2_kg": 312000,
      "scope_3_kg": 890000
    },
    "yoy_change_percent": null
  },
  "esg": {
    "current": {
      "overall_score": 68.2,
      "rating": "BBB",
      "environmental_score": 64.5,
      "social_score": 70.8,
      "governance_score": 69.3
    }
  },
  "summary": {
    "total_emissions_kg": 1358000,
    "esg_score": 68.2,
    "active_initiatives": 0
  }
}
```

### 4.2 Compare to Industry Benchmark

See how you stack up against peers:

```bash
# Carbon intensity benchmark
curl "http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/benchmark/carbon_intensity_per_million_usd?value=9.05"
```

**Response:**
```json
{
  "company": "Acme Corporation",
  "industry": "manufacturing",
  "metric": "carbon_intensity_per_million_usd",
  "value": 9.05,
  "unit": "tCO2e/$M",
  "percentile": "Top 50%",
  "rating": "Good",
  "benchmark": {
    "p25": 8.0,
    "p50": 15.0,
    "p75": 25.0,
    "p90": 40.0,
    "year": 2024,
    "source": "CDP Climate Change 2024"
  }
}
```

---

## Step 5: Create Reduction Plan (Optional)

### 5.1 Set Your Net Zero Target

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/db/companies/abc123-def456/plans \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Net Zero 2040",
    "base_year": 2024,
    "target_year": 2040,
    "base_emissions_kg": 1358000,
    "target_emissions_kg": 0,
    "strategy": "SBTi 1.5C aligned pathway"
  }'
```

### 5.2 Add Reduction Initiatives

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/db/plans/plan-id-here/initiatives \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Solar Installation",
    "description": "Install rooftop solar at Austin factory",
    "category": "energy",
    "target_reduction_kg": 200000,
    "target_reduction_percent": 64,
    "timeline_months": 18,
    "estimated_cost_usd": 500000
  }'
```

---

## 📊 Summary: Your ESG Report Card

After completing the steps above, you'll have:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ACME CORPORATION - ESG REPORT 2024               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📊 ESG SCORE: 68.2/100                      Rating: BBB            │
│  ─────────────────────────────────────────────────────              │
│  Environmental: 64.5 ████████████░░░░░                              │
│  Social:        70.8 █████████████░░░░                              │
│  Governance:    69.3 █████████████░░░░                              │
│                                                                      │
│  🌡️ CARBON FOOTPRINT: 1,358 tonnes CO2e                             │
│  ─────────────────────────────────────────────────────              │
│  Scope 1 (Direct):     156t  ████                                   │
│  Scope 2 (Energy):     312t  ████████                               │
│  Scope 3 (Indirect):   890t  ██████████████████████                 │
│                                                                      │
│  📍 INDUSTRY BENCHMARK                                              │
│  ─────────────────────────────────────────────────────              │
│  Carbon Intensity: 9.05 tCO2e/$M  →  Top 50% (Good)                 │
│  ESG Score: 68.2/100              →  62nd Percentile                │
│                                                                      │
│  ✅ STRENGTHS                    ⚠️ IMPROVEMENT AREAS               │
│  • Waste Management              • Renewable Energy (25%)           │
│  • Employee Welfare              • Community Investment             │
│  • Water Efficiency              • Board Independence               │
│                                                                      │
│  🎯 TOP RECOMMENDATIONS                                             │
│  1. Increase renewable energy to 50%                                │
│  2. Improve community investment to 1.5%                            │
│  3. Address ethics violations                                       │
│  4. Add independent board members                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Quick Reference

### All Endpoints You'll Use

| Step | Endpoint | Method |
|------|----------|--------|
| Create company | `/db/companies` | POST |
| Add location | `/db/companies/{id}/locations` | POST |
| Calculate flight | `/flight-emissions` | POST |
| Calculate energy | `/electricity-emissions` | POST |
| Record footprint | `/db/companies/{id}/footprints` | POST |
| Calculate ESG | `/esg-score` | POST |
| Record ESG | `/db/companies/{id}/esg` | POST |
| Get dashboard | `/db/companies/{id}/dashboard` | GET |
| Benchmark | `/db/companies/{id}/benchmark/{metric}` | GET |
| Create plan | `/db/companies/{id}/plans` | POST |

### Data Collection Checklist

- [ ] Company information (name, industry, employees, revenue)
- [ ] Location details (addresses, sqft, employees per location)
- [ ] Energy bills (electricity kWh per location)
- [ ] Gas bills (therms/ccf per location)
- [ ] Business travel records (flights, car rentals)
- [ ] Employee commute survey data
- [ ] Fleet vehicle mileage
- [ ] Shipping/logistics data
- [ ] HR metrics (diversity, satisfaction)
- [ ] Safety records
- [ ] Board composition
- [ ] Community investment amounts

---

## 💬 Need Help?

Ask the AI assistant:

```bash
curl -X POST http://localhost:8000/api/v1/sustainability/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I calculate Scope 3 emissions for my manufacturing company?",
    "context": {"industry": "manufacturing"}
  }'
```


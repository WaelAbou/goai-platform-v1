#!/usr/bin/env python3
"""
Seed Sustainability Database

This script loads the XYZ Corporation demo data into the 
structured sustainability database.

Run with: python use_cases/sustainability_expert/seed_database.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.sustainability.database import (
    sustainability_db, Company, Location, CarbonFootprint,
    ESGScore, ReductionPlan, ReductionInitiative, IndustryBenchmark,
    EmissionSource
)


def load_xyz_corporation():
    """Load XYZ Corporation demo data into database."""
    
    # Load JSON data
    demo_file = Path(__file__).parent / "demo_data" / "xyz_corporation.json"
    
    if not demo_file.exists():
        print(f"❌ Demo data file not found: {demo_file}")
        return
    
    with open(demo_file) as f:
        data = json.load(f)
    
    print("=" * 60)
    print("🌱 SEEDING SUSTAINABILITY DATABASE")
    print("=" * 60)
    
    company_data = data["company"]
    
    # 1. Create Company
    print("\n📊 Creating company...")
    company = Company(
        id=company_data["id"],
        name=company_data["name"],
        industry=company_data["industry"],
        sub_industry=company_data.get("sub_industry"),
        employees=company_data.get("employees"),
        revenue_usd=company_data.get("revenue_usd"),
        headquarters="San Francisco, CA"
    )
    
    try:
        sustainability_db.create_company(company)
        print(f"   ✅ {company.name} created (ID: {company.id})")
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            print(f"   ⏭️  {company.name} already exists")
        else:
            print(f"   ❌ Error: {e}")
            return
    
    # 2. Add Locations
    print("\n📍 Adding locations...")
    for loc_data in company_data.get("locations", []):
        location = Location(
            id=f"{company.id}-{loc_data['name'].lower().replace(' ', '-')}",
            company_id=company.id,
            name=loc_data["name"],
            location_type=loc_data["type"],
            country="USA" if "US" in loc_data.get("name", "") or loc_data["type"] == "headquarters" else "UK",
            employees=loc_data.get("employees"),
            sqft=loc_data.get("sqft"),
            renewable_energy_percent=loc_data.get("renewable_energy_percent", 0)
        )
        try:
            sustainability_db.add_location(location)
            print(f"   ✅ {location.name} ({location.location_type})")
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                print(f"   ⏭️  {location.name} already exists")
            else:
                print(f"   ❌ {location.name}: {e}")
    
    # 3. Record Carbon Footprint
    print("\n🌡️ Recording carbon footprint...")
    cf_data = data["carbon_footprint"]
    
    footprint = CarbonFootprint(
        id=f"{company.id}-{cf_data['year']}",
        company_id=company.id,
        year=cf_data["year"],
        scope_1_kg=cf_data["breakdown"]["heating"]["co2e_kg"],
        scope_2_kg=cf_data["breakdown"]["office_energy"]["co2e_kg"],
        scope_3_kg=(
            cf_data["breakdown"]["business_travel"]["co2e_kg"] +
            cf_data["breakdown"]["employee_commuting"]["co2e_kg"] +
            cf_data["breakdown"]["cloud_infrastructure"]["co2e_kg"] +
            cf_data["breakdown"]["supply_chain"]["co2e_kg"]
        ),
        total_kg=cf_data["total_co2e_kg"],
        methodology="GHG Protocol Corporate Standard",
        verification_status=data["metadata"]["verification_status"],
        breakdown=cf_data["breakdown"]
    )
    
    try:
        sustainability_db.record_footprint(footprint)
        print(f"   ✅ {cf_data['year']}: {cf_data['total_co2e_tonnes']:,.1f} tonnes CO2e")
        print(f"      Scope 1: {footprint.scope_1_kg/1000:,.1f}t | Scope 2: {footprint.scope_2_kg/1000:,.1f}t | Scope 3: {footprint.scope_3_kg/1000:,.1f}t")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Add Emission Sources
    print("\n📋 Adding emission sources...")
    for category, source_data in cf_data["breakdown"].items():
        source = EmissionSource(
            id=f"{footprint.id}-{category}",
            footprint_id=footprint.id,
            category=category,
            scope=f"scope_{source_data['scope']}",
            co2e_kg=source_data["co2e_kg"],
            activity_data=source_data.get("details", {})
        )
        try:
            sustainability_db.add_emission_source(source)
            print(f"   ✅ {category}: {source_data['co2e_kg']:,.0f} kg ({source_data['percent']}%)")
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                print(f"   ⏭️  {category} already exists")
            else:
                print(f"   ❌ {category}: {e}")
    
    # 5. Record ESG Score
    print("\n⭐ Recording ESG score...")
    esg_data = data["esg_score"]
    
    esg = ESGScore(
        id=f"{company.id}-esg-{esg_data['assessment_date']}",
        company_id=company.id,
        assessment_date=datetime.fromisoformat(esg_data["assessment_date"]),
        overall_score=esg_data["overall_score"],
        rating=esg_data["rating"],
        environmental_score=esg_data["environmental"]["score"],
        social_score=esg_data["social"]["score"],
        governance_score=esg_data["governance"]["score"],
        environmental_metrics=esg_data["environmental"]["metrics"],
        social_metrics=esg_data["social"]["metrics"],
        governance_metrics=esg_data["governance"]["metrics"],
        strengths=esg_data["strengths"],
        weaknesses=esg_data["weaknesses"],
        industry_percentile=esg_data.get("industry_percentile")
    )
    
    try:
        sustainability_db.record_esg_score(esg)
        print(f"   ✅ Overall: {esg.overall_score}/100 ({esg.rating})")
        print(f"      E: {esg.environmental_score} | S: {esg.social_score} | G: {esg.governance_score}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 6. Create Reduction Plan
    print("\n🎯 Creating reduction plan...")
    plan_data = data["reduction_plan"]
    nz_data = data["net_zero_pathway"]
    
    plan = ReductionPlan(
        id=f"{company.id}-plan-{plan_data['target_year']}",
        company_id=company.id,
        name=f"Net Zero Pathway {nz_data['target_year']}",
        base_year=nz_data["base_year"],
        target_year=nz_data["target_year"],
        base_emissions_kg=nz_data["base_emissions_tonnes"] * 1000,
        target_emissions_kg=0,
        target_reduction_percent=100,
        strategy=nz_data["strategy"]
    )
    
    try:
        sustainability_db.create_reduction_plan(plan)
        print(f"   ✅ {plan.name}")
        print(f"      Base: {plan.base_emissions_kg/1000:,.0f}t → Target: Net Zero by {plan.target_year}")
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            print(f"   ⏭️  Plan already exists")
        else:
            print(f"   ❌ Error: {e}")
    
    # 7. Add Initiatives
    print("\n🚀 Adding reduction initiatives...")
    for init_data in plan_data["initiatives"]:
        initiative = ReductionInitiative(
            id=f"{plan.id}-{init_data['name'].lower().replace(' ', '-')}",
            plan_id=plan.id,
            name=init_data["name"],
            description=init_data["description"],
            category=init_data["name"].lower().split()[0],  # Extract category from name
            target_reduction_kg=init_data["estimated_reduction_kg"],
            target_reduction_percent=init_data["target_reduction_percent"],
            timeline_months=init_data["timeline_months"],
            status=init_data["status"]
        )
        try:
            sustainability_db.add_initiative(initiative)
            print(f"   ✅ {init_data['name']}: -{init_data['estimated_reduction_kg']/1000:,.1f}t ({init_data['target_reduction_percent']}%)")
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                print(f"   ⏭️  {init_data['name']} already exists")
            else:
                print(f"   ❌ {init_data['name']}: {e}")
    
    # 8. Add Industry Benchmarks
    print("\n📈 Adding industry benchmarks...")
    benchmarks = [
        IndustryBenchmark(
            id="tech-2024-carbon-intensity",
            industry="technology",
            year=2024,
            metric_name="carbon_intensity_per_million_usd",
            metric_unit="tCO2e/$M",
            percentile_25=8.0,
            percentile_50=15.0,
            percentile_75=25.0,
            percentile_90=40.0,
            sample_size=500,
            source="CDP Climate Change 2024"
        ),
        IndustryBenchmark(
            id="tech-2024-renewable-percent",
            industry="technology",
            year=2024,
            metric_name="renewable_energy_percent",
            metric_unit="%",
            percentile_25=90.0,
            percentile_50=65.0,
            percentile_75=40.0,
            percentile_90=20.0,
            sample_size=500,
            source="RE100 Progress Report 2024"
        ),
        IndustryBenchmark(
            id="tech-2024-esg-score",
            industry="technology",
            year=2024,
            metric_name="esg_overall_score",
            metric_unit="points",
            percentile_25=80.0,
            percentile_50=70.0,
            percentile_75=60.0,
            percentile_90=50.0,
            sample_size=500,
            source="MSCI ESG Ratings 2024"
        )
    ]
    
    for benchmark in benchmarks:
        try:
            sustainability_db.add_benchmark(benchmark)
            print(f"   ✅ {benchmark.metric_name} ({benchmark.industry})")
        except Exception as e:
            print(f"   ❌ {benchmark.metric_name}: {e}")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("📊 DATABASE SUMMARY")
    print("=" * 60)
    
    stats = sustainability_db.get_stats()
    for table, count in stats.items():
        print(f"   {table}: {count} records")
    
    print("\n✅ Seeding complete!")
    print(f"\n💡 Test with: curl http://localhost:8000/api/v1/sustainability/db/companies/{company.id}/dashboard")


def add_more_benchmarks():
    """Add additional industry benchmarks."""
    industries = ["manufacturing", "retail", "finance", "healthcare"]
    
    print("\n📈 Adding benchmarks for other industries...")
    
    for industry in industries:
        benchmarks = [
            IndustryBenchmark(
                id=f"{industry}-2024-carbon-intensity",
                industry=industry,
                year=2024,
                metric_name="carbon_intensity_per_million_usd",
                metric_unit="tCO2e/$M",
                percentile_25=20.0 if industry == "manufacturing" else 10.0,
                percentile_50=35.0 if industry == "manufacturing" else 18.0,
                percentile_75=50.0 if industry == "manufacturing" else 30.0,
                percentile_90=80.0 if industry == "manufacturing" else 50.0,
                sample_size=300,
                source="CDP Climate Change 2024"
            ),
            IndustryBenchmark(
                id=f"{industry}-2024-esg-score",
                industry=industry,
                year=2024,
                metric_name="esg_overall_score",
                metric_unit="points",
                percentile_25=75.0,
                percentile_50=65.0,
                percentile_75=55.0,
                percentile_90=45.0,
                sample_size=300,
                source="MSCI ESG Ratings 2024"
            )
        ]
        
        for benchmark in benchmarks:
            try:
                sustainability_db.add_benchmark(benchmark)
                print(f"   ✅ {industry}: {benchmark.metric_name}")
            except:
                pass


if __name__ == "__main__":
    load_xyz_corporation()
    add_more_benchmarks()


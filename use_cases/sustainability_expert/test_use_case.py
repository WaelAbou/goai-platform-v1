"""
Sustainability Expert Bot - Test Script

Comprehensive tests for carbon footprint, ESG scoring, and recommendations.

Run with:
    python use_cases/sustainability_expert/test_use_case.py

Requires:
    - Server running: uvicorn main:app --port 8000
    - Optional: OPENAI_API_KEY for chat features
"""

import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1/sustainability"


async def test_sustainability_expert():
    """Run comprehensive tests for the Sustainability Expert Bot."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("""
╔══════════════════════════════════════════════════════════════════╗
║           🌱 SUSTAINABILITY EXPERT BOT - TEST SUITE              ║
╚══════════════════════════════════════════════════════════════════╝
        """)
        
        # ==================== Test 1: Module Info ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("1️⃣  MODULE INFO")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.get(f"{BASE_URL}/info")
        if response.status_code == 200:
            info = response.json()
            print(f"   ✅ Name: {info['name']}")
            print(f"   ✅ Version: {info['version']}")
            print(f"   ✅ Capabilities: {len(info['capabilities'])}")
            for cap in info['capabilities'][:3]:
                print(f"      • {cap}")
        else:
            print(f"   ❌ Error: {response.status_code}")
        
        # ==================== Test 2: Flight Emissions ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("2️⃣  CARBON FOOTPRINT - FLIGHT (NYC to London)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.post(
            f"{BASE_URL}/carbon-footprint/flight",
            json={
                "distance_km": 5567,
                "travel_class": "economy",
                "round_trip": True,
                "passengers": 1
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Activity: {result['activity']}")
            print(f"   ✅ CO2e: {result['emissions']['co2e_kg']:.1f} kg ({result['emissions']['co2e_tonnes']:.2f} tonnes)")
            print(f"   ✅ Scope: {result['emissions']['scope']}")
            print(f"   ✅ Source: {result['methodology']['source']}")
            print(f"   📊 Equivalents:")
            for eq_name, eq_value in list(result['equivalents'].items())[:3]:
                print(f"      • {eq_value}")
        else:
            print(f"   ❌ Error: {response.text}")
        
        # ==================== Test 3: Vehicle Emissions ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("3️⃣  CARBON FOOTPRINT - VEHICLE COMPARISON")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        vehicle_types = [
            ("car_petrol_medium", "Petrol Car"),
            ("car_electric", "Electric Car"),
            ("train_national", "Train")
        ]
        
        for vehicle_type, name in vehicle_types:
            response = await client.post(
                f"{BASE_URL}/carbon-footprint/vehicle",
                json={
                    "distance_km": 100,
                    "vehicle_type": vehicle_type,
                    "passengers": 1
                }
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   🚗 {name}: {result['emissions']['co2e_kg']:.2f} kg CO2e for 100km")
        
        # ==================== Test 4: Electricity Emissions ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("4️⃣  CARBON FOOTPRINT - ELECTRICITY (10,000 kWh)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Compare grids
        grids = [("us_avg", "US Average"), ("uk", "UK Grid"), ("eu_avg", "EU Average")]
        
        for grid_code, grid_name in grids:
            response = await client.post(
                f"{BASE_URL}/carbon-footprint/electricity",
                json={
                    "kwh": 10000,
                    "grid": grid_code,
                    "renewable_percent": 0
                }
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ⚡ {grid_name}: {result['emissions']['co2e_kg']:.0f} kg CO2e")
        
        # With renewables
        response = await client.post(
            f"{BASE_URL}/carbon-footprint/electricity",
            json={
                "kwh": 10000,
                "grid": "us_avg",
                "renewable_percent": 50
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   🌿 US + 50% Renewable: {result['emissions']['co2e_kg']:.0f} kg CO2e")
        
        # ==================== Test 5: Shipping Emissions ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("5️⃣  CARBON FOOTPRINT - SHIPPING (1 tonne, 10,000 km)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        shipping_modes = [
            ("sea_container", "🚢 Sea Freight"),
            ("air_freight", "✈️ Air Freight"),
            ("road_freight", "🚛 Road Freight"),
            ("rail_freight", "🚂 Rail Freight")
        ]
        
        for mode, name in shipping_modes:
            response = await client.post(
                f"{BASE_URL}/carbon-footprint/shipping",
                json={
                    "weight_tonnes": 1,
                    "distance_km": 10000,
                    "mode": mode
                }
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   {name}: {result['emissions']['co2e_kg']:.0f} kg CO2e")
        
        # ==================== Test 6: ESG Score ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("6️⃣  ESG SCORING")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.post(
            f"{BASE_URL}/esg-score",
            json={
                "environmental_data": {
                    "renewable_energy_percent": 45,
                    "waste_recycled_percent": 65,
                    "carbon_intensity": 40,
                    "water_efficiency_score": 70
                },
                "social_data": {
                    "employee_satisfaction": 78,
                    "diversity_score": 62,
                    "safety_incident_rate": 1.5,
                    "community_investment_percent": 2
                },
                "governance_data": {
                    "board_independence_percent": 75,
                    "transparency_score": 80,
                    "risk_management_score": 72
                },
                "industry": "technology"
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   📊 ESG Scores:")
            print(f"      🌍 Environmental: {result['scores']['environmental']:.1f}/100")
            print(f"      👥 Social: {result['scores']['social']:.1f}/100")
            print(f"      📋 Governance: {result['scores']['governance']:.1f}/100")
            print(f"      ⭐ Overall: {result['scores']['overall']:.1f}/100")
            print(f"      🏆 Rating: {result['rating']}")
            print(f"      📈 Industry Percentile: {result['industry_percentile']}%")
            print(f"\n   💪 Strengths:")
            for s in result['analysis']['strengths'][:3]:
                print(f"      • {s}")
            print(f"\n   ⚠️ Weaknesses:")
            for w in result['analysis']['weaknesses'][:3]:
                print(f"      • {w}")
            print(f"\n   💡 Recommendations:")
            for r in result['analysis']['recommendations'][:3]:
                print(f"      • {r}")
        else:
            print(f"   ❌ Error: {response.text}")
        
        # ==================== Test 7: Industry Recommendations ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("7️⃣  INDUSTRY RECOMMENDATIONS (Technology)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.post(
            f"{BASE_URL}/recommendations",
            json={
                "industry": "technology",
                "company_size": "medium"
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   📋 {result['total']} recommendations for {result['industry']}:\n")
            for rec in result['recommendations']:
                print(f"   {rec['title']}")
                print(f"      📝 {rec['description']}")
                print(f"      📊 Impact: {rec['impact']} | Effort: {rec['effort']}")
                if rec.get('estimated_reduction_percent'):
                    print(f"      🎯 Est. reduction: {rec['estimated_reduction_percent']}%")
                if rec.get('timeline'):
                    print(f"      ⏱️ Timeline: {rec['timeline']}")
                if rec.get('sdg_alignment'):
                    print(f"      🎯 SDGs: {rec['sdg_alignment']}")
                print()
        
        # ==================== Test 8: Standards ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("8️⃣  SUSTAINABILITY STANDARDS")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.get(f"{BASE_URL}/standards")
        if response.status_code == 200:
            result = response.json()
            for std in result['standards']:
                print(f"   📚 {std['name']} - {std['full_name']}")
                print(f"      {std['description']}")
                print()
        
        # ==================== Test 9: UN SDGs ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("9️⃣  UN SUSTAINABLE DEVELOPMENT GOALS")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.get(f"{BASE_URL}/sdgs")
        if response.status_code == 200:
            result = response.json()
            # Show first 6 SDGs
            for sdg in result['sdgs'][:6]:
                print(f"   {sdg['icon']} SDG {sdg['number']}: {sdg['name']}")
            print(f"   ... and {result['total'] - 6} more")
        
        # ==================== Test 10: Chat (if LLM available) ====================
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔟 SUSTAINABILITY CHAT (Requires LLM)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        response = await client.post(
            f"{BASE_URL}/chat",
            json={
                "message": "What are the top 3 ways a tech startup can reduce its carbon footprint?",
                "context": {
                    "industry": "technology",
                    "company_size": "small"
                }
            }
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print(f"   ✅ Chat Response:")
                # Print first 500 chars of response
                response_text = result['response'][:500]
                print(f"   {response_text}...")
            else:
                print(f"   ⚠️ LLM not available: {result.get('tip', 'Check API key')}")
        else:
            print(f"   ❌ Error: {response.status_code}")
        
        # ==================== Summary ====================
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        print("""
   ✅ Module Info
   ✅ Flight Carbon Calculator
   ✅ Vehicle Carbon Calculator
   ✅ Electricity Carbon Calculator
   ✅ Shipping Carbon Calculator
   ✅ ESG Scoring
   ✅ Industry Recommendations
   ✅ Sustainability Standards
   ✅ UN SDGs
   ✅ Chat Interface (LLM-dependent)
   
   🌱 Sustainability Expert Bot is ready!
        """)


async def quick_demo():
    """Quick demonstration of key features."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n🚀 QUICK SUSTAINABILITY DEMO")
        print("-" * 40)
        
        # Calculate annual business travel footprint
        print("\n📊 Annual Business Travel Footprint:")
        
        # 10 round-trip flights
        response = await client.post(
            f"{BASE_URL}/carbon-footprint",
            json={
                "activity": "flight",
                "details": {
                    "distance_km": 3000,
                    "travel_class": "economy",
                    "round_trip": True
                }
            }
        )
        if response.status_code == 200:
            flight = response.json()
            annual_flights = flight['emissions']['co2e_kg'] * 10
            print(f"   ✈️ 10 Flights (3000km avg): {annual_flights:,.0f} kg CO2e")
        
        # 15000 km driving
        response = await client.post(
            f"{BASE_URL}/carbon-footprint",
            json={
                "activity": "vehicle",
                "details": {
                    "distance_km": 15000,
                    "vehicle_type": "car_petrol_medium"
                }
            }
        )
        if response.status_code == 200:
            driving = response.json()
            print(f"   🚗 15,000 km Driving: {driving['emissions']['co2e_kg']:,.0f} kg CO2e")
        
        # Office electricity
        response = await client.post(
            f"{BASE_URL}/carbon-footprint",
            json={
                "activity": "electricity",
                "details": {
                    "kwh": 50000,
                    "grid": "us_avg"
                }
            }
        )
        if response.status_code == 200:
            electricity = response.json()
            print(f"   ⚡ Office Electricity: {electricity['emissions']['co2e_kg']:,.0f} kg CO2e")
            
            # Total
            total = annual_flights + driving['emissions']['co2e_kg'] + electricity['emissions']['co2e_kg']
            print(f"\n   📊 TOTAL ANNUAL: {total:,.0f} kg CO2e ({total/1000:.1f} tonnes)")
            print(f"   🌳 Trees needed to offset: {total/21:,.0f} trees for 1 year")


if __name__ == "__main__":
    print("""
    ╭────────────────────────────────────────────────────────────╮
    │           🌱 SUSTAINABILITY EXPERT BOT                     │
    │                    Test Suite v1.0                         │
    ╰────────────────────────────────────────────────────────────╯
    """)
    
    # Run quick demo first
    asyncio.run(quick_demo())
    
    # Run full test suite
    asyncio.run(test_sustainability_expert())


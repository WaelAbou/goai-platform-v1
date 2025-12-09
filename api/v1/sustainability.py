"""
Sustainability Expert API

Endpoints for carbon footprint calculation, ESG scoring,
and sustainability recommendations.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from modules.sustainability import sustainability_engine
from modules.sustainability.unified_service import unified_service
from core.llm import llm_router
from modules.rag import rag_engine
from modules.ingestion import ingestion_engine
from core.vector import vector_retriever

router = APIRouter()

# Wire up dependencies
sustainability_engine.set_llm_router(llm_router)
sustainability_engine.set_rag_engine(rag_engine)

# Ensure RAG engine has its dependencies
rag_engine.set_llm_router(llm_router)
rag_engine.set_vector_retriever(vector_retriever)
rag_engine.set_ingestion_engine(ingestion_engine)


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    """Chat with the sustainability expert."""
    message: str = Field(..., description="User's sustainability question")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context like industry, company_size"
    )
    conversation_id: Optional[str] = None
    use_rag: bool = Field(default=True, description="Use RAG to retrieve relevant documents")


class IngestDocumentRequest(BaseModel):
    """Ingest a sustainability document into the knowledge base."""
    content: str = Field(..., description="Document content")
    title: str = Field(..., description="Document title")
    category: str = Field(
        default="general",
        description="Category: standards, regulations, best_practices, research, guidelines"
    )
    source: Optional[str] = Field(default=None, description="Source/author of the document")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorization")


class FlightEmissionsRequest(BaseModel):
    """Calculate flight emissions."""
    distance_km: float = Field(..., gt=0, description="One-way distance in kilometers")
    travel_class: str = Field(default="economy", description="economy, business, or first")
    round_trip: bool = Field(default=False)
    passengers: int = Field(default=1, ge=1)


class VehicleEmissionsRequest(BaseModel):
    """Calculate vehicle emissions."""
    distance_km: float = Field(..., gt=0)
    vehicle_type: str = Field(
        default="car_petrol_medium",
        description="Type: car_petrol_small/medium/large, car_diesel_medium, car_electric, car_hybrid, bus, train_national"
    )
    passengers: int = Field(default=1, ge=1)


class ElectricityEmissionsRequest(BaseModel):
    """Calculate electricity emissions."""
    kwh: float = Field(..., gt=0, description="Electricity consumption in kWh")
    grid: str = Field(default="us_avg", description="Grid: us_avg, uk, eu_avg")
    renewable_percent: float = Field(default=0, ge=0, le=100)


class NaturalGasEmissionsRequest(BaseModel):
    """Calculate natural gas emissions."""
    therms: float = Field(..., gt=0, description="Natural gas in therms")


class ShippingEmissionsRequest(BaseModel):
    """Calculate shipping emissions."""
    weight_tonnes: float = Field(..., gt=0)
    distance_km: float = Field(..., gt=0)
    mode: str = Field(
        default="sea_container",
        description="Mode: sea_container, air_freight, road_freight, rail_freight"
    )


class ESGScoreRequest(BaseModel):
    """Calculate ESG score."""
    environmental_data: Dict[str, float] = Field(
        default_factory=dict,
        description="E.g., renewable_energy_percent, waste_recycled_percent, carbon_intensity"
    )
    social_data: Dict[str, float] = Field(
        default_factory=dict,
        description="E.g., employee_satisfaction, diversity_score, safety_incident_rate"
    )
    governance_data: Dict[str, float] = Field(
        default_factory=dict,
        description="E.g., board_independence_percent, transparency_score"
    )
    industry: Optional[str] = None


class RecommendationsRequest(BaseModel):
    """Get sustainability recommendations."""
    industry: str = Field(..., description="technology, manufacturing, retail, finance, etc.")
    focus_area: Optional[str] = Field(
        default=None,
        description="Optional focus: energy, waste, transportation, supply_chain"
    )
    company_size: str = Field(default="medium", description="small, medium, large")


class CarbonFootprintRequest(BaseModel):
    """Generic carbon footprint calculation."""
    activity: str = Field(..., description="Activity type: flight, vehicle, electricity, natural_gas, shipping")
    details: Dict[str, Any] = Field(..., description="Activity-specific details")


# ==================== Chat Endpoint ====================

@router.post("/chat")
async def chat_with_expert(request: ChatRequest):
    """
    Chat with the Sustainability Expert Bot.
    
    Ask questions about:
    - Carbon footprint reduction
    - ESG reporting
    - Sustainability standards (GRI, TCFD, CDP)
    - Science-based targets
    - Industry best practices
    
    Set `use_rag: true` to retrieve relevant documents from the knowledge base.
    
    Example:
    ```json
    {
        "message": "How can a tech company reduce its carbon footprint?",
        "context": {"industry": "technology", "company_size": "medium"},
        "use_rag": true
    }
    ```
    """
    result = await sustainability_engine.chat(
        message=request.message,
        context=request.context,
        conversation_id=request.conversation_id,
        use_rag=request.use_rag
    )
    
    if result.get("error"):
        return {
            "response": result["response"],
            "status": "error",
            "tip": "Ensure OPENAI_API_KEY is configured in .env"
        }
    
    response_data = {
        "response": result["response"],
        "conversation_id": result.get("conversation_id"),
        "status": "success",
        "rag_enabled": result.get("rag_enabled", False)
    }
    
    # Include sources if RAG was used
    if result.get("sources"):
        response_data["sources"] = result["sources"]
    
    return response_data


# ==================== Knowledge Base / RAG Endpoints ====================

@router.post("/knowledge/ingest")
async def ingest_sustainability_document(request: IngestDocumentRequest):
    """
    Ingest a sustainability document into the knowledge base.
    
    This allows you to add custom documents that will be used
    to enhance AI responses with RAG.
    
    Categories:
    - `standards`: GRI, TCFD, CDP, ISO standards
    - `regulations`: Environmental regulations
    - `best_practices`: Industry best practices
    - `research`: Research papers and studies
    - `guidelines`: Internal guidelines
    
    Example:
    ```json
    {
        "title": "GRI 305: Emissions 2016",
        "content": "This Standard sets out reporting requirements...",
        "category": "standards",
        "source": "Global Reporting Initiative",
        "tags": ["GRI", "emissions", "scope1", "scope2"]
    }
    ```
    """
    try:
        # Build metadata
        metadata = {
            "filename": request.title,
            "category": request.category,
            "type": "sustainability_knowledge",
            "source": request.source or "user_upload"
        }
        if request.tags:
            metadata["tags"] = request.tags
        
        # Ingest via the ingestion engine
        result = await ingestion_engine.ingest_text(
            text=request.content,
            filename=request.title,
            metadata=metadata
        )
        
        return {
            "status": "success",
            "message": f"Document '{request.title}' ingested successfully",
            "document_id": result.id,
            "chunks": result.total_chunks,
            "category": request.category
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/knowledge/stats")
async def get_knowledge_base_stats():
    """
    Get statistics about the sustainability knowledge base.
    """
    try:
        # Get stats from vector retriever
        doc_count = len(vector_retriever.documents) if hasattr(vector_retriever, 'documents') else 0
        
        return {
            "status": "active",
            "documents": doc_count,
            "categories": ["standards", "regulations", "best_practices", "research", "guidelines"],
            "supported_standards": [
                "GRI Standards",
                "TCFD Recommendations", 
                "CDP Questionnaires",
                "Science Based Targets (SBTi)",
                "ISO 14001",
                "UN SDGs"
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/knowledge/search")
async def search_knowledge_base(query: str, top_k: int = 5):
    """
    Search the sustainability knowledge base.
    
    Returns relevant documents without generating an AI response.
    Useful for exploring what documents are available.
    """
    try:
        results = await vector_retriever.search(
            query=query,
            top_k=top_k
        )
        
        return {
            "query": query,
            "results": [
                {
                    "content": r.content[:500] + "..." if len(r.content) > 500 else r.content,
                    "score": r.score,
                    "metadata": r.metadata
                }
                for r in results
            ],
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ==================== Carbon Footprint Endpoints ====================

@router.post("/carbon-footprint")
async def calculate_carbon_footprint(request: CarbonFootprintRequest):
    """
    Calculate carbon footprint for various activities.
    
    Supported activities:
    - `flight`: Air travel emissions
    - `vehicle`: Ground transportation
    - `electricity`: Electricity consumption
    - `natural_gas`: Natural gas usage
    - `shipping`: Freight transport
    
    Example:
    ```json
    {
        "activity": "flight",
        "details": {
            "distance_km": 5600,
            "travel_class": "economy",
            "round_trip": true
        }
    }
    ```
    """
    try:
        if request.activity == "flight":
            result = sustainability_engine.calculate_flight_emissions(
                distance_km=request.details.get("distance_km", 1000),
                travel_class=request.details.get("travel_class", "economy"),
                round_trip=request.details.get("round_trip", False),
                passengers=request.details.get("passengers", 1)
            )
        elif request.activity == "vehicle":
            result = sustainability_engine.calculate_vehicle_emissions(
                distance_km=request.details.get("distance_km", 100),
                vehicle_type=request.details.get("vehicle_type", "car_petrol_medium"),
                passengers=request.details.get("passengers", 1)
            )
        elif request.activity == "electricity":
            result = sustainability_engine.calculate_electricity_emissions(
                kwh=request.details.get("kwh", 1000),
                grid=request.details.get("grid", "us_avg"),
                renewable_percent=request.details.get("renewable_percent", 0)
            )
        elif request.activity == "natural_gas":
            result = sustainability_engine.calculate_natural_gas_emissions(
                therms=request.details.get("therms", 100)
            )
        elif request.activity == "shipping":
            result = sustainability_engine.calculate_shipping_emissions(
                weight_tonnes=request.details.get("weight_tonnes", 1),
                distance_km=request.details.get("distance_km", 1000),
                mode=request.details.get("mode", "sea_container")
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown activity: {request.activity}. Supported: flight, vehicle, electricity, natural_gas, shipping"
            )
        
        return result.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/carbon-footprint/flight")
async def calculate_flight(request: FlightEmissionsRequest):
    """
    Calculate flight emissions.
    
    Example: NYC to London round trip in economy
    ```json
    {
        "distance_km": 5567,
        "travel_class": "economy",
        "round_trip": true
    }
    ```
    """
    result = sustainability_engine.calculate_flight_emissions(
        distance_km=request.distance_km,
        travel_class=request.travel_class,
        round_trip=request.round_trip,
        passengers=request.passengers
    )
    return result.to_dict()


@router.post("/carbon-footprint/vehicle")
async def calculate_vehicle(request: VehicleEmissionsRequest):
    """Calculate vehicle emissions."""
    result = sustainability_engine.calculate_vehicle_emissions(
        distance_km=request.distance_km,
        vehicle_type=request.vehicle_type,
        passengers=request.passengers
    )
    return result.to_dict()


@router.post("/carbon-footprint/electricity")
async def calculate_electricity(request: ElectricityEmissionsRequest):
    """Calculate electricity emissions."""
    result = sustainability_engine.calculate_electricity_emissions(
        kwh=request.kwh,
        grid=request.grid,
        renewable_percent=request.renewable_percent
    )
    return result.to_dict()


@router.post("/carbon-footprint/natural-gas")
async def calculate_natural_gas(request: NaturalGasEmissionsRequest):
    """Calculate natural gas emissions."""
    result = sustainability_engine.calculate_natural_gas_emissions(
        therms=request.therms
    )
    return result.to_dict()


@router.post("/carbon-footprint/shipping")
async def calculate_shipping(request: ShippingEmissionsRequest):
    """Calculate shipping/freight emissions."""
    result = sustainability_engine.calculate_shipping_emissions(
        weight_tonnes=request.weight_tonnes,
        distance_km=request.distance_km,
        mode=request.mode
    )
    return result.to_dict()


# ==================== ESG Endpoints ====================

@router.post("/esg-score")
async def calculate_esg_score(request: ESGScoreRequest):
    """
    Calculate ESG (Environmental, Social, Governance) score.
    
    Example:
    ```json
    {
        "environmental_data": {
            "renewable_energy_percent": 40,
            "waste_recycled_percent": 60,
            "carbon_intensity": 50
        },
        "social_data": {
            "employee_satisfaction": 75,
            "diversity_score": 65,
            "safety_incident_rate": 2
        },
        "governance_data": {
            "board_independence_percent": 70,
            "transparency_score": 80
        },
        "industry": "technology"
    }
    ```
    """
    result = sustainability_engine.calculate_esg_score(
        environmental_data=request.environmental_data,
        social_data=request.social_data,
        governance_data=request.governance_data,
        industry=request.industry
    )
    return result.to_dict()


# ==================== Recommendations Endpoints ====================

@router.post("/recommendations")
async def get_recommendations(request: RecommendationsRequest):
    """
    Get industry-specific sustainability recommendations.
    
    Example:
    ```json
    {
        "industry": "technology",
        "focus_area": "energy",
        "company_size": "medium"
    }
    ```
    """
    recommendations = sustainability_engine.get_industry_recommendations(
        industry=request.industry,
        focus_area=request.focus_area,
        company_size=request.company_size
    )
    
    return {
        "industry": request.industry,
        "focus_area": request.focus_area,
        "recommendations": [r.to_dict() for r in recommendations],
        "total": len(recommendations)
    }


# ==================== Reference Data Endpoints ====================

@router.get("/standards")
async def list_standards():
    """
    List supported sustainability standards and frameworks.
    
    Returns information about GRI, TCFD, CDP, SBTi, ISO 14001, and UN SDGs.
    """
    return {
        "standards": sustainability_engine.get_supported_standards(),
        "total": len(sustainability_engine.get_supported_standards())
    }


@router.get("/sdgs")
async def list_sdgs():
    """
    Get UN Sustainable Development Goals (SDGs).
    
    Returns all 17 SDGs with names and icons.
    """
    sdgs = sustainability_engine.get_sdgs()
    return {
        "sdgs": [
            {"number": k, **v}
            for k, v in sdgs.items()
        ],
        "total": 17
    }


@router.get("/sdgs/{sdg_number}")
async def get_sdg(sdg_number: int):
    """Get details for a specific SDG."""
    if sdg_number < 1 or sdg_number > 17:
        raise HTTPException(status_code=404, detail="SDG number must be 1-17")
    
    sdgs = sustainability_engine.get_sdgs()
    sdg = sdgs.get(sdg_number)
    
    return {
        "number": sdg_number,
        **sdg
    }


@router.get("/emission-factors")
async def list_emission_factors():
    """
    List all emission factors used in calculations.
    
    Useful for understanding the data sources and methodology.
    """
    factors = sustainability_engine.EMISSION_FACTORS
    
    categories = {
        "aviation": {},
        "ground_transport": {},
        "electricity": {},
        "heating": {},
        "shipping": {},
        "other": {}
    }
    
    for key, value in factors.items():
        if "flight" in key:
            categories["aviation"][key] = value
        elif "car" in key or "bus" in key or "train" in key:
            categories["ground_transport"][key] = value
        elif "electricity" in key:
            categories["electricity"][key] = value
        elif "gas" in key:
            categories["heating"][key] = value
        elif "shipping" in key:
            categories["shipping"][key] = value
        else:
            categories["other"][key] = value
    
    return {
        "factors_by_category": categories,
        "sources": [
            "EPA GHG Emission Factors Hub",
            "UK DEFRA Greenhouse Gas Conversion Factors 2023"
        ],
        "units_note": "All factors are in kg CO2e per unit specified"
    }


# ==================== Info Endpoint ====================

@router.get("/info")
async def get_info():
    """Get information about the Sustainability Expert module."""
    return {
        "name": "Sustainability Expert Bot",
        "version": "1.0.0",
        "description": "AI-powered sustainability advisor for carbon footprint, ESG, and recommendations",
        "capabilities": [
            "Carbon footprint calculation (Scope 1, 2, 3)",
            "ESG scoring and analysis",
            "Industry-specific recommendations",
            "UN SDG alignment",
            "Sustainability standards guidance (GRI, TCFD, CDP, SBTi)",
            "Structured database for companies and metrics"
        ],
        "endpoints": {
            "chat": "POST /api/v1/sustainability/chat",
            "carbon_footprint": "POST /api/v1/sustainability/carbon-footprint",
            "esg_score": "POST /api/v1/sustainability/esg-score",
            "recommendations": "POST /api/v1/sustainability/recommendations",
            "standards": "GET /api/v1/sustainability/standards",
            "sdgs": "GET /api/v1/sustainability/sdgs",
            "database": {
                "companies": "GET/POST /api/v1/sustainability/db/companies",
                "footprints": "GET/POST /api/v1/sustainability/db/companies/{id}/footprints",
                "esg": "GET/POST /api/v1/sustainability/db/companies/{id}/esg",
                "plans": "GET/POST /api/v1/sustainability/db/companies/{id}/plans",
                "dashboard": "GET /api/v1/sustainability/db/companies/{id}/dashboard"
            }
        },
        "data_sources": [
            "EPA GHG Emission Factors Hub",
            "UK DEFRA Conversion Factors 2023",
            "GRI Standards 2021",
            "TCFD Recommendations"
        ]
    }


# ==================== Database API Endpoints ====================

from modules.sustainability.database import (
    sustainability_db, Company, Location, CarbonFootprint, 
    ESGScore, ReductionPlan, ReductionInitiative, IndustryBenchmark
)
import uuid
from datetime import datetime


# --- Company Endpoints ---

class CreateCompanyRequest(BaseModel):
    """Create a new company."""
    name: str = Field(..., description="Company name")
    industry: str = Field(..., description="Industry sector")
    sub_industry: Optional[str] = None
    employees: Optional[int] = None
    revenue_usd: Optional[float] = None
    headquarters: Optional[str] = None
    description: Optional[str] = None


@router.post("/db/companies")
async def create_company(request: CreateCompanyRequest):
    """
    Create a new company in the sustainability database.
    
    Example:
    ```json
    {
        "name": "XYZ Corporation",
        "industry": "technology",
        "employees": 500,
        "revenue_usd": 75000000
    }
    ```
    """
    company = Company(
        id=str(uuid.uuid4()),
        name=request.name,
        industry=request.industry,
        sub_industry=request.sub_industry,
        employees=request.employees,
        revenue_usd=request.revenue_usd,
        headquarters=request.headquarters,
        description=request.description
    )
    
    company_id = sustainability_db.create_company(company)
    
    return {
        "status": "success",
        "company_id": company_id,
        "message": f"Company '{request.name}' created successfully"
    }


@router.get("/db/companies")
async def list_companies(industry: Optional[str] = None):
    """List all companies, optionally filtered by industry."""
    companies = sustainability_db.list_companies(industry)
    return {
        "companies": companies,
        "total": len(companies),
        "filter": {"industry": industry} if industry else None
    }


@router.get("/db/companies/{company_id}")
async def get_company(company_id: str):
    """Get company details by ID."""
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    locations = sustainability_db.get_company_locations(company_id)
    company["locations"] = locations
    
    return company


@router.get("/db/companies/{company_id}/dashboard")
async def get_company_dashboard(company_id: str):
    """
    Get comprehensive sustainability dashboard for a company.
    
    Includes:
    - Company profile
    - Carbon footprint history
    - Latest ESG score
    - Active reduction plans
    - Year-over-year trends
    """
    dashboard = sustainability_db.get_company_dashboard(company_id)
    
    if dashboard.get("error"):
        raise HTTPException(status_code=404, detail=dashboard["error"])
    
    return dashboard


# --- Location Endpoints ---

class AddLocationRequest(BaseModel):
    """Add a company location."""
    name: str
    location_type: str = Field(..., description="headquarters, regional, warehouse, factory")
    country: str
    city: Optional[str] = None
    employees: Optional[int] = None
    sqft: Optional[float] = None
    renewable_energy_percent: float = 0.0


@router.post("/db/companies/{company_id}/locations")
async def add_company_location(company_id: str, request: AddLocationRequest):
    """Add a location/facility to a company."""
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    location = Location(
        id=str(uuid.uuid4()),
        company_id=company_id,
        name=request.name,
        location_type=request.location_type,
        country=request.country,
        city=request.city,
        employees=request.employees,
        sqft=request.sqft,
        renewable_energy_percent=request.renewable_energy_percent
    )
    
    location_id = sustainability_db.add_location(location)
    
    return {
        "status": "success",
        "location_id": location_id,
        "message": f"Location '{request.name}' added to company"
    }


# --- Carbon Footprint Endpoints ---

class RecordFootprintRequest(BaseModel):
    """Record annual carbon footprint."""
    year: int = Field(..., ge=2000, le=2100)
    scope_1_kg: float = Field(default=0, ge=0)
    scope_2_kg: float = Field(default=0, ge=0)
    scope_3_kg: float = Field(default=0, ge=0)
    methodology: str = "GHG Protocol"
    verification_status: str = "self-reported"
    breakdown: Optional[Dict[str, Any]] = None


@router.post("/db/companies/{company_id}/footprints")
async def record_carbon_footprint(company_id: str, request: RecordFootprintRequest):
    """
    Record annual carbon footprint for a company.
    
    Example:
    ```json
    {
        "year": 2024,
        "scope_1_kg": 42480,
        "scope_2_kg": 81090,
        "scope_3_kg": 1022198,
        "methodology": "GHG Protocol",
        "breakdown": {
            "business_travel": {"co2e_kg": 467424, "percent": 40.8},
            "office_energy": {"co2e_kg": 81090, "percent": 7.1}
        }
    }
    ```
    """
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    total_kg = request.scope_1_kg + request.scope_2_kg + request.scope_3_kg
    
    footprint = CarbonFootprint(
        id=str(uuid.uuid4()),
        company_id=company_id,
        year=request.year,
        scope_1_kg=request.scope_1_kg,
        scope_2_kg=request.scope_2_kg,
        scope_3_kg=request.scope_3_kg,
        total_kg=total_kg,
        methodology=request.methodology,
        verification_status=request.verification_status,
        breakdown=request.breakdown or {}
    )
    
    footprint_id = sustainability_db.record_footprint(footprint)
    
    return {
        "status": "success",
        "footprint_id": footprint_id,
        "year": request.year,
        "total_kg": total_kg,
        "total_tonnes": round(total_kg / 1000, 2)
    }


@router.get("/db/companies/{company_id}/footprints")
async def get_footprint_history(company_id: str, years: int = 5):
    """Get carbon footprint history for a company."""
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    history = sustainability_db.get_footprint_history(company_id, years)
    
    return {
        "company_id": company_id,
        "company_name": company["name"],
        "footprints": history,
        "total_records": len(history)
    }


@router.get("/db/companies/{company_id}/footprints/{year}")
async def get_footprint_by_year(company_id: str, year: int):
    """Get carbon footprint for a specific year."""
    footprint = sustainability_db.get_footprint(company_id, year)
    if not footprint:
        raise HTTPException(status_code=404, detail=f"No footprint found for {year}")
    
    return footprint


# --- ESG Score Endpoints ---

class RecordESGRequest(BaseModel):
    """Record ESG assessment."""
    overall_score: float = Field(..., ge=0, le=100)
    rating: str = Field(..., description="AAA, AA, A, BBB, BB, B, CCC, CC")
    environmental_score: float = Field(..., ge=0, le=100)
    social_score: float = Field(..., ge=0, le=100)
    governance_score: float = Field(..., ge=0, le=100)
    environmental_metrics: Optional[Dict[str, float]] = None
    social_metrics: Optional[Dict[str, float]] = None
    governance_metrics: Optional[Dict[str, float]] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    industry_percentile: Optional[float] = None


@router.post("/db/companies/{company_id}/esg")
async def record_esg_score(company_id: str, request: RecordESGRequest):
    """
    Record ESG assessment for a company.
    
    Example:
    ```json
    {
        "overall_score": 74.5,
        "rating": "A",
        "environmental_score": 69.5,
        "social_score": 72.8,
        "governance_score": 81.1,
        "industry_percentile": 79
    }
    ```
    """
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    esg = ESGScore(
        id=str(uuid.uuid4()),
        company_id=company_id,
        assessment_date=datetime.now(),
        overall_score=request.overall_score,
        rating=request.rating,
        environmental_score=request.environmental_score,
        social_score=request.social_score,
        governance_score=request.governance_score,
        environmental_metrics=request.environmental_metrics or {},
        social_metrics=request.social_metrics or {},
        governance_metrics=request.governance_metrics or {},
        strengths=request.strengths or [],
        weaknesses=request.weaknesses or [],
        industry_percentile=request.industry_percentile
    )
    
    esg_id = sustainability_db.record_esg_score(esg)
    
    return {
        "status": "success",
        "esg_id": esg_id,
        "overall_score": request.overall_score,
        "rating": request.rating
    }


@router.get("/db/companies/{company_id}/esg")
async def get_esg_scores(company_id: str):
    """Get ESG score history for a company."""
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    history = sustainability_db.get_esg_history(company_id)
    latest = sustainability_db.get_latest_esg_score(company_id)
    
    return {
        "company_id": company_id,
        "latest": latest,
        "history": history
    }


# --- Reduction Plan Endpoints ---

class CreatePlanRequest(BaseModel):
    """Create a reduction plan."""
    name: str
    base_year: int
    target_year: int
    base_emissions_kg: float
    target_emissions_kg: float
    strategy: Optional[str] = None


class AddInitiativeRequest(BaseModel):
    """Add initiative to a plan."""
    name: str
    description: str
    category: str = Field(..., description="energy, travel, supply_chain, waste")
    target_reduction_kg: float
    target_reduction_percent: float
    timeline_months: int
    estimated_cost_usd: Optional[float] = None


@router.post("/db/companies/{company_id}/plans")
async def create_reduction_plan(company_id: str, request: CreatePlanRequest):
    """Create a carbon reduction plan for a company."""
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    target_reduction = ((request.base_emissions_kg - request.target_emissions_kg) 
                        / request.base_emissions_kg * 100)
    
    plan = ReductionPlan(
        id=str(uuid.uuid4()),
        company_id=company_id,
        name=request.name,
        base_year=request.base_year,
        target_year=request.target_year,
        base_emissions_kg=request.base_emissions_kg,
        target_emissions_kg=request.target_emissions_kg,
        target_reduction_percent=target_reduction,
        strategy=request.strategy
    )
    
    plan_id = sustainability_db.create_reduction_plan(plan)
    
    return {
        "status": "success",
        "plan_id": plan_id,
        "target_reduction_percent": round(target_reduction, 1)
    }


@router.get("/db/companies/{company_id}/plans")
async def get_company_plans(company_id: str):
    """Get all reduction plans for a company."""
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    plans = sustainability_db.get_company_plans(company_id)
    
    return {
        "company_id": company_id,
        "plans": plans,
        "total": len(plans)
    }


@router.post("/db/plans/{plan_id}/initiatives")
async def add_initiative(plan_id: str, request: AddInitiativeRequest):
    """Add an initiative to a reduction plan."""
    plan = sustainability_db.get_reduction_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    initiative = ReductionInitiative(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        name=request.name,
        description=request.description,
        category=request.category,
        target_reduction_kg=request.target_reduction_kg,
        target_reduction_percent=request.target_reduction_percent,
        timeline_months=request.timeline_months,
        estimated_cost_usd=request.estimated_cost_usd
    )
    
    initiative_id = sustainability_db.add_initiative(initiative)
    
    return {
        "status": "success",
        "initiative_id": initiative_id
    }


# --- Benchmark Endpoints ---

@router.get("/db/benchmarks/{industry}")
async def get_industry_benchmarks(industry: str, year: Optional[int] = None):
    """Get industry benchmarks."""
    benchmarks = sustainability_db.get_benchmarks(industry, year)
    
    return {
        "industry": industry,
        "year": year,
        "benchmarks": benchmarks,
        "total": len(benchmarks)
    }


@router.get("/db/companies/{company_id}/benchmark/{metric}")
async def compare_to_benchmark(company_id: str, metric: str, value: float):
    """Compare a company's metric to industry benchmark."""
    result = sustainability_db.compare_to_benchmark(company_id, metric, value)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


# --- Database Stats ---

@router.get("/db/stats")
async def get_database_stats():
    """Get sustainability database statistics."""
    stats = sustainability_db.get_stats()
    
    return {
        "database": "sustainability.db",
        "tables": stats,
        "status": "active"
    }


# ==================== Data Ingestion Endpoints ====================

from modules.sustainability.data_ingestion import data_ingestion, DATA_TEMPLATES
from fastapi import UploadFile, File, Form
from fastapi.responses import PlainTextResponse


@router.get("/import/templates")
async def list_import_templates():
    """
    List all available data import templates.
    
    Templates help you format your data for import:
    - energy: Electricity and gas usage
    - travel: Business travel (flights, car)
    - fleet: Company vehicle data
    - commuting: Employee commute surveys
    - esg_metrics: Quarterly ESG data
    - shipping: Logistics/freight data
    """
    templates = data_ingestion.get_templates()
    
    return {
        "templates": templates,
        "total": len(templates),
        "instructions": "Download a template, fill with your data, then upload via /import/{category}"
    }


@router.get("/import/templates/{category}")
async def get_import_template(category: str, format: str = "json"):
    """
    Get a specific data import template.
    
    Args:
        category: energy, travel, fleet, commuting, esg_metrics, shipping
        format: json or csv
    """
    template = data_ingestion.get_template(category)
    
    if not template:
        raise HTTPException(
            status_code=404, 
            detail=f"Template not found. Available: {list(DATA_TEMPLATES.keys())}"
        )
    
    if format.lower() == "csv":
        csv_content = data_ingestion.generate_csv_template(category)
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={category}_template.csv"}
        )
    else:
        return {
            "template": template["name"],
            "description": template["description"],
            "columns": template["columns"],
            "example": template["example_row"],
            "download_csv": f"/api/v1/sustainability/import/templates/{category}?format=csv"
        }


@router.post("/import/{category}/csv")
async def import_csv_data(
    category: str,
    file: UploadFile = File(...),
    company_id: Optional[str] = Form(None)
):
    """
    Import data from CSV file.
    
    Supported categories:
    - `energy`: Electricity and gas usage by location
    - `travel`: Business travel records (flights, car rentals)
    - `fleet`: Company vehicle mileage and fuel
    - `commuting`: Employee commute surveys
    - `esg_metrics`: Quarterly ESG metrics
    - `shipping`: Logistics and freight data
    
    Example:
    ```bash
    curl -X POST http://localhost:8000/api/v1/sustainability/import/energy/csv \\
      -F "file=@energy_data.csv" \\
      -F "company_id=xyz-corp-001"
    ```
    """
    if category not in DATA_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {list(DATA_TEMPLATES.keys())}"
        )
    
    # Read file content
    content = await file.read()
    csv_content = content.decode("utf-8")
    
    # Import data
    result = data_ingestion.import_csv(csv_content, category)
    
    return {
        "status": "success" if result.success else "partial",
        "import_id": result.import_id,
        "category": category,
        "company_id": company_id,
        "records": {
            "processed": result.records_processed,
            "imported": result.records_imported,
            "failed": result.records_failed
        },
        "errors": [
            {"row": e.row, "column": e.column, "error": e.error}
            for e in result.errors[:10]  # Limit to first 10 errors
        ] if result.errors else [],
        "data_preview": result.data[:3] if result.data else [],
        "total_co2e_kg": sum(r.get("calculated_co2e_kg", 0) for r in result.data) if result.data else 0
    }


@router.post("/import/{category}/json")
async def import_json_data(
    category: str,
    data: List[Dict[str, Any]],
    company_id: Optional[str] = None
):
    """
    Import data from JSON.
    
    Example:
    ```json
    {
        "company_id": "xyz-corp-001",
        "data": [
            {
                "location_name": "SF HQ",
                "month": "2024-01",
                "electricity_kwh": 45000,
                "renewable_percent": 100
            }
        ]
    }
    ```
    """
    if category not in DATA_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {list(DATA_TEMPLATES.keys())}"
        )
    
    # Convert to JSON string for processing
    json_content = json.dumps(data)
    
    # Import data
    result = data_ingestion.import_json(json_content, category)
    
    return {
        "status": "success" if result.success else "partial",
        "import_id": result.import_id,
        "category": category,
        "company_id": company_id,
        "records": {
            "processed": result.records_processed,
            "imported": result.records_imported,
            "failed": result.records_failed
        },
        "errors": [
            {"row": e.row, "column": e.column, "error": e.error}
            for e in result.errors[:10]
        ] if result.errors else [],
        "data": result.data,
        "total_co2e_kg": sum(r.get("calculated_co2e_kg", 0) for r in result.data) if result.data else 0
    }


@router.post("/import/aggregate/{company_id}/{year}")
async def aggregate_imported_data(
    company_id: str,
    year: int,
    energy_data: Optional[List[Dict[str, Any]]] = None,
    travel_data: Optional[List[Dict[str, Any]]] = None,
    fleet_data: Optional[List[Dict[str, Any]]] = None,
    commuting_data: Optional[List[Dict[str, Any]]] = None,
    shipping_data: Optional[List[Dict[str, Any]]] = None,
    save_to_db: bool = True
):
    """
    Aggregate all imported data into a carbon footprint and optionally save to database.
    
    This combines data from all categories into a single annual footprint.
    """
    company = sustainability_db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Aggregate data
    footprint = data_ingestion.aggregate_to_footprint(
        energy_data=energy_data or [],
        travel_data=travel_data or [],
        fleet_data=fleet_data or [],
        commuting_data=commuting_data or [],
        shipping_data=shipping_data or [],
        year=year
    )
    
    # Save to database if requested
    if save_to_db:
        from modules.sustainability.database import CarbonFootprint
        
        cf = CarbonFootprint(
            id=f"{company_id}-{year}",
            company_id=company_id,
            year=year,
            scope_1_kg=footprint["scope_1_kg"],
            scope_2_kg=footprint["scope_2_kg"],
            scope_3_kg=footprint["scope_3_kg"],
            total_kg=footprint["total_kg"],
            methodology=footprint["methodology"],
            verification_status="calculated",
            breakdown=footprint["breakdown"]
        )
        
        sustainability_db.record_footprint(cf)
        footprint["saved_to_db"] = True
        footprint["footprint_id"] = cf.id
    
    return {
        "company_id": company_id,
        "company_name": company["name"],
        "footprint": footprint
    }


@router.get("/import/emission-factors")
async def get_emission_factors():
    """
    Get all emission factors used for calculations.
    
    These are the CO2e conversion factors applied to raw data.
    """
    return {
        "emission_factors": data_ingestion.EMISSION_FACTORS,
        "sources": [
            "EPA GHG Emission Factors Hub 2023",
            "UK DEFRA Conversion Factors 2023",
            "IPCC Guidelines for National GHG Inventories"
        ],
        "units": {
            "electricity": "kg CO2e per kWh",
            "natural_gas": "kg CO2e per therm",
            "flights": "kg CO2e per passenger-km",
            "vehicles": "kg CO2e per km",
            "shipping": "kg CO2e per tonne-km"
        }
    }


# ==================== Smart Document Processing (OCR + LLM) ====================

from modules.sustainability.smart_ingestion import (
    smart_processor, 
    SustainabilityDocumentType,
    ExtractedData
)
from modules.ingestion.ocr import ocr_engine

# Wire up dependencies
smart_processor.set_llm_router(llm_router)
smart_processor.set_ocr_engine(ocr_engine)


@router.get("/smart/document-types")
async def list_smart_document_types():
    """
    List document types that can be automatically detected and processed.
    
    The smart processor uses OCR + LLM to:
    1. Detect document type from image/text
    2. Extract relevant sustainability data
    3. Calculate CO2e emissions automatically
    """
    return {
        "supported_types": smart_processor.get_supported_document_types(),
        "how_it_works": [
            "1. Upload document image or text",
            "2. OCR extracts text (if image)",
            "3. LLM classifies document type",
            "4. LLM extracts structured data",
            "5. System calculates CO2e emissions",
            "6. Data ready for import to database"
        ],
        "endpoints": {
            "process_image": "POST /smart/process-image",
            "process_text": "POST /smart/process-text",
            "classify": "POST /smart/classify"
        }
    }


class SmartProcessRequest(BaseModel):
    """Request for smart document processing."""
    image_base64: Optional[str] = Field(None, description="Base64-encoded image")
    text_content: Optional[str] = Field(None, description="Plain text content")
    force_type: Optional[str] = Field(None, description="Force specific document type")
    company_id: Optional[str] = Field(None, description="Company to associate data with")


@router.post("/smart/process")
async def smart_process_document(request: SmartProcessRequest):
    """
    🧠 Smart Document Processing - Auto-detect and extract sustainability data.
    
    Upload a document (image or text) and the system will:
    1. **Detect** document type (utility bill, flight receipt, etc.)
    2. **Extract** relevant data fields automatically
    3. **Calculate** CO2e emissions
    
    Supported document types:
    - Utility bills (electricity, gas, water)
    - Flight receipts/boarding passes
    - Car rental receipts
    - Fuel receipts
    - Shipping invoices
    - Expense reports
    
    Example with image:
    ```json
    {
        "image_base64": "<base64-encoded-image>",
        "company_id": "xyz-corp-001"
    }
    ```
    
    Example with text:
    ```json
    {
        "text_content": "Pacific Gas & Electric\\nAccount: 12345\\nUsage: 450 kWh\\nAmount Due: $85.50",
        "company_id": "xyz-corp-001"
    }
    ```
    """
    if not request.image_base64 and not request.text_content:
        raise HTTPException(
            status_code=400,
            detail="Either image_base64 or text_content must be provided"
        )
    
    force_type = None
    if request.force_type:
        try:
            force_type = SustainabilityDocumentType(request.force_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document type. Use /smart/document-types for valid options"
            )
    
    try:
        result = await smart_processor.process_document(
            image_base64=request.image_base64,
            text_content=request.text_content,
            force_type=force_type
        )
        
        response = {
            "status": "success",
            "document_type": result.document_type.value,
            "suggested_template": result.template,
            "confidence": result.confidence,
            "extracted_data": result.data,
            "calculated_co2e_kg": result.calculated_co2e_kg,
            "company_id": request.company_id
        }
        
        # Add helpful info
        if result.calculated_co2e_kg:
            response["calculated_co2e_tonnes"] = round(result.calculated_co2e_kg / 1000, 4)
            response["emission_equivalents"] = {
                "trees_needed": round(result.calculated_co2e_kg / 21, 1),
                "car_km": round(result.calculated_co2e_kg / 0.171, 1)
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/smart/process-image")
async def smart_process_image(
    file: UploadFile = File(...),
    company_id: Optional[str] = Form(None),
    force_type: Optional[str] = Form(None)
):
    """
    🖼️ Process a document image with automatic type detection.
    
    Upload any sustainability-related document image:
    - Utility bills
    - Flight receipts
    - Fuel receipts
    - Shipping invoices
    
    The system will:
    1. Extract text using OCR
    2. Classify the document type
    3. Extract structured data
    4. Calculate CO2e emissions
    
    Example:
    ```bash
    curl -X POST http://localhost:8000/api/v1/sustainability/smart/process-image \\
      -F "file=@utility_bill.jpg" \\
      -F "company_id=xyz-corp-001"
    ```
    """
    # Read and encode image
    content = await file.read()
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    force_doc_type = None
    if force_type:
        try:
            force_doc_type = SustainabilityDocumentType(force_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {force_type}")
    
    try:
        result = await smart_processor.process_document(
            image_base64=image_base64,
            force_type=force_doc_type
        )
        
        return {
            "status": "success",
            "filename": file.filename,
            "document_type": result.document_type.value,
            "suggested_template": result.template,
            "confidence": result.confidence,
            "extracted_data": result.data,
            "calculated_co2e_kg": result.calculated_co2e_kg,
            "company_id": company_id,
            "raw_text_preview": result.raw_text[:500] + "..." if len(result.raw_text) > 500 else result.raw_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/smart/classify")
async def smart_classify_document(
    text: str,
):
    """
    📋 Classify document type without full extraction.
    
    Quick classification to determine what type of document this is.
    Useful for routing documents to the correct processing pipeline.
    """
    try:
        classification = await smart_processor._classify_document(text)
        
        return {
            "document_type": classification.document_type.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "suggested_template": classification.suggested_template,
            "hints": classification.extracted_hints
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/smart/batch-process")
async def smart_batch_process(
    files: List[UploadFile] = File(...),
    company_id: Optional[str] = Form(None)
):
    """
    📦 Process multiple documents in batch.
    
    Upload multiple document images and process them all at once.
    Returns results for each document with aggregated totals.
    """
    results = []
    total_co2e = 0
    
    for file in files:
        try:
            content = await file.read()
            image_base64 = base64.b64encode(content).decode('utf-8')
            
            result = await smart_processor.process_document(image_base64=image_base64)
            
            doc_result = {
                "filename": file.filename,
                "status": "success",
                "document_type": result.document_type.value,
                "template": result.template,
                "extracted_data": result.data,
                "co2e_kg": result.calculated_co2e_kg
            }
            
            if result.calculated_co2e_kg:
                total_co2e += result.calculated_co2e_kg
            
            results.append(doc_result)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "company_id": company_id,
        "documents_processed": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "total_co2e_kg": round(total_co2e, 2),
        "total_co2e_tonnes": round(total_co2e / 1000, 4),
        "results": results
    }


import base64


# ==================== Auto Template Generation (Self-Learning) ====================

from modules.sustainability.template_generator import template_generator

# Wire up LLM router
template_generator.set_llm_router(llm_router)


@router.get("/templates/auto")
async def list_auto_templates():
    """
    📋 List all auto-generated templates.
    
    These are templates that were created by the LLM when it encountered
    new document types. The system learns from each new document!
    """
    templates = template_generator.list_templates()
    
    return {
        "total_templates": len(templates),
        "templates": templates,
        "how_it_works": [
            "1. Upload a document the system hasn't seen before",
            "2. LLM analyzes the document structure",
            "3. LLM generates extraction template with fields",
            "4. Template is saved for future documents",
            "5. System gets smarter over time!"
        ]
    }


@router.get("/templates/auto/{template_id}")
async def get_auto_template(template_id: str):
    """
    📄 Get details of a specific auto-generated template.
    """
    template = template_generator.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    return {
        "template": template.to_dict(),
        "emission_factors": {
            k: v for k, v in template_generator.EMISSION_FACTORS.items()
        }
    }


class AutoTemplateRequest(BaseModel):
    """Request to auto-generate a template."""
    document_text: str = Field(..., description="Document text to analyze")
    hint_type: Optional[str] = Field(None, description="Hint about document type")


@router.post("/templates/auto/generate")
async def generate_auto_template(request: AutoTemplateRequest):
    """
    🧠 Auto-Generate Template from Document
    
    The LLM will analyze the document and automatically create a template for
    extracting sustainability data from similar documents in the future.
    
    This is the SELF-LEARNING feature - the system gets smarter with each
    new document type it encounters!
    
    Example:
    ```json
    {
        "document_text": "Carbon Offset Certificate\\nProject: Wind Farm XYZ\\nCredits: 100 tonnes CO2e...",
        "hint_type": "carbon offset certificate"
    }
    ```
    """
    try:
        template = await template_generator.generate_template(
            document_text=request.document_text,
            hint_type=request.hint_type
        )
        
        return {
            "status": "success",
            "message": "Template created successfully! The system can now process similar documents.",
            "template": template.to_dict(),
            "next_steps": [
                f"Use template_id '{template.template_id}' for extraction",
                "Or upload similar documents - they'll be auto-matched",
                "The more documents processed, the smarter the system gets"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template generation failed: {str(e)}")


@router.post("/templates/auto/{template_id}/extract")
async def extract_with_auto_template(
    template_id: str,
    document_text: str
):
    """
    📊 Extract data using a specific auto-generated template.
    
    Use this when you know which template to apply.
    """
    template = template_generator.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    try:
        # Extract data
        extracted = await template_generator.extract_with_template(document_text, template)
        
        # Calculate emissions
        co2e = template_generator.calculate_emissions(extracted, template)
        
        # Update usage count
        template.usage_count += 1
        
        response = {
            "status": "success",
            "template_used": template.name,
            "category": template.category,
            "scope": template.scope,
            "extracted_data": extracted,
            "calculated_co2e_kg": co2e
        }
        
        if co2e:
            response["calculated_co2e_tonnes"] = round(co2e / 1000, 4)
            response["emission_equivalents"] = {
                "trees_needed": round(co2e / 21, 1),
                "car_km": round(co2e / 0.171, 1)
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.delete("/templates/auto/{template_id}")
async def delete_auto_template(template_id: str):
    """
    🗑️ Delete an auto-generated template.
    """
    success = template_generator.delete_template(template_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    return {"status": "success", "message": f"Template {template_id} deleted"}


@router.post("/smart/process-auto")
async def smart_process_with_auto_template(request: SmartProcessRequest):
    """
    🚀 ULTIMATE SMART PROCESSING - Auto-detect, Auto-template, Auto-extract!
    
    This endpoint does EVERYTHING:
    1. First tries to match against built-in document types
    2. If no match, checks auto-generated templates
    3. If still no match, GENERATES A NEW TEMPLATE automatically
    4. Extracts data using the best available template
    5. Calculates emissions
    
    This is TRUE SELF-LEARNING AI!
    
    The more documents you process, the smarter the system becomes.
    """
    if not request.text_content and not request.image_base64:
        raise HTTPException(
            status_code=400,
            detail="Either text_content or image_base64 required"
        )
    
    # Get text content
    if request.text_content:
        text = request.text_content
    elif request.image_base64 and smart_processor.ocr_engine:
        import base64
        image_bytes = base64.b64decode(request.image_base64)
        ocr_result = await smart_processor.ocr_engine.extract_text(image_data=image_bytes)
        text = ocr_result.text
    else:
        raise HTTPException(status_code=400, detail="Cannot process image without OCR engine")
    
    # Step 1: Try built-in smart processor
    try:
        result = await smart_processor.process_document(text_content=text)
        
        if result.document_type.value != "unknown" and result.confidence > 0.7:
            return {
                "status": "success",
                "processing_mode": "built_in_template",
                "document_type": result.document_type.value,
                "template": result.template,
                "confidence": result.confidence,
                "extracted_data": result.data,
                "calculated_co2e_kg": result.calculated_co2e_kg,
                "company_id": request.company_id
            }
    except Exception:
        pass
    
    # Step 2: Try auto-generated templates
    matching_template = template_generator.find_matching_template(text)
    
    if matching_template:
        extracted = await template_generator.extract_with_template(text, matching_template)
        co2e = template_generator.calculate_emissions(extracted, matching_template)
        matching_template.usage_count += 1
        
        return {
            "status": "success",
            "processing_mode": "auto_generated_template",
            "template_id": matching_template.template_id,
            "template_name": matching_template.name,
            "category": matching_template.category,
            "scope": matching_template.scope,
            "confidence": 0.85,
            "extracted_data": extracted,
            "calculated_co2e_kg": co2e,
            "company_id": request.company_id
        }
    
    # Step 3: Generate NEW template automatically!
    try:
        new_template = await template_generator.generate_template(text)
        extracted = await template_generator.extract_with_template(text, new_template)
        co2e = template_generator.calculate_emissions(extracted, new_template)
        
        return {
            "status": "success",
            "processing_mode": "new_template_generated",
            "message": "🎉 New document type learned! Template created for future use.",
            "template_id": new_template.template_id,
            "template_name": new_template.name,
            "category": new_template.category,
            "scope": new_template.scope,
            "fields_discovered": len(new_template.fields),
            "extracted_data": extracted,
            "calculated_co2e_kg": co2e,
            "company_id": request.company_id,
            "learning_note": "The system will now recognize similar documents automatically!"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-processing failed: {str(e)}")


# ==================== UNIFIED DATABASE ENDPOINTS ====================
# These endpoints provide access to the consolidated sustainability database

@router.get("/unified/stats")
async def get_unified_stats(company_id: Optional[str] = None):
    """
    📊 Get comprehensive statistics from the unified database.
    
    Returns:
    - Document counts by status
    - Emissions by scope and category
    - Confidence distribution
    """
    return unified_service.get_stats(company_id)


@router.get("/unified/companies")
async def get_companies():
    """
    🏢 List all companies in the system.
    """
    return {"companies": unified_service.get_companies()}


@router.get("/unified/companies/{company_id}")
async def get_company(company_id: str):
    """
    🏢 Get company details with sustainability summary.
    """
    company = unified_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    
    # Get related data
    footprint = unified_service.get_carbon_footprint(company_id)
    esg = unified_service.get_esg_score(company_id)
    plans = unified_service.get_reduction_plans(company_id)
    
    return {
        "company": company,
        "carbon_footprint": footprint,
        "esg_score": esg,
        "reduction_plans": plans
    }


class CreateCompanyRequest(BaseModel):
    id: Optional[str] = None
    name: str
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    employees: Optional[int] = None
    revenue_usd: Optional[float] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None


@router.post("/unified/companies")
async def create_company(request: CreateCompanyRequest):
    """
    🏢 Create a new company.
    """
    company_id = unified_service.create_company(request.dict())
    return {"company_id": company_id, "status": "created"}


@router.get("/unified/emissions/{company_id}")
async def get_company_emissions(
    company_id: str,
    year: Optional[int] = None
):
    """
    🌍 Get carbon footprint and emissions breakdown for a company.
    """
    footprint = unified_service.get_carbon_footprint(company_id, year)
    history = unified_service.get_emissions_history(company_id)
    
    return {
        "current_footprint": footprint,
        "history": history,
        "emissions_by_category": unified_service.db.get_emissions_by_category(company_id)
    }


@router.get("/unified/knowledge")
async def get_knowledge_base(
    category: Optional[str] = None,
    company_id: Optional[str] = None
):
    """
    📚 List knowledge base documents.
    """
    docs = unified_service.get_knowledge_documents(category, company_id)
    return {"documents": docs, "count": len(docs)}


class AddKnowledgeRequest(BaseModel):
    title: str
    doc_type: str = "reference"
    content: str
    category: Optional[str] = None
    source: Optional[str] = None
    company_id: Optional[str] = None


@router.post("/unified/knowledge")
async def add_knowledge_document(request: AddKnowledgeRequest):
    """
    📚 Add a document to the knowledge base.
    """
    doc_id = unified_service.add_knowledge_document(
        title=request.title,
        doc_type=request.doc_type,
        content=request.content,
        category=request.category,
        source=request.source,
        company_id=request.company_id
    )
    return {"document_id": doc_id, "status": "added"}


@router.get("/unified/reports/{company_id}")
async def get_company_reports(company_id: str):
    """
    📋 Get sustainability reports for a company.
    """
    reports = unified_service.get_reports(company_id)
    return {"reports": reports}


class GenerateReportRequest(BaseModel):
    company_id: str
    report_type: str = "annual_sustainability"
    title: str
    year: int


@router.post("/unified/reports")
async def generate_report(request: GenerateReportRequest):
    """
    📋 Generate a sustainability report.
    """
    # Get company data for the report
    company = unified_service.get_company(request.company_id)
    footprint = unified_service.get_carbon_footprint(request.company_id, request.year)
    esg = unified_service.get_esg_score(request.company_id)
    
    report_content = {
        "company": company,
        "carbon_footprint": footprint,
        "esg_score": esg,
        "generated_at": datetime.now().isoformat(),
        "reporting_period": request.year
    }
    
    report_id = unified_service.create_report(
        company_id=request.company_id,
        report_type=request.report_type,
        title=request.title,
        year=request.year,
        content=report_content
    )
    
    return {"report_id": report_id, "status": "generated"}


@router.get("/unified/audit-log")
async def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100
):
    """
    📜 Get audit log entries for compliance tracking.
    """
    entries = unified_service.get_audit_log(entity_type, entity_id, limit)
    return {"entries": entries, "count": len(entries)}


@router.get("/unified/dashboard/{company_id}")
async def get_dashboard_data(company_id: str):
    """
    📊 Get all dashboard data for a company in one call.
    
    Perfect for populating a sustainability dashboard UI.
    """
    company = unified_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    
    stats = unified_service.get_stats(company_id)
    footprint = unified_service.get_carbon_footprint(company_id)
    esg = unified_service.get_esg_score(company_id)
    plans = unified_service.get_reduction_plans(company_id)
    
    return {
        "company": company,
        "stats": stats,
        "carbon_footprint": footprint,
        "esg_score": esg,
        "reduction_plans": plans,
        "recent_activity": unified_service.get_audit_log(limit=10)
    }

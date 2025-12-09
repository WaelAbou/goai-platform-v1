"""
Sustainability Expert Engine

Comprehensive sustainability analysis including:
- Carbon footprint calculation with verified emission factors
- ESG (Environmental, Social, Governance) scoring
- Industry-specific recommendations
- UN SDG alignment analysis
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math


class ActivityType(str, Enum):
    """Types of activities for carbon calculation."""
    FLIGHT = "flight"
    VEHICLE = "vehicle"
    ELECTRICITY = "electricity"
    NATURAL_GAS = "natural_gas"
    SHIPPING = "shipping"
    DATA_CENTER = "data_center"
    OFFICE = "office"
    MANUFACTURING = "manufacturing"
    WASTE = "waste"
    WATER = "water"


class Industry(str, Enum):
    """Industry categories for recommendations."""
    TECHNOLOGY = "technology"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    CONSTRUCTION = "construction"
    ENERGY = "energy"
    TRANSPORTATION = "transportation"
    AGRICULTURE = "agriculture"
    HOSPITALITY = "hospitality"


@dataclass
class CarbonFootprint:
    """Carbon footprint calculation result."""
    activity: str
    co2e_kg: float
    co2e_tonnes: float
    scope: int  # 1, 2, or 3
    methodology: str
    emission_factor: float
    emission_factor_unit: str
    emission_factor_source: str
    equivalents: Dict[str, str]
    reduction_tips: List[str]
    confidence: str  # "high", "medium", "low"
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity": self.activity,
            "emissions": {
                "co2e_kg": round(self.co2e_kg, 2),
                "co2e_tonnes": round(self.co2e_tonnes, 4),
                "scope": self.scope
            },
            "methodology": {
                "description": self.methodology,
                "emission_factor": self.emission_factor,
                "emission_factor_unit": self.emission_factor_unit,
                "source": self.emission_factor_source,
                "confidence": self.confidence
            },
            "equivalents": self.equivalents,
            "reduction_tips": self.reduction_tips,
            "calculated_at": self.calculated_at.isoformat()
        }


@dataclass
class ESGScore:
    """ESG scoring result."""
    environmental_score: float  # 0-100
    social_score: float  # 0-100
    governance_score: float  # 0-100
    overall_score: float  # 0-100
    rating: str  # "AAA" to "CCC"
    environmental_breakdown: Dict[str, float]
    social_breakdown: Dict[str, float]
    governance_breakdown: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    industry_percentile: Optional[int] = None
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores": {
                "environmental": round(self.environmental_score, 1),
                "social": round(self.social_score, 1),
                "governance": round(self.governance_score, 1),
                "overall": round(self.overall_score, 1)
            },
            "rating": self.rating,
            "breakdown": {
                "environmental": self.environmental_breakdown,
                "social": self.social_breakdown,
                "governance": self.governance_breakdown
            },
            "analysis": {
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "recommendations": self.recommendations
            },
            "industry_percentile": self.industry_percentile,
            "calculated_at": self.calculated_at.isoformat()
        }


@dataclass
class SustainabilityRecommendation:
    """A sustainability recommendation."""
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    effort: str  # "high", "medium", "low"
    category: str  # "energy", "waste", "water", "supply_chain", etc.
    estimated_reduction_percent: Optional[float] = None
    estimated_cost_savings: Optional[str] = None
    timeline: Optional[str] = None
    sdg_alignment: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "effort": self.effort,
            "category": self.category,
            "estimated_reduction_percent": self.estimated_reduction_percent,
            "estimated_cost_savings": self.estimated_cost_savings,
            "timeline": self.timeline,
            "sdg_alignment": self.sdg_alignment
        }


class SustainabilityEngine:
    """
    AI-powered sustainability expert engine.
    
    Provides carbon calculations, ESG scoring, and recommendations
    based on verified emission factors and industry best practices.
    """
    
    # ==================== Emission Factors (kg CO2e per unit) ====================
    # Source: EPA GHG Emission Factors Hub & UK DEFRA 2023
    
    EMISSION_FACTORS = {
        # Aviation (kg CO2e per passenger-km)
        "flight_economy_short": 0.255,      # <1500 km
        "flight_economy_medium": 0.156,     # 1500-4000 km
        "flight_economy_long": 0.150,       # >4000 km
        "flight_business": 0.434,           # Business class multiplier
        "flight_first": 0.599,              # First class multiplier
        
        # Ground Transportation (kg CO2e per km)
        "car_petrol_small": 0.142,
        "car_petrol_medium": 0.171,
        "car_petrol_large": 0.209,
        "car_diesel_medium": 0.168,
        "car_electric": 0.053,              # Grid average
        "car_hybrid": 0.120,
        "bus": 0.089,
        "train_national": 0.035,
        "train_international": 0.006,
        
        # Electricity (kg CO2e per kWh) - varies by grid
        "electricity_us_avg": 0.417,
        "electricity_uk": 0.207,
        "electricity_eu_avg": 0.276,
        "electricity_renewable": 0.0,
        "electricity_coal": 0.91,
        "electricity_natural_gas": 0.40,
        
        # Natural Gas (kg CO2e per therm)
        "natural_gas": 5.31,
        
        # Shipping (kg CO2e per tonne-km)
        "shipping_sea_container": 0.016,
        "shipping_air_freight": 0.602,
        "shipping_road_freight": 0.107,
        "shipping_rail_freight": 0.028,
        
        # Data Centers (kg CO2e per kWh)
        "data_center_avg": 0.50,            # Including cooling overhead
        
        # Water (kg CO2e per cubic meter)
        "water_supply": 0.344,
        "water_treatment": 0.708,
        
        # Waste (kg CO2e per kg)
        "waste_landfill": 0.587,
        "waste_incineration": 0.021,
        "waste_recycled": -0.050,           # Avoided emissions
        "waste_composted": 0.010,
    }
    
    # ==================== ESG Weights ====================
    
    ESG_WEIGHTS = {
        "environmental": {
            "carbon_emissions": 0.25,
            "renewable_energy": 0.20,
            "waste_management": 0.15,
            "water_usage": 0.15,
            "biodiversity": 0.10,
            "pollution_prevention": 0.15
        },
        "social": {
            "employee_welfare": 0.20,
            "diversity_inclusion": 0.20,
            "community_impact": 0.15,
            "health_safety": 0.20,
            "human_rights": 0.15,
            "customer_satisfaction": 0.10
        },
        "governance": {
            "board_independence": 0.20,
            "executive_compensation": 0.15,
            "shareholder_rights": 0.15,
            "ethics_compliance": 0.20,
            "transparency": 0.15,
            "risk_management": 0.15
        }
    }
    
    # ==================== UN SDGs ====================
    
    UN_SDGS = {
        1: {"name": "No Poverty", "icon": "🏠"},
        2: {"name": "Zero Hunger", "icon": "🌾"},
        3: {"name": "Good Health and Well-being", "icon": "❤️"},
        4: {"name": "Quality Education", "icon": "📚"},
        5: {"name": "Gender Equality", "icon": "⚖️"},
        6: {"name": "Clean Water and Sanitation", "icon": "💧"},
        7: {"name": "Affordable and Clean Energy", "icon": "⚡"},
        8: {"name": "Decent Work and Economic Growth", "icon": "💼"},
        9: {"name": "Industry, Innovation and Infrastructure", "icon": "🏭"},
        10: {"name": "Reduced Inequalities", "icon": "🤝"},
        11: {"name": "Sustainable Cities and Communities", "icon": "🏙️"},
        12: {"name": "Responsible Consumption and Production", "icon": "♻️"},
        13: {"name": "Climate Action", "icon": "🌍"},
        14: {"name": "Life Below Water", "icon": "🐋"},
        15: {"name": "Life on Land", "icon": "🌳"},
        16: {"name": "Peace, Justice and Strong Institutions", "icon": "🕊️"},
        17: {"name": "Partnerships for the Goals", "icon": "🤲"}
    }
    
    def __init__(self):
        self.llm_router = None
        self.rag_engine = None
        self.memory_service = None
        
    def set_llm_router(self, router):
        """Set the LLM router for conversational features."""
        self.llm_router = router
        
    def set_rag_engine(self, engine):
        """Set RAG engine for knowledge retrieval."""
        self.rag_engine = engine
        
    def set_memory_service(self, service):
        """Set memory service for conversation context."""
        self.memory_service = service
    
    # ==================== Carbon Footprint Calculations ====================
    
    def calculate_flight_emissions(
        self,
        distance_km: float,
        travel_class: str = "economy",
        round_trip: bool = False,
        passengers: int = 1
    ) -> CarbonFootprint:
        """
        Calculate carbon emissions for air travel.
        
        Args:
            distance_km: One-way distance in kilometers
            travel_class: "economy", "business", or "first"
            round_trip: Whether this is a round trip
            passengers: Number of passengers
        """
        # Select emission factor based on distance
        if distance_km < 1500:
            base_factor = self.EMISSION_FACTORS["flight_economy_short"]
            distance_category = "short-haul"
        elif distance_km < 4000:
            base_factor = self.EMISSION_FACTORS["flight_economy_medium"]
            distance_category = "medium-haul"
        else:
            base_factor = self.EMISSION_FACTORS["flight_economy_long"]
            distance_category = "long-haul"
        
        # Adjust for travel class
        class_multipliers = {
            "economy": 1.0,
            "premium_economy": 1.6,
            "business": 2.9,
            "first": 4.0
        }
        class_multiplier = class_multipliers.get(travel_class.lower(), 1.0)
        
        # Calculate total distance
        total_distance = distance_km * (2 if round_trip else 1)
        
        # Calculate emissions
        co2e_kg = total_distance * base_factor * class_multiplier * passengers
        
        return CarbonFootprint(
            activity=f"Flight ({distance_category}, {travel_class})",
            co2e_kg=co2e_kg,
            co2e_tonnes=co2e_kg / 1000,
            scope=3,
            methodology=f"Distance-based calculation using DEFRA {distance_category} factors with class adjustment",
            emission_factor=base_factor * class_multiplier,
            emission_factor_unit="kg CO2e/passenger-km",
            emission_factor_source="UK DEFRA 2023",
            confidence="high",
            equivalents=self._get_equivalents(co2e_kg),
            reduction_tips=[
                "Consider video conferencing instead of travel",
                "Choose economy class (70% lower emissions than business)",
                "Book direct flights (takeoff uses most fuel)",
                "Offset remaining emissions through verified programs"
            ]
        )
    
    def calculate_vehicle_emissions(
        self,
        distance_km: float,
        vehicle_type: str = "car_petrol_medium",
        passengers: int = 1
    ) -> CarbonFootprint:
        """Calculate carbon emissions for ground transportation."""
        
        factor = self.EMISSION_FACTORS.get(vehicle_type, 
                                           self.EMISSION_FACTORS["car_petrol_medium"])
        
        # Per-passenger emissions
        co2e_kg = (distance_km * factor) / passengers
        
        vehicle_names = {
            "car_petrol_small": "Small petrol car",
            "car_petrol_medium": "Medium petrol car",
            "car_petrol_large": "Large petrol car",
            "car_diesel_medium": "Diesel car",
            "car_electric": "Electric car",
            "car_hybrid": "Hybrid car",
            "bus": "Bus",
            "train_national": "National train",
            "train_international": "International train"
        }
        
        return CarbonFootprint(
            activity=f"{vehicle_names.get(vehicle_type, vehicle_type)} travel",
            co2e_kg=co2e_kg,
            co2e_tonnes=co2e_kg / 1000,
            scope=1 if "car" in vehicle_type else 3,
            methodology="Distance-based calculation using DEFRA vehicle factors",
            emission_factor=factor,
            emission_factor_unit="kg CO2e/vehicle-km",
            emission_factor_source="UK DEFRA 2023",
            confidence="high",
            equivalents=self._get_equivalents(co2e_kg),
            reduction_tips=[
                "Consider carpooling to share emissions",
                "Switch to electric or hybrid vehicle",
                "Use public transportation when possible",
                "Combine trips to reduce total distance"
            ]
        )
    
    def calculate_electricity_emissions(
        self,
        kwh: float,
        grid: str = "us_avg",
        renewable_percent: float = 0
    ) -> CarbonFootprint:
        """Calculate carbon emissions from electricity consumption."""
        
        grid_factor = self.EMISSION_FACTORS.get(f"electricity_{grid}",
                                                self.EMISSION_FACTORS["electricity_us_avg"])
        
        # Adjust for renewable energy
        effective_factor = grid_factor * (1 - renewable_percent / 100)
        co2e_kg = kwh * effective_factor
        
        grid_names = {
            "us_avg": "US average grid",
            "uk": "UK grid",
            "eu_avg": "EU average grid",
            "renewable": "100% renewable"
        }
        
        return CarbonFootprint(
            activity=f"Electricity consumption ({grid_names.get(grid, grid)})",
            co2e_kg=co2e_kg,
            co2e_tonnes=co2e_kg / 1000,
            scope=2,
            methodology=f"Grid-average factor adjusted for {renewable_percent}% renewable",
            emission_factor=effective_factor,
            emission_factor_unit="kg CO2e/kWh",
            emission_factor_source="EPA eGRID / UK DEFRA 2023",
            confidence="medium",
            equivalents=self._get_equivalents(co2e_kg),
            reduction_tips=[
                "Switch to a renewable energy provider",
                "Install solar panels or purchase RECs",
                "Improve energy efficiency (LED lighting, insulation)",
                "Use smart meters to identify waste"
            ]
        )
    
    def calculate_natural_gas_emissions(
        self,
        therms: float
    ) -> CarbonFootprint:
        """Calculate carbon emissions from natural gas consumption."""
        
        factor = self.EMISSION_FACTORS["natural_gas"]
        co2e_kg = therms * factor
        
        return CarbonFootprint(
            activity="Natural gas consumption",
            co2e_kg=co2e_kg,
            co2e_tonnes=co2e_kg / 1000,
            scope=1,
            methodology="Direct combustion factor",
            emission_factor=factor,
            emission_factor_unit="kg CO2e/therm",
            emission_factor_source="EPA GHG Emission Factors Hub",
            confidence="high",
            equivalents=self._get_equivalents(co2e_kg),
            reduction_tips=[
                "Improve insulation to reduce heating needs",
                "Switch to electric heat pump",
                "Install smart thermostat",
                "Consider renewable natural gas (RNG)"
            ]
        )
    
    def calculate_shipping_emissions(
        self,
        weight_tonnes: float,
        distance_km: float,
        mode: str = "sea_container"
    ) -> CarbonFootprint:
        """Calculate carbon emissions for shipping/freight."""
        
        factor = self.EMISSION_FACTORS.get(f"shipping_{mode}",
                                          self.EMISSION_FACTORS["shipping_sea_container"])
        
        co2e_kg = weight_tonnes * distance_km * factor
        
        mode_names = {
            "sea_container": "Sea freight (container)",
            "air_freight": "Air freight",
            "road_freight": "Road freight (truck)",
            "rail_freight": "Rail freight"
        }
        
        return CarbonFootprint(
            activity=f"{mode_names.get(mode, mode)}",
            co2e_kg=co2e_kg,
            co2e_tonnes=co2e_kg / 1000,
            scope=3,
            methodology="Weight-distance based calculation",
            emission_factor=factor,
            emission_factor_unit="kg CO2e/tonne-km",
            emission_factor_source="UK DEFRA 2023",
            confidence="medium",
            equivalents=self._get_equivalents(co2e_kg),
            reduction_tips=[
                "Prefer sea over air freight (95% lower emissions)",
                "Consolidate shipments to improve efficiency",
                "Choose suppliers closer to reduce distance",
                "Use rail freight where available"
            ]
        )
    
    def _get_equivalents(self, co2e_kg: float) -> Dict[str, str]:
        """Get relatable equivalents for CO2 emissions."""
        return {
            "car_km": f"{co2e_kg / 0.171:,.0f} km driven in average car",
            "tree_years": f"{co2e_kg / 21:,.1f} trees growing for 1 year to absorb",
            "home_days": f"{co2e_kg / 14.5:,.1f} days of average home energy use",
            "smartphones_charged": f"{co2e_kg / 0.008:,.0f} smartphone charges",
            "beef_kg": f"{co2e_kg / 27:,.1f} kg of beef production"
        }
    
    # ==================== ESG Scoring ====================
    
    def calculate_esg_score(
        self,
        environmental_data: Dict[str, float],
        social_data: Dict[str, float],
        governance_data: Dict[str, float],
        industry: Optional[str] = None
    ) -> ESGScore:
        """
        Calculate comprehensive ESG score.
        
        Args:
            environmental_data: Dict with keys like:
                - renewable_energy_percent (0-100)
                - waste_recycled_percent (0-100)
                - carbon_intensity (tonnes CO2e per $1M revenue)
                - water_efficiency_score (0-100)
            social_data: Dict with keys like:
                - employee_satisfaction (0-100)
                - diversity_score (0-100)
                - safety_incident_rate (lower is better)
                - community_investment_percent (0-100)
            governance_data: Dict with keys like:
                - board_independence_percent (0-100)
                - ethics_violations (count, lower is better)
                - transparency_score (0-100)
                - risk_management_score (0-100)
        """
        # Calculate Environmental Score
        e_score = self._calculate_environmental_score(environmental_data)
        
        # Calculate Social Score
        s_score = self._calculate_social_score(social_data)
        
        # Calculate Governance Score
        g_score = self._calculate_governance_score(governance_data)
        
        # Overall weighted score (equal weights)
        overall = (e_score["score"] + s_score["score"] + g_score["score"]) / 3
        
        # Determine rating (AAA to CCC)
        rating = self._get_esg_rating(overall)
        
        # Generate analysis
        strengths, weaknesses = self._analyze_esg_scores(
            e_score, s_score, g_score
        )
        
        recommendations = self._generate_esg_recommendations(
            e_score, s_score, g_score, industry
        )
        
        return ESGScore(
            environmental_score=e_score["score"],
            social_score=s_score["score"],
            governance_score=g_score["score"],
            overall_score=overall,
            rating=rating,
            environmental_breakdown=e_score["breakdown"],
            social_breakdown=s_score["breakdown"],
            governance_breakdown=g_score["breakdown"],
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            industry_percentile=self._estimate_industry_percentile(overall, industry)
        )
    
    def _calculate_environmental_score(self, data: Dict[str, float]) -> Dict:
        """Calculate environmental pillar score."""
        breakdown = {}
        
        # Renewable energy (0-100 input maps to 0-100 score)
        breakdown["renewable_energy"] = data.get("renewable_energy_percent", 0)
        
        # Waste management
        breakdown["waste_management"] = data.get("waste_recycled_percent", 0)
        
        # Carbon intensity (lower is better, normalize to 0-100)
        carbon_intensity = data.get("carbon_intensity", 100)
        breakdown["carbon_emissions"] = max(0, 100 - carbon_intensity)
        
        # Water efficiency
        breakdown["water_usage"] = data.get("water_efficiency_score", 50)
        
        # Default scores for missing data
        breakdown["biodiversity"] = data.get("biodiversity_score", 50)
        breakdown["pollution_prevention"] = data.get("pollution_score", 50)
        
        # Weighted score
        score = sum(
            breakdown[k] * self.ESG_WEIGHTS["environmental"].get(k, 0.1)
            for k in breakdown
        )
        
        return {"score": score, "breakdown": breakdown}
    
    def _calculate_social_score(self, data: Dict[str, float]) -> Dict:
        """Calculate social pillar score."""
        breakdown = {}
        
        breakdown["employee_welfare"] = data.get("employee_satisfaction", 50)
        breakdown["diversity_inclusion"] = data.get("diversity_score", 50)
        
        # Safety (lower incident rate is better)
        incident_rate = data.get("safety_incident_rate", 5)
        breakdown["health_safety"] = max(0, 100 - incident_rate * 10)
        
        breakdown["community_impact"] = data.get("community_investment_percent", 0) * 10
        breakdown["human_rights"] = data.get("human_rights_score", 50)
        breakdown["customer_satisfaction"] = data.get("customer_satisfaction", 50)
        
        score = sum(
            breakdown[k] * self.ESG_WEIGHTS["social"].get(k, 0.1)
            for k in breakdown
        )
        
        return {"score": min(100, score), "breakdown": breakdown}
    
    def _calculate_governance_score(self, data: Dict[str, float]) -> Dict:
        """Calculate governance pillar score."""
        breakdown = {}
        
        breakdown["board_independence"] = data.get("board_independence_percent", 50)
        
        # Executive compensation (ratio to median employee, lower is better)
        exec_ratio = data.get("executive_pay_ratio", 200)
        breakdown["executive_compensation"] = max(0, 100 - exec_ratio / 5)
        
        breakdown["shareholder_rights"] = data.get("shareholder_rights_score", 50)
        
        # Ethics violations (lower is better)
        violations = data.get("ethics_violations", 0)
        breakdown["ethics_compliance"] = max(0, 100 - violations * 20)
        
        breakdown["transparency"] = data.get("transparency_score", 50)
        breakdown["risk_management"] = data.get("risk_management_score", 50)
        
        score = sum(
            breakdown[k] * self.ESG_WEIGHTS["governance"].get(k, 0.1)
            for k in breakdown
        )
        
        return {"score": min(100, score), "breakdown": breakdown}
    
    def _get_esg_rating(self, score: float) -> str:
        """Convert numeric score to letter rating."""
        if score >= 85:
            return "AAA"
        elif score >= 75:
            return "AA"
        elif score >= 65:
            return "A"
        elif score >= 55:
            return "BBB"
        elif score >= 45:
            return "BB"
        elif score >= 35:
            return "B"
        elif score >= 25:
            return "CCC"
        else:
            return "CC"
    
    def _analyze_esg_scores(
        self,
        e_score: Dict,
        s_score: Dict,
        g_score: Dict
    ) -> tuple:
        """Identify strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        # Analyze each pillar
        for pillar_name, pillar_data in [
            ("Environmental", e_score),
            ("Social", s_score),
            ("Governance", g_score)
        ]:
            for metric, value in pillar_data["breakdown"].items():
                metric_name = metric.replace("_", " ").title()
                if value >= 70:
                    strengths.append(f"{pillar_name}: Strong {metric_name} ({value:.0f}/100)")
                elif value < 40:
                    weaknesses.append(f"{pillar_name}: Weak {metric_name} ({value:.0f}/100)")
        
        return strengths[:5], weaknesses[:5]  # Top 5 each
    
    def _generate_esg_recommendations(
        self,
        e_score: Dict,
        s_score: Dict,
        g_score: Dict,
        industry: Optional[str]
    ) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []
        
        # Environmental recommendations
        if e_score["breakdown"].get("renewable_energy", 0) < 50:
            recommendations.append(
                "🔋 Increase renewable energy usage to 50%+ (high impact on E score)"
            )
        if e_score["breakdown"].get("waste_management", 0) < 60:
            recommendations.append(
                "♻️ Implement circular economy practices to improve waste diversion"
            )
        
        # Social recommendations
        if s_score["breakdown"].get("diversity_inclusion", 0) < 50:
            recommendations.append(
                "👥 Develop diversity and inclusion programs with measurable targets"
            )
        if s_score["breakdown"].get("health_safety", 0) < 70:
            recommendations.append(
                "🦺 Strengthen workplace safety programs to reduce incident rate"
            )
        
        # Governance recommendations
        if g_score["breakdown"].get("board_independence", 0) < 60:
            recommendations.append(
                "📋 Increase board independence to 60%+ with diverse expertise"
            )
        if g_score["breakdown"].get("transparency", 0) < 60:
            recommendations.append(
                "📊 Publish annual sustainability report following GRI standards"
            )
        
        return recommendations[:6]  # Top 6 recommendations
    
    def _estimate_industry_percentile(
        self,
        score: float,
        industry: Optional[str]
    ) -> int:
        """Estimate percentile ranking within industry."""
        # Industry average ESG scores (simplified)
        industry_averages = {
            "technology": 62,
            "finance": 58,
            "healthcare": 55,
            "manufacturing": 48,
            "energy": 45,
            "retail": 52,
            "construction": 42
        }
        
        avg = industry_averages.get(industry, 50)
        
        # Estimate percentile using normal distribution approximation
        z_score = (score - avg) / 15  # Assume std dev of 15
        percentile = int(50 + 50 * math.erf(z_score / math.sqrt(2)))
        
        return max(1, min(99, percentile))
    
    # ==================== Recommendations Engine ====================
    
    def get_industry_recommendations(
        self,
        industry: str,
        focus_area: Optional[str] = None,
        company_size: str = "medium"
    ) -> List[SustainabilityRecommendation]:
        """Get industry-specific sustainability recommendations."""
        
        recommendations = []
        
        # Industry-specific recommendations
        industry_recs = {
            "technology": [
                SustainabilityRecommendation(
                    title="Green Data Centers",
                    description="Transition to renewable-powered data centers with efficient cooling",
                    impact="high",
                    effort="high",
                    category="energy",
                    estimated_reduction_percent=40,
                    estimated_cost_savings="15-25% on energy costs",
                    timeline="12-24 months",
                    sdg_alignment=[7, 9, 13]
                ),
                SustainabilityRecommendation(
                    title="E-Waste Program",
                    description="Implement comprehensive electronics recycling and refurbishment",
                    impact="medium",
                    effort="low",
                    category="waste",
                    estimated_reduction_percent=20,
                    timeline="3-6 months",
                    sdg_alignment=[12]
                ),
                SustainabilityRecommendation(
                    title="Remote Work Policy",
                    description="Enable flexible remote work to reduce commuting emissions",
                    impact="medium",
                    effort="low",
                    category="transportation",
                    estimated_reduction_percent=15,
                    estimated_cost_savings="$5,000-10,000 per employee annually",
                    timeline="1-3 months",
                    sdg_alignment=[8, 11, 13]
                ),
            ],
            "manufacturing": [
                SustainabilityRecommendation(
                    title="Process Electrification",
                    description="Replace fossil fuel processes with electric alternatives",
                    impact="high",
                    effort="high",
                    category="energy",
                    estimated_reduction_percent=50,
                    timeline="24-36 months",
                    sdg_alignment=[7, 9, 13]
                ),
                SustainabilityRecommendation(
                    title="Circular Materials",
                    description="Design products for disassembly and use recycled materials",
                    impact="high",
                    effort="medium",
                    category="materials",
                    estimated_reduction_percent=30,
                    timeline="12-18 months",
                    sdg_alignment=[9, 12]
                ),
                SustainabilityRecommendation(
                    title="Supplier Standards",
                    description="Implement sustainability requirements for supply chain",
                    impact="high",
                    effort="medium",
                    category="supply_chain",
                    estimated_reduction_percent=25,
                    timeline="6-12 months",
                    sdg_alignment=[8, 12, 17]
                ),
            ],
            "retail": [
                SustainabilityRecommendation(
                    title="Sustainable Packaging",
                    description="Switch to recyclable/compostable packaging materials",
                    impact="medium",
                    effort="medium",
                    category="packaging",
                    estimated_reduction_percent=25,
                    timeline="6-12 months",
                    sdg_alignment=[12, 14]
                ),
                SustainabilityRecommendation(
                    title="Local Sourcing",
                    description="Increase locally sourced products to reduce transport emissions",
                    impact="medium",
                    effort="medium",
                    category="supply_chain",
                    estimated_reduction_percent=20,
                    timeline="6-12 months",
                    sdg_alignment=[8, 12, 13]
                ),
            ],
            "finance": [
                SustainabilityRecommendation(
                    title="ESG Integration",
                    description="Integrate ESG factors into investment decisions",
                    impact="high",
                    effort="medium",
                    category="investment",
                    timeline="6-12 months",
                    sdg_alignment=[8, 13, 17]
                ),
                SustainabilityRecommendation(
                    title="Paperless Operations",
                    description="Digitize all customer communications and internal processes",
                    impact="low",
                    effort="low",
                    category="operations",
                    estimated_reduction_percent=5,
                    timeline="3-6 months",
                    sdg_alignment=[12, 15]
                ),
            ]
        }
        
        # Get industry-specific or default recommendations
        recommendations = industry_recs.get(
            industry.lower(),
            self._get_universal_recommendations()
        )
        
        # Filter by focus area if specified
        if focus_area:
            recommendations = [
                r for r in recommendations
                if focus_area.lower() in r.category.lower()
            ]
        
        return recommendations
    
    def _get_universal_recommendations(self) -> List[SustainabilityRecommendation]:
        """Get recommendations applicable to all industries."""
        return [
            SustainabilityRecommendation(
                title="Renewable Energy Transition",
                description="Switch to 100% renewable electricity through PPAs or green tariffs",
                impact="high",
                effort="medium",
                category="energy",
                estimated_reduction_percent=40,
                timeline="6-12 months",
                sdg_alignment=[7, 13]
            ),
            SustainabilityRecommendation(
                title="Employee Commute Program",
                description="Incentivize sustainable commuting (EV, transit, cycling)",
                impact="medium",
                effort="low",
                category="transportation",
                estimated_reduction_percent=15,
                timeline="3-6 months",
                sdg_alignment=[11, 13]
            ),
            SustainabilityRecommendation(
                title="Science-Based Targets",
                description="Commit to SBTi-validated emissions reduction targets",
                impact="high",
                effort="medium",
                category="strategy",
                timeline="6-12 months",
                sdg_alignment=[13, 17]
            ),
        ]
    
    # ==================== Standards & SDGs ====================
    
    def get_supported_standards(self) -> List[Dict[str, str]]:
        """Get list of supported sustainability standards."""
        return [
            {
                "name": "GRI Standards",
                "full_name": "Global Reporting Initiative",
                "description": "Most widely used sustainability reporting standards",
                "url": "https://www.globalreporting.org/"
            },
            {
                "name": "TCFD",
                "full_name": "Task Force on Climate-related Financial Disclosures",
                "description": "Climate risk disclosure framework",
                "url": "https://www.fsb-tcfd.org/"
            },
            {
                "name": "CDP",
                "full_name": "Carbon Disclosure Project",
                "description": "Environmental disclosure system",
                "url": "https://www.cdp.net/"
            },
            {
                "name": "SBTi",
                "full_name": "Science Based Targets initiative",
                "description": "Science-based emissions reduction targets",
                "url": "https://sciencebasedtargets.org/"
            },
            {
                "name": "ISO 14001",
                "full_name": "Environmental Management System",
                "description": "Environmental management certification",
                "url": "https://www.iso.org/iso-14001-environmental-management.html"
            },
            {
                "name": "UN SDGs",
                "full_name": "United Nations Sustainable Development Goals",
                "description": "17 global goals for sustainable development",
                "url": "https://sdgs.un.org/"
            }
        ]
    
    def get_sdgs(self) -> Dict[int, Dict[str, str]]:
        """Get UN Sustainable Development Goals information."""
        return self.UN_SDGS
    
    # ==================== Conversational Interface ====================
    
    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        Process a sustainability question with AI.
        
        Uses LLM with sustainability expertise and optionally RAG
        for document-grounded responses.
        
        Args:
            message: User's question
            context: Optional context (industry, company_size, etc.)
            conversation_id: For conversation tracking
            use_rag: Whether to retrieve relevant documents (default: True)
        """
        if not self.llm_router:
            return {
                "response": "LLM not configured. Please set up the LLM router.",
                "error": True
            }
        
        # Retrieve relevant documents if RAG is enabled
        rag_context = ""
        sources = []
        
        if use_rag and self.rag_engine:
            try:
                # Search for relevant sustainability documents
                rag_result = await self.rag_engine.query(
                    query=message,
                    top_k=5,
                    include_sources=True
                )
                
                if rag_result.get("sources"):
                    sources = rag_result["sources"]
                    # Build context from retrieved documents
                    doc_texts = []
                    for i, source in enumerate(sources[:3], 1):
                        content = source.get("content", source.get("text", ""))[:500]
                        doc_name = source.get("metadata", {}).get("filename", f"Document {i}")
                        doc_texts.append(f"[{doc_name}]: {content}")
                    
                    if doc_texts:
                        rag_context = "\n\n📚 RELEVANT DOCUMENTS:\n" + "\n\n".join(doc_texts)
                        
            except Exception as e:
                # Continue without RAG if it fails
                pass
        
        # Build system prompt
        system_prompt = """You are an expert sustainability advisor with deep knowledge of:
- Carbon footprint calculation and reduction strategies
- ESG (Environmental, Social, Governance) frameworks
- Sustainability standards (GRI, TCFD, CDP, SBTi, ISO 14001)
- UN Sustainable Development Goals (SDGs)
- Industry-specific best practices
- Climate science and environmental regulations

When answering questions:
1. Provide accurate, actionable advice
2. Cite relevant standards and frameworks
3. Include specific metrics and targets where applicable
4. Suggest practical implementation steps
5. Mention relevant SDGs when appropriate
6. Be honest about limitations and uncertainties
7. If document context is provided, reference it in your answer

Always prioritize science-based information and avoid greenwashing claims."""

        # Add user context if provided
        context_str = ""
        if context:
            if context.get("industry"):
                context_str += f"\nUser's industry: {context['industry']}"
            if context.get("company_size"):
                context_str += f"\nCompany size: {context['company_size']}"
            if context.get("current_initiatives"):
                context_str += f"\nCurrent initiatives: {context['current_initiatives']}"
        
        if context_str:
            system_prompt += f"\n\nUser context:{context_str}"
        
        # Add RAG context to the user message
        user_message = message
        if rag_context:
            user_message = f"{message}\n{rag_context}"
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )
            
            if response.get("status") == "error":
                return {
                    "response": f"LLM error: {response.get('error', 'Unknown error')}",
                    "error": True
                }
            
            result = {
                "response": response.get("content", ""),
                "conversation_id": conversation_id,
                "context_used": context,
                "rag_enabled": use_rag and bool(self.rag_engine)
            }
            
            # Include sources if RAG was used
            if sources:
                result["sources"] = [
                    {
                        "document": s.get("metadata", {}).get("filename", "Unknown"),
                        "relevance": s.get("score", 0)
                    }
                    for s in sources[:3]
                ]
            
            return result
            
        except Exception as e:
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "error": True
            }
    
    async def chat_with_docs(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat with explicit RAG - always retrieves documents.
        Alias for chat(use_rag=True).
        """
        return await self.chat(message, context, use_rag=True)


# Singleton instance
sustainability_engine = SustainabilityEngine()


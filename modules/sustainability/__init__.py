"""
Sustainability Expert Module

AI-powered sustainability advisor providing:
- Carbon footprint calculations
- ESG scoring and analysis
- Industry-specific recommendations
- Regulatory guidance (GRI, TCFD, CDP, SBTi)
"""

from .engine import (
    SustainabilityEngine,
    sustainability_engine,
    CarbonFootprint,
    ESGScore,
    SustainabilityRecommendation
)

__all__ = [
    "SustainabilityEngine",
    "sustainability_engine",
    "CarbonFootprint",
    "ESGScore",
    "SustainabilityRecommendation"
]


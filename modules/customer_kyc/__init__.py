"""
Customer KYC Module

AI-powered Know Your Customer verification system.
Handles document validation, risk assessment, and compliance checking.

Business Owner: Compliance & Risk Management
Version: 1.0.0
"""

from .engine import KYCEngine, kyc_engine
from .models import (
    KYCRequest,
    KYCResponse,
    KYCDocument,
    KYCCustomer,
    RiskLevel,
    VerificationStatus,
    DocumentType,
)

__all__ = [
    "KYCEngine",
    "kyc_engine",
    "KYCRequest",
    "KYCResponse",
    "KYCDocument",
    "KYCCustomer",
    "RiskLevel",
    "VerificationStatus",
    "DocumentType",
]


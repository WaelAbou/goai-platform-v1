"""
Customer KYC Models

Pydantic models for KYC verification requests and responses.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime, date


class DocumentType(str, Enum):
    """Supported identity document types."""
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    PROOF_OF_ADDRESS = "proof_of_address"
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"


class RiskLevel(str, Enum):
    """Customer risk classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    """Verification outcome status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    ESCALATED = "escalated"


class KYCDocument(BaseModel):
    """Identity document for verification."""
    document_type: DocumentType
    document_number: Optional[str] = None
    issuing_country: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    content: str = Field(..., description="Document text content or base64 image")
    

class KYCCustomer(BaseModel):
    """Customer information for KYC."""
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    source_of_funds: Optional[str] = None


class KYCRequest(BaseModel):
    """KYC verification request."""
    customer: KYCCustomer
    documents: List[KYCDocument]
    verification_type: str = Field(default="standard", description="standard, enhanced, simplified")
    notes: Optional[str] = None
    
    @validator('documents')
    def validate_documents(cls, v):
        if not v or len(v) < 1:
            raise ValueError('At least one document is required')
        return v


class DocumentVerification(BaseModel):
    """Result of individual document verification."""
    document_type: DocumentType
    is_valid: bool
    confidence: float = Field(..., ge=0, le=1)
    extracted_data: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    

class RiskAssessment(BaseModel):
    """Risk assessment result."""
    risk_level: RiskLevel
    risk_score: int = Field(..., ge=0, le=100)
    risk_factors: List[str] = Field(default_factory=list)
    pep_match: bool = False
    sanctions_match: bool = False
    adverse_media: bool = False


class ComplianceCheck(BaseModel):
    """Compliance check result."""
    is_compliant: bool
    checks_passed: List[str] = Field(default_factory=list)
    checks_failed: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)


class KYCResponse(BaseModel):
    """Complete KYC verification response."""
    verification_id: str
    customer_id: str
    status: VerificationStatus
    
    # Verification results
    document_verifications: List[DocumentVerification]
    risk_assessment: RiskAssessment
    compliance_check: ComplianceCheck
    
    # Summary
    overall_score: int = Field(..., ge=0, le=100)
    recommendation: str
    summary: str
    
    # Actions
    required_actions: List[str] = Field(default_factory=list)
    next_review_date: Optional[datetime] = None
    
    # Audit
    verified_by: str = "AI System"
    verified_at: datetime
    processing_time_ms: int
    
    # Metadata
    model_used: str
    confidence: float


class KYCCase(BaseModel):
    """KYC case for database storage."""
    id: str
    customer_id: str
    user_id: str
    status: VerificationStatus
    risk_level: RiskLevel
    overall_score: int
    request_data: dict
    response_data: dict
    created_at: datetime
    updated_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None


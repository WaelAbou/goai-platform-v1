"""
Customer KYC API Router

RESTful API endpoints for KYC verification.
All endpoints require authentication.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

from modules.customer_kyc import (
    kyc_engine,
    KYCRequest,
    KYCResponse,
    KYCDocument,
    KYCCustomer,
    DocumentType,
    RiskLevel,
    VerificationStatus,
)
from core.auth import get_user_id_flexible
from core.llm.router import llm_router

# Initialize engine with LLM
kyc_engine.set_llm_router(llm_router)

router = APIRouter(prefix="/kyc", tags=["Customer KYC"])


# === REQUEST MODELS ===

class DocumentInput(BaseModel):
    """Document input for API."""
    document_type: DocumentType
    document_number: Optional[str] = None
    issuing_country: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    content: str = Field(..., description="Document text content")


class CustomerInput(BaseModel):
    """Customer input for API."""
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    source_of_funds: Optional[str] = None


class VerifyRequest(BaseModel):
    """KYC verification request."""
    customer: CustomerInput
    documents: List[DocumentInput]
    verification_type: str = Field(default="standard")
    model: str = Field(default="gpt-4o-mini")
    notes: Optional[str] = None


class UpdateCaseRequest(BaseModel):
    """Request to update a KYC case."""
    status: Optional[VerificationStatus] = None
    reviewed_by: Optional[str] = None
    notes: Optional[str] = None


# === ENDPOINTS ===

@router.post("/verify", response_model=KYCResponse)
async def verify_customer(
    request: VerifyRequest,
    user_id: str = Depends(get_user_id_flexible)
):
    """
    Perform KYC verification for a customer.
    
    This endpoint:
    1. Validates all provided documents
    2. Assesses customer risk level
    3. Checks compliance requirements
    4. Returns verification decision and report
    
    **Verification Types:**
    - `standard`: Basic KYC checks
    - `enhanced`: Additional due diligence for high-risk
    - `simplified`: Minimal checks for low-risk
    """
    try:
        # Convert to internal models
        customer = KYCCustomer(
            first_name=request.customer.first_name,
            last_name=request.customer.last_name,
            date_of_birth=request.customer.date_of_birth,
            nationality=request.customer.nationality,
            email=request.customer.email,
            phone=request.customer.phone,
            address=request.customer.address,
            occupation=request.customer.occupation,
            source_of_funds=request.customer.source_of_funds,
        )
        
        documents = [
            KYCDocument(
                document_type=doc.document_type,
                document_number=doc.document_number,
                issuing_country=doc.issuing_country,
                issue_date=doc.issue_date,
                expiry_date=doc.expiry_date,
                content=doc.content,
            )
            for doc in request.documents
        ]
        
        kyc_request = KYCRequest(
            customer=customer,
            documents=documents,
            verification_type=request.verification_type,
            notes=request.notes,
        )
        
        # Perform verification
        result = await kyc_engine.verify(
            request=kyc_request,
            user_id=user_id,
            model=request.model
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases")
async def list_cases(
    status: Optional[VerificationStatus] = None,
    risk_level: Optional[RiskLevel] = None,
    limit: int = 50,
    user_id: str = Depends(get_user_id_flexible)
):
    """
    List KYC verification cases.
    
    Filter by status and/or risk level.
    """
    cases = await kyc_engine.list_cases(
        user_id=user_id,
        status=status.value if status else None,
        risk_level=risk_level.value if risk_level else None,
        limit=limit
    )
    return {"cases": cases, "total": len(cases)}


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    user_id: str = Depends(get_user_id_flexible)
):
    """
    Get specific KYC case details.
    """
    case = await kyc_engine.get_case(case_id, user_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.put("/cases/{case_id}")
async def update_case(
    case_id: str,
    request: UpdateCaseRequest,
    user_id: str = Depends(get_user_id_flexible)
):
    """
    Update a KYC case (manual review).
    
    Use this for:
    - Approving/rejecting after manual review
    - Adding reviewer notes
    - Recording who reviewed the case
    """
    success = await kyc_engine.update_case(
        case_id=case_id,
        user_id=user_id,
        status=request.status.value if request.status else None,
        reviewed_by=request.reviewed_by,
        notes=request.notes
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {"success": True, "case_id": case_id}


@router.get("/stats")
async def get_stats(
    user_id: str = Depends(get_user_id_flexible)
):
    """
    Get KYC statistics.
    
    Returns:
    - Total cases
    - Breakdown by status
    - Breakdown by risk level
    - Approval rate
    - Average score
    """
    stats = await kyc_engine.get_stats(user_id)
    return stats


@router.get("/document-types")
async def list_document_types():
    """
    List supported document types for KYC.
    """
    return {
        "document_types": [
            {
                "type": DocumentType.PASSPORT.value,
                "name": "Passport",
                "description": "International travel document",
                "category": "identity"
            },
            {
                "type": DocumentType.DRIVERS_LICENSE.value,
                "name": "Driver's License",
                "description": "Government-issued driving permit",
                "category": "identity"
            },
            {
                "type": DocumentType.NATIONAL_ID.value,
                "name": "National ID Card",
                "description": "Government-issued national identification",
                "category": "identity"
            },
            {
                "type": DocumentType.PROOF_OF_ADDRESS.value,
                "name": "Proof of Address",
                "description": "Document showing residential address",
                "category": "address"
            },
            {
                "type": DocumentType.UTILITY_BILL.value,
                "name": "Utility Bill",
                "description": "Recent utility bill showing address",
                "category": "address"
            },
            {
                "type": DocumentType.BANK_STATEMENT.value,
                "name": "Bank Statement",
                "description": "Official bank account statement",
                "category": "financial"
            }
        ]
    }


@router.get("/risk-levels")
async def list_risk_levels():
    """
    List risk level definitions and thresholds.
    """
    return {
        "risk_levels": [
            {
                "level": RiskLevel.LOW.value,
                "score_range": "0-25",
                "action": "Auto-approve",
                "review_period": "Annual"
            },
            {
                "level": RiskLevel.MEDIUM.value,
                "score_range": "26-50",
                "action": "Manual review within 24h",
                "review_period": "Semi-annual"
            },
            {
                "level": RiskLevel.HIGH.value,
                "score_range": "51-75",
                "action": "Escalate to compliance officer",
                "review_period": "Quarterly"
            },
            {
                "level": RiskLevel.CRITICAL.value,
                "score_range": "76-100",
                "action": "Immediate escalation, do not proceed",
                "review_period": "Continuous monitoring"
            }
        ]
    }


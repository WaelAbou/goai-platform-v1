"""
OCR API Router

REST API endpoints for OCR (Optical Character Recognition).
Part of Layer 3 - Knowledge Layer.

Available to all use cases:
- KYC document verification
- Document ingestion
- Any image-to-text extraction
"""

import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

from modules.ingestion.ocr import (
    ocr_engine,
    OCRProvider,
    DocumentType,
    OCRResult,
)


router = APIRouter(prefix="/ocr", tags=["OCR"])


# === REQUEST/RESPONSE MODELS ===

class ExtractRequest(BaseModel):
    """Request to extract text from base64-encoded image."""
    image_base64: str
    document_type: str = "generic"
    provider: str = "auto"
    language: str = "eng"
    extract_structured: bool = False


class ExtractResponse(BaseModel):
    """Response with extracted text."""
    text: str
    confidence: float
    provider: str
    language: str
    processing_time_ms: int
    structured_data: Optional[dict] = None
    metadata: Optional[dict] = None


class PDFExtractRequest(BaseModel):
    """Request to extract text from base64-encoded scanned PDF."""
    pdf_base64: str
    provider: str = "auto"
    language: str = "eng"


class PDFPageResult(BaseModel):
    """OCR result for a single PDF page."""
    page_number: int
    text: str
    confidence: float


class PDFExtractResponse(BaseModel):
    """Response with extracted text from all PDF pages."""
    total_pages: int
    pages: List[PDFPageResult]
    full_text: str
    provider: str
    total_processing_time_ms: int


# === ENDPOINTS ===

@router.get("/providers")
async def list_providers():
    """
    List available OCR providers.
    
    Returns which OCR backends are configured and available.
    """
    providers = ocr_engine.get_available_providers()
    return {
        "available_providers": providers,
        "default": "auto",
        "provider_details": {
            "gpt4_vision": {
                "name": "GPT-4 Vision",
                "description": "OpenAI GPT-4 with vision capabilities",
                "accuracy": "Highest",
                "speed": "Medium",
                "available": "gpt4_vision" in providers,
                "requires": "OPENAI_API_KEY"
            },
            "tesseract": {
                "name": "Tesseract OCR",
                "description": "Open-source OCR engine",
                "accuracy": "Good",
                "speed": "Fast",
                "available": "tesseract" in providers,
                "requires": "tesseract-ocr system package"
            },
            "easyocr": {
                "name": "EasyOCR",
                "description": "Deep learning based OCR",
                "accuracy": "Good",
                "speed": "Slow (first run)",
                "available": "easyocr" in providers,
                "requires": "easyocr Python package"
            }
        }
    }


@router.get("/document-types")
async def list_document_types():
    """
    List supported document types for specialized extraction.
    
    Different document types have optimized extraction prompts.
    """
    return {
        "document_types": [
            {
                "type": "generic",
                "name": "Generic Document",
                "description": "Any document or image with text"
            },
            {
                "type": "passport",
                "name": "Passport",
                "description": "International passport document",
                "extracted_fields": ["surname", "given_names", "date_of_birth", "passport_number", "mrz"]
            },
            {
                "type": "drivers_license",
                "name": "Driver's License",
                "description": "Driving license/permit",
                "extracted_fields": ["full_name", "address", "license_number", "expiry_date"]
            },
            {
                "type": "national_id",
                "name": "National ID",
                "description": "Government-issued national ID card",
                "extracted_fields": ["full_name", "id_number", "date_of_birth", "nationality"]
            },
            {
                "type": "invoice",
                "name": "Invoice",
                "description": "Commercial invoice document",
                "extracted_fields": ["invoice_number", "date", "vendor", "line_items", "total"]
            },
            {
                "type": "receipt",
                "name": "Receipt",
                "description": "Purchase receipt",
                "extracted_fields": ["merchant", "date", "items", "total"]
            },
            {
                "type": "form",
                "name": "Form",
                "description": "Structured form document",
                "extracted_fields": ["field_labels", "field_values"]
            }
        ]
    }


@router.get("/supported-formats")
async def list_supported_formats():
    """List supported image formats for OCR."""
    return {
        "supported_formats": ocr_engine.SUPPORTED_FORMATS,
        "max_file_size_mb": 20,
        "recommendations": {
            "best_quality": ["png", "tiff"],
            "smallest_size": ["jpeg", "webp"],
            "animated": ["gif"]
        }
    }


@router.post("/extract", response_model=ExtractResponse)
async def extract_text(request: ExtractRequest):
    """
    Extract text from a base64-encoded image.
    
    **Document Types:**
    - `generic`: Any document (default)
    - `passport`: Passport with MRZ extraction
    - `drivers_license`: Driver's license
    - `national_id`: National ID card
    - `invoice`: Commercial invoice
    - `receipt`: Purchase receipt
    - `form`: Structured form
    
    **Providers:**
    - `auto`: Auto-select best available (default)
    - `gpt4_vision`: GPT-4 Vision (highest accuracy)
    - `tesseract`: Tesseract OCR (local, fast)
    - `easyocr`: EasyOCR (multilingual)
    """
    try:
        # Decode base64 image
        try:
            image_data = base64.b64decode(request.image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Map string to enums
        doc_type = DocumentType(request.document_type)
        provider = OCRProvider(request.provider)
        
        # Run OCR
        result = await ocr_engine.extract_text(
            image_data=image_data,
            document_type=doc_type,
            provider=provider,
            language=request.language,
            extract_structured=request.extract_structured,
        )
        
        return ExtractResponse(
            text=result.text,
            confidence=result.confidence,
            provider=result.provider,
            language=result.language,
            processing_time_ms=result.processing_time_ms,
            structured_data=result.structured_data,
            metadata=result.metadata,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")


@router.post("/extract/upload", response_model=ExtractResponse)
async def extract_text_upload(
    file: UploadFile = File(...),
    document_type: str = Form(default="generic"),
    provider: str = Form(default="auto"),
    language: str = Form(default="eng"),
    extract_structured: bool = Form(default=False),
):
    """
    Extract text from an uploaded image file.
    
    Supports: JPEG, PNG, GIF, WebP, BMP, TIFF
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not ocr_engine.is_image_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported: {ocr_engine.SUPPORTED_FORMATS}"
            )
        
        # Read file
        image_data = await file.read()
        
        # Validate size (max 20MB)
        if len(image_data) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Max 20MB.")
        
        # Map string to enums
        doc_type = DocumentType(document_type)
        prov = OCRProvider(provider)
        
        # Run OCR
        result = await ocr_engine.extract_text(
            image_data=image_data,
            document_type=doc_type,
            provider=prov,
            language=language,
            extract_structured=extract_structured,
        )
        
        return ExtractResponse(
            text=result.text,
            confidence=result.confidence,
            provider=result.provider,
            language=result.language,
            processing_time_ms=result.processing_time_ms,
            structured_data=result.structured_data,
            metadata={
                **(result.metadata or {}),
                "filename": file.filename,
                "file_size": len(image_data),
            },
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")


@router.post("/extract/pdf", response_model=PDFExtractResponse)
async def extract_text_from_pdf(request: PDFExtractRequest):
    """
    Extract text from a scanned PDF using OCR.
    
    Converts each PDF page to an image and runs OCR.
    Useful for scanned documents that don't have embedded text.
    """
    try:
        # Decode base64 PDF
        try:
            pdf_data = base64.b64decode(request.pdf_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 PDF data")
        
        # Map provider
        provider = OCRProvider(request.provider)
        
        # Run OCR on PDF
        results = await ocr_engine.extract_from_pdf(
            pdf_data=pdf_data,
            provider=provider,
            language=request.language,
        )
        
        # Format response
        pages = []
        full_text_parts = []
        total_time = 0
        
        for result in results:
            page_num = result.metadata.get("page_number", 0)
            pages.append(PDFPageResult(
                page_number=page_num,
                text=result.text,
                confidence=result.confidence,
            ))
            full_text_parts.append(f"[Page {page_num}]\n{result.text}")
            total_time += result.processing_time_ms
        
        return PDFExtractResponse(
            total_pages=len(results),
            pages=pages,
            full_text="\n\n".join(full_text_parts),
            provider=results[0].provider if results else "unknown",
            total_processing_time_ms=total_time,
        )
        
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF OCR extraction failed: {str(e)}")


@router.post("/extract/pdf/upload", response_model=PDFExtractResponse)
async def extract_text_from_pdf_upload(
    file: UploadFile = File(...),
    provider: str = Form(default="auto"),
    language: str = Form(default="eng"),
):
    """
    Extract text from an uploaded scanned PDF using OCR.
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Read file
        pdf_data = await file.read()
        
        # Validate size (max 50MB for PDFs)
        if len(pdf_data) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Max 50MB.")
        
        # Map provider
        prov = OCRProvider(provider)
        
        # Run OCR on PDF
        results = await ocr_engine.extract_from_pdf(
            pdf_data=pdf_data,
            provider=prov,
            language=language,
        )
        
        # Format response
        pages = []
        full_text_parts = []
        total_time = 0
        
        for result in results:
            page_num = result.metadata.get("page_number", 0)
            pages.append(PDFPageResult(
                page_number=page_num,
                text=result.text,
                confidence=result.confidence,
            ))
            full_text_parts.append(f"[Page {page_num}]\n{result.text}")
            total_time += result.processing_time_ms
        
        return PDFExtractResponse(
            total_pages=len(results),
            pages=pages,
            full_text="\n\n".join(full_text_parts),
            provider=results[0].provider if results else "unknown",
            total_processing_time_ms=total_time,
        )
        
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF OCR extraction failed: {str(e)}")


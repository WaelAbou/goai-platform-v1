"""
OCR Engine - Core Module for Text Extraction from Images

Layer 3 - Knowledge Layer Component
Part of the Ingestion Pipeline

Supports:
- GPT-4 Vision (primary, highest accuracy)
- Tesseract OCR (fallback, local processing)
- EasyOCR (optional, multilingual)

Used by:
- KYC document verification
- Scanned PDF processing  
- Document ingestion
- Any use case requiring image-to-text
"""

import os
import io
import base64
import asyncio
import httpx
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json


class OCRProvider(str, Enum):
    """Available OCR providers."""
    GPT4_VISION = "gpt4_vision"
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    AUTO = "auto"  # Auto-select best available


class DocumentType(str, Enum):
    """Document types for specialized extraction."""
    GENERIC = "generic"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    FORM = "form"


@dataclass
class OCRResult:
    """Result from OCR extraction."""
    text: str
    confidence: float
    provider: str
    language: str
    processing_time_ms: int
    structured_data: Optional[Dict[str, Any]] = None
    bounding_boxes: Optional[List[Dict]] = None
    metadata: Optional[Dict[str, Any]] = None


class OCREngine:
    """
    Core OCR Engine for the GoAI Platform.
    
    Provides unified interface for text extraction from images
    with multiple provider support and intelligent fallback.
    """
    
    # Supported image formats
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif']
    
    # GPT-4 Vision prompts for different document types
    EXTRACTION_PROMPTS = {
        DocumentType.GENERIC: """Extract all visible text from this image. 
Preserve the layout and structure as much as possible.
Return the extracted text only, no explanations.""",

        DocumentType.PASSPORT: """Extract all text from this passport image.
Focus on:
- Surname and Given Names
- Nationality
- Date of Birth (format as YYYY-MM-DD)
- Sex
- Place of Birth
- Date of Issue
- Date of Expiry
- Passport Number
- Machine Readable Zone (MRZ) if visible

Return the extracted text preserving the document structure.""",

        DocumentType.DRIVERS_LICENSE: """Extract all text from this driver's license.
Focus on:
- Full Name
- Address
- Date of Birth
- License Number
- Issue Date
- Expiry Date
- License Class/Type
- Restrictions

Return the extracted text preserving the document structure.""",

        DocumentType.NATIONAL_ID: """Extract all text from this national ID card.
Focus on:
- Full Name
- ID Number
- Date of Birth
- Nationality
- Address (if present)
- Issue Date
- Expiry Date

Return the extracted text preserving the document structure.""",

        DocumentType.INVOICE: """Extract all text from this invoice.
Focus on:
- Invoice Number
- Date
- Vendor/Supplier Name
- Customer Name
- Line Items (description, quantity, price)
- Subtotal, Tax, Total
- Payment Terms

Return the extracted text in a structured format.""",

        DocumentType.RECEIPT: """Extract all text from this receipt.
Focus on:
- Store/Merchant Name
- Date and Time
- Items purchased (name, quantity, price)
- Subtotal, Tax, Total
- Payment Method

Return the extracted text preserving the receipt structure.""",

        DocumentType.FORM: """Extract all text from this form.
Identify field labels and their corresponding values.
Preserve the form structure and layout.
Return as field: value pairs where possible.""",
    }
    
    # Structured extraction prompts (returns JSON)
    STRUCTURED_PROMPTS = {
        DocumentType.PASSPORT: """Extract passport information as JSON:
{
  "surname": "",
  "given_names": "",
  "nationality": "",
  "date_of_birth": "YYYY-MM-DD",
  "sex": "",
  "place_of_birth": "",
  "date_of_issue": "YYYY-MM-DD",
  "date_of_expiry": "YYYY-MM-DD",
  "passport_number": "",
  "mrz_line1": "",
  "mrz_line2": "",
  "issuing_country": ""
}
Only return valid JSON, no explanations.""",

        DocumentType.DRIVERS_LICENSE: """Extract driver's license information as JSON:
{
  "full_name": "",
  "address": "",
  "date_of_birth": "YYYY-MM-DD",
  "license_number": "",
  "issue_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "license_class": "",
  "restrictions": "",
  "issuing_state": ""
}
Only return valid JSON, no explanations.""",

        DocumentType.NATIONAL_ID: """Extract national ID information as JSON:
{
  "full_name": "",
  "id_number": "",
  "date_of_birth": "YYYY-MM-DD",
  "nationality": "",
  "address": "",
  "issue_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "issuing_authority": ""
}
Only return valid JSON, no explanations.""",
    }
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self._check_providers()
    
    def _check_providers(self):
        """Check which OCR providers are available."""
        self.has_tesseract = False
        self.has_easyocr = False
        
        # Check Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.has_tesseract = True
        except:
            pass
        
        # Check EasyOCR
        try:
            import easyocr
            self.has_easyocr = True
        except:
            pass
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OCR providers."""
        providers = []
        if self.openai_api_key:
            providers.append(OCRProvider.GPT4_VISION.value)
        if self.has_tesseract:
            providers.append(OCRProvider.TESSERACT.value)
        if self.has_easyocr:
            providers.append(OCRProvider.EASYOCR.value)
        return providers
    
    def _select_provider(self, preferred: OCRProvider) -> OCRProvider:
        """Select the best available provider."""
        if preferred != OCRProvider.AUTO:
            # Verify preferred provider is available
            if preferred == OCRProvider.GPT4_VISION and self.openai_api_key:
                return OCRProvider.GPT4_VISION
            elif preferred == OCRProvider.TESSERACT and self.has_tesseract:
                return OCRProvider.TESSERACT
            elif preferred == OCRProvider.EASYOCR and self.has_easyocr:
                return OCRProvider.EASYOCR
        
        # Auto-select: prefer GPT-4V > Tesseract > EasyOCR
        if self.openai_api_key:
            return OCRProvider.GPT4_VISION
        elif self.has_tesseract:
            return OCRProvider.TESSERACT
        elif self.has_easyocr:
            return OCRProvider.EASYOCR
        
        raise RuntimeError("No OCR provider available. Install tesseract or set OPENAI_API_KEY.")
    
    async def extract_text(
        self,
        image_data: bytes,
        document_type: DocumentType = DocumentType.GENERIC,
        provider: OCRProvider = OCRProvider.AUTO,
        language: str = "eng",
        extract_structured: bool = False,
    ) -> OCRResult:
        """
        Extract text from an image.
        
        Args:
            image_data: Raw image bytes
            document_type: Type of document for specialized extraction
            provider: OCR provider to use
            language: Language code (ISO 639-2)
            extract_structured: Return structured JSON data
            
        Returns:
            OCRResult with extracted text and metadata
        """
        import time
        start_time = time.time()
        
        # Select provider
        selected_provider = self._select_provider(provider)
        
        # Extract based on provider
        if selected_provider == OCRProvider.GPT4_VISION:
            result = await self._extract_with_gpt4v(
                image_data, document_type, extract_structured
            )
        elif selected_provider == OCRProvider.TESSERACT:
            result = await self._extract_with_tesseract(
                image_data, language
            )
        elif selected_provider == OCRProvider.EASYOCR:
            result = await self._extract_with_easyocr(
                image_data, language
            )
        else:
            raise ValueError(f"Unknown provider: {selected_provider}")
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return OCRResult(
            text=result.get("text", ""),
            confidence=result.get("confidence", 0.0),
            provider=selected_provider.value,
            language=language,
            processing_time_ms=processing_time_ms,
            structured_data=result.get("structured_data"),
            bounding_boxes=result.get("bounding_boxes"),
            metadata={
                "document_type": document_type.value,
                "extracted_at": datetime.utcnow().isoformat(),
            }
        )
    
    async def _extract_with_gpt4v(
        self,
        image_data: bytes,
        document_type: DocumentType,
        extract_structured: bool,
    ) -> Dict[str, Any]:
        """Extract text using GPT-4 Vision."""
        if not self.openai_api_key:
            raise RuntimeError("OpenAI API key not configured")
        
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Detect image type
        image_type = self._detect_image_type(image_data)
        
        # Select prompt
        if extract_structured and document_type in self.STRUCTURED_PROMPTS:
            prompt = self.STRUCTURED_PROMPTS[document_type]
        else:
            prompt = self.EXTRACTION_PROMPTS.get(
                document_type, 
                self.EXTRACTION_PROMPTS[DocumentType.GENERIC]
            )
        
        # Call GPT-4 Vision
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",  # GPT-4 Vision
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{image_type};base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1,  # Low temperature for accuracy
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"GPT-4V API error: {response.text}")
            
            result = response.json()
            text = result["choices"][0]["message"]["content"]
            
            # Try to parse structured data if requested
            structured_data = None
            if extract_structured:
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        structured_data = json.loads(json_match.group())
                except:
                    pass
            
            return {
                "text": text,
                "confidence": 0.95,  # GPT-4V is highly accurate
                "structured_data": structured_data,
            }
    
    async def _extract_with_tesseract(
        self,
        image_data: bytes,
        language: str,
    ) -> Dict[str, Any]:
        """Extract text using Tesseract OCR."""
        import pytesseract
        from PIL import Image
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Run OCR
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: pytesseract.image_to_data(
                image, 
                lang=language,
                output_type=pytesseract.Output.DICT
            )
        )
        
        # Extract text and confidence
        text_parts = []
        confidences = []
        
        for i, word in enumerate(result["text"]):
            if word.strip():
                text_parts.append(word)
                conf = result["conf"][i]
                if conf > 0:
                    confidences.append(conf)
        
        text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
        
        # Get bounding boxes
        bounding_boxes = []
        for i in range(len(result["text"])):
            if result["text"][i].strip():
                bounding_boxes.append({
                    "text": result["text"][i],
                    "x": result["left"][i],
                    "y": result["top"][i],
                    "width": result["width"][i],
                    "height": result["height"][i],
                    "confidence": result["conf"][i] / 100,
                })
        
        return {
            "text": text,
            "confidence": avg_confidence,
            "bounding_boxes": bounding_boxes,
        }
    
    async def _extract_with_easyocr(
        self,
        image_data: bytes,
        language: str,
    ) -> Dict[str, Any]:
        """Extract text using EasyOCR."""
        import easyocr
        import numpy as np
        from PIL import Image
        
        # Map language codes
        lang_map = {
            "eng": "en",
            "ara": "ar",
            "fra": "fr",
            "deu": "de",
            "spa": "es",
        }
        lang = lang_map.get(language, language)
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        image_np = np.array(image)
        
        # Initialize reader (cached after first call)
        loop = asyncio.get_event_loop()
        
        def run_easyocr():
            reader = easyocr.Reader([lang], gpu=False)
            return reader.readtext(image_np)
        
        results = await loop.run_in_executor(None, run_easyocr)
        
        # Process results
        text_parts = []
        confidences = []
        bounding_boxes = []
        
        for bbox, text, conf in results:
            text_parts.append(text)
            confidences.append(conf)
            bounding_boxes.append({
                "text": text,
                "bbox": bbox,
                "confidence": conf,
            })
        
        text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "text": text,
            "confidence": avg_confidence,
            "bounding_boxes": bounding_boxes,
        }
    
    def _detect_image_type(self, image_data: bytes) -> str:
        """Detect image MIME type from bytes."""
        # Check magic bytes
        if image_data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_data[:2] == b'\xff\xd8':
            return "image/jpeg"
        elif image_data[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            return "image/webp"
        else:
            return "image/jpeg"  # Default
    
    async def extract_from_pdf(
        self,
        pdf_data: bytes,
        provider: OCRProvider = OCRProvider.AUTO,
        language: str = "eng",
    ) -> List[OCRResult]:
        """
        Extract text from a scanned PDF using OCR.
        Converts each page to image and runs OCR.
        
        Args:
            pdf_data: Raw PDF bytes
            provider: OCR provider to use
            language: Language code
            
        Returns:
            List of OCRResult, one per page
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")
        
        results = []
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for quality
            image_data = pix.tobytes("png")
            
            # Run OCR on page image
            result = await self.extract_text(
                image_data=image_data,
                provider=provider,
                language=language,
            )
            
            # Add page number to metadata
            result.metadata["page_number"] = page_num + 1
            result.metadata["total_pages"] = len(doc)
            
            results.append(result)
        
        doc.close()
        return results
    
    def is_image_file(self, filename: str) -> bool:
        """Check if filename is a supported image format."""
        from pathlib import Path
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_FORMATS


# Singleton instance
ocr_engine = OCREngine()


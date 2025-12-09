"""
Email Processor for Sustainability Data Ingestion

Automatically processes emails forwarded to a dedicated inbox:
1. Parses email content and attachments
2. Extracts text from PDFs/images using OCR
3. Processes through smart ingestion
4. Adds to review queue

Supports integration with:
- SendGrid Inbound Parse
- Mailgun Routes
- Microsoft Graph API (Office 365)
- Google Cloud Pub/Sub (Gmail)
- AWS SES
"""

import base64
import re
import json
import email
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from email.parser import BytesParser
import mimetypes


@dataclass
class EmailAttachment:
    """Represents an email attachment."""
    filename: str
    content_type: str
    content_base64: str
    size_bytes: int
    
    @property
    def is_image(self) -> bool:
        return self.content_type.startswith('image/')
    
    @property
    def is_pdf(self) -> bool:
        return self.content_type == 'application/pdf'
    
    @property
    def is_processable(self) -> bool:
        """Check if this attachment can be processed."""
        processable_types = [
            'application/pdf',
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'text/plain', 'text/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
        return self.content_type in processable_types or self.is_image


@dataclass
class ParsedEmail:
    """Parsed email data."""
    message_id: str
    from_address: str
    from_name: Optional[str]
    to_address: str
    subject: str
    body_text: str
    body_html: Optional[str]
    received_at: str
    attachments: List[EmailAttachment]
    headers: Dict[str, str]
    
    # Extracted metadata
    forwarded_from: Optional[str] = None
    original_sender: Optional[str] = None
    company_hint: Optional[str] = None
    
    @property
    def has_attachments(self) -> bool:
        return len(self.attachments) > 0
    
    @property
    def processable_attachments(self) -> List[EmailAttachment]:
        return [a for a in self.attachments if a.is_processable]


@dataclass
class ProcessingResult:
    """Result of processing an email."""
    email_id: str
    status: str  # success, partial, failed
    items_created: int
    items: List[Dict[str, Any]]
    errors: List[str]
    processing_time_ms: int


class EmailProcessor:
    """
    Processes incoming emails for sustainability data extraction.
    
    Workflow:
    1. Receive email (via webhook or polling)
    2. Parse email and extract attachments
    3. For each attachment: OCR if image/PDF, extract text
    4. Run through smart ingestion
    5. Add to review queue
    6. Send confirmation email (optional)
    """
    
    # Allowed sender domains (for security)
    ALLOWED_DOMAINS: List[str] = []  # Empty = allow all
    
    # Maximum attachment size (10MB)
    MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
    
    # Supported email providers
    PROVIDERS = ['sendgrid', 'mailgun', 'microsoft', 'google', 'aws_ses', 'raw']
    
    def __init__(self):
        self.smart_processor = None
        self.review_queue = None
        self.ocr_engine = None
        
    def set_dependencies(self, smart_processor, review_queue, ocr_engine=None):
        """Set required dependencies."""
        self.smart_processor = smart_processor
        self.review_queue = review_queue
        self.ocr_engine = ocr_engine
    
    def parse_sendgrid(self, payload: Dict[str, Any]) -> ParsedEmail:
        """
        Parse SendGrid Inbound Parse webhook payload.
        
        SendGrid sends multipart/form-data with fields:
        - from, to, subject, text, html
        - attachment1, attachment2, etc.
        - attachment-info (JSON with attachment metadata)
        """
        attachments = []
        
        # Parse attachment info
        attachment_info = json.loads(payload.get('attachment-info', '{}'))
        
        for key, info in attachment_info.items():
            # Key is like "attachment1"
            if key in payload:
                content = payload[key]
                if isinstance(content, bytes):
                    content_b64 = base64.b64encode(content).decode('utf-8')
                else:
                    content_b64 = content
                
                attachments.append(EmailAttachment(
                    filename=info.get('filename', f'{key}.bin'),
                    content_type=info.get('type', 'application/octet-stream'),
                    content_base64=content_b64,
                    size_bytes=len(base64.b64decode(content_b64)) if content_b64 else 0
                ))
        
        return ParsedEmail(
            message_id=payload.get('Message-Id', self._generate_message_id()),
            from_address=self._extract_email(payload.get('from', '')),
            from_name=self._extract_name(payload.get('from', '')),
            to_address=self._extract_email(payload.get('to', '')),
            subject=payload.get('subject', '(no subject)'),
            body_text=payload.get('text', ''),
            body_html=payload.get('html'),
            received_at=datetime.now().isoformat(),
            attachments=attachments,
            headers=self._parse_headers(payload.get('headers', ''))
        )
    
    def parse_mailgun(self, payload: Dict[str, Any]) -> ParsedEmail:
        """
        Parse Mailgun webhook payload.
        
        Similar to SendGrid but with different field names.
        """
        attachments = []
        
        # Mailgun sends attachments as a list
        for i, att in enumerate(payload.get('attachments', [])):
            attachments.append(EmailAttachment(
                filename=att.get('filename', f'attachment_{i}'),
                content_type=att.get('content-type', 'application/octet-stream'),
                content_base64=att.get('content', ''),
                size_bytes=att.get('size', 0)
            ))
        
        return ParsedEmail(
            message_id=payload.get('Message-Id', self._generate_message_id()),
            from_address=self._extract_email(payload.get('sender', '')),
            from_name=self._extract_name(payload.get('sender', '')),
            to_address=self._extract_email(payload.get('recipient', '')),
            subject=payload.get('subject', '(no subject)'),
            body_text=payload.get('body-plain', ''),
            body_html=payload.get('body-html'),
            received_at=datetime.now().isoformat(),
            attachments=attachments,
            headers={}
        )
    
    def parse_microsoft(self, payload: Dict[str, Any]) -> ParsedEmail:
        """
        Parse Microsoft Graph API webhook payload.
        
        Office 365 / Outlook integration.
        """
        message = payload.get('message', payload)
        
        attachments = []
        for att in message.get('attachments', []):
            if att.get('@odata.type') == '#microsoft.graph.fileAttachment':
                attachments.append(EmailAttachment(
                    filename=att.get('name', 'attachment'),
                    content_type=att.get('contentType', 'application/octet-stream'),
                    content_base64=att.get('contentBytes', ''),
                    size_bytes=att.get('size', 0)
                ))
        
        sender = message.get('from', {}).get('emailAddress', {})
        recipient = message.get('toRecipients', [{}])[0].get('emailAddress', {})
        
        return ParsedEmail(
            message_id=message.get('internetMessageId', self._generate_message_id()),
            from_address=sender.get('address', ''),
            from_name=sender.get('name'),
            to_address=recipient.get('address', ''),
            subject=message.get('subject', '(no subject)'),
            body_text=message.get('body', {}).get('content', '') if message.get('body', {}).get('contentType') == 'text' else '',
            body_html=message.get('body', {}).get('content', '') if message.get('body', {}).get('contentType') == 'html' else None,
            received_at=message.get('receivedDateTime', datetime.now().isoformat()),
            attachments=attachments,
            headers={}
        )
    
    def parse_raw_email(self, raw_bytes: bytes) -> ParsedEmail:
        """
        Parse raw RFC 822 email bytes.
        
        Useful for AWS SES or direct IMAP/POP3 integration.
        """
        msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
        
        attachments = []
        body_text = ""
        body_html = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition', ''))
                
                if 'attachment' in disposition:
                    content = part.get_payload(decode=True)
                    if content:
                        attachments.append(EmailAttachment(
                            filename=part.get_filename() or 'attachment',
                            content_type=content_type,
                            content_base64=base64.b64encode(content).decode('utf-8'),
                            size_bytes=len(content)
                        ))
                elif content_type == 'text/plain':
                    body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == 'text/html':
                    body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return ParsedEmail(
            message_id=msg.get('Message-ID', self._generate_message_id()),
            from_address=self._extract_email(msg.get('From', '')),
            from_name=self._extract_name(msg.get('From', '')),
            to_address=self._extract_email(msg.get('To', '')),
            subject=msg.get('Subject', '(no subject)'),
            body_text=body_text,
            body_html=body_html,
            received_at=msg.get('Date', datetime.now().isoformat()),
            attachments=attachments,
            headers={k: v for k, v in msg.items()}
        )
    
    async def process_email(
        self,
        parsed_email: ParsedEmail,
        company_id: Optional[str] = None,
        auto_approve_threshold: float = 0.95
    ) -> ProcessingResult:
        """
        Process a parsed email and extract sustainability data.
        
        Args:
            parsed_email: Parsed email object
            company_id: Company to associate data with
            auto_approve_threshold: Auto-approve if confidence >= this
            
        Returns:
            ProcessingResult with created items
        """
        start_time = datetime.now()
        items_created = []
        errors = []
        
        # Extract company hint from email domain
        if not company_id:
            domain = parsed_email.from_address.split('@')[-1] if '@' in parsed_email.from_address else None
            if domain:
                company_id = f"domain_{domain.replace('.', '_')}"
        
        # Process attachments
        for attachment in parsed_email.processable_attachments:
            try:
                # Check size limit
                if attachment.size_bytes > self.MAX_ATTACHMENT_SIZE:
                    errors.append(f"{attachment.filename}: Exceeds size limit")
                    continue
                
                # Extract text content
                text_content = await self._extract_text(attachment)
                
                if not text_content:
                    errors.append(f"{attachment.filename}: Could not extract text")
                    continue
                
                # Process through smart ingestion
                result = await self.smart_processor.process_document(
                    text_content=text_content
                )
                
                # Add to review queue
                item = self.review_queue.add_item(
                    document_type=result.document_type.value,
                    category=result.template,
                    source="email",
                    filename=attachment.filename,
                    uploaded_by=parsed_email.from_address,
                    confidence=result.confidence,
                    extracted_data=result.data,
                    raw_text=result.raw_text,
                    calculated_co2e_kg=result.calculated_co2e_kg,
                    company_id=company_id,
                    auto_approve_threshold=auto_approve_threshold
                )
                
                items_created.append({
                    "item_id": item.id,
                    "filename": attachment.filename,
                    "document_type": result.document_type.value,
                    "confidence": result.confidence,
                    "status": item.status,
                    "co2e_kg": result.calculated_co2e_kg
                })
                
            except Exception as e:
                errors.append(f"{attachment.filename}: {str(e)}")
        
        # If no attachments or no items from attachments, try processing email body
        if (not parsed_email.has_attachments or len(items_created) == 0) and parsed_email.body_text:
            try:
                # Always try to process body text if it's substantial
                body_text = parsed_email.body_text.strip()
                
                if len(body_text) > 20:  # At least some content
                    result = await self.smart_processor.process_document(
                        text_content=body_text
                    )
                    
                    # Accept if we got a document type (even unknown) with some confidence
                    if result.document_type.value != "unknown" or result.confidence > 0.3:
                        msg_id_short = parsed_email.message_id.replace('<', '').replace('>', '')[:8]
                        item = self.review_queue.add_item(
                            document_type=result.document_type.value,
                            category=result.template,
                            source="email",
                            filename=f"email_body_{msg_id_short}.txt",
                            uploaded_by=parsed_email.from_address,
                            confidence=result.confidence,
                            extracted_data=result.data,
                            raw_text=result.raw_text,
                            calculated_co2e_kg=result.calculated_co2e_kg,
                            company_id=company_id,
                            auto_approve_threshold=auto_approve_threshold
                        )
                        
                        items_created.append({
                            "item_id": item.id,
                            "filename": "Email Body",
                            "document_type": result.document_type.value,
                            "confidence": result.confidence,
                            "status": item.status,
                            "co2e_kg": result.calculated_co2e_kg
                        })
                        
            except Exception as e:
                errors.append(f"Email body: {str(e)}")
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Determine overall status
        if len(items_created) > 0 and len(errors) == 0:
            status = "success"
        elif len(items_created) > 0:
            status = "partial"
        else:
            status = "failed"
        
        return ProcessingResult(
            email_id=parsed_email.message_id,
            status=status,
            items_created=len(items_created),
            items=items_created,
            errors=errors,
            processing_time_ms=processing_time
        )
    
    async def _extract_text(self, attachment: EmailAttachment) -> Optional[str]:
        """Extract text content from attachment."""
        content_bytes = base64.b64decode(attachment.content_base64)
        
        if attachment.content_type == 'text/plain':
            return content_bytes.decode('utf-8', errors='ignore')
        
        if attachment.content_type == 'text/csv':
            # Convert CSV to readable text
            return content_bytes.decode('utf-8', errors='ignore')
        
        if attachment.is_pdf:
            # Try OCR or PDF text extraction
            if self.ocr_engine:
                result = await self.ocr_engine.extract_from_pdf(
                    pdf_base64=attachment.content_base64
                )
                return result.get('full_text', '')
            # Fallback: try basic PDF text extraction
            return self._basic_pdf_extract(content_bytes)
        
        if attachment.is_image:
            # Use OCR
            if self.ocr_engine:
                result = await self.ocr_engine.extract(
                    image_base64=attachment.content_base64,
                    document_type="generic"
                )
                return result.text
            return None
        
        return None
    
    def _basic_pdf_extract(self, pdf_bytes: bytes) -> Optional[str]:
        """Basic PDF text extraction without OCR."""
        try:
            # Try using PyPDF2 or pdfplumber if available
            import io
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(pdf_bytes))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                return text if text.strip() else None
            except ImportError:
                pass
            
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    return text if text.strip() else None
            except ImportError:
                pass
            
            return None
        except Exception:
            return None
    
    def _looks_like_sustainability_data(self, text: str) -> bool:
        """Check if text might contain sustainability data."""
        keywords = [
            'kwh', 'kilowatt', 'electricity', 'utility',
            'therms', 'natural gas', 'gas bill',
            'flight', 'airline', 'boarding',
            'fuel', 'gallons', 'liters',
            'shipping', 'freight', 'cargo',
            'co2', 'carbon', 'emissions',
            'esg', 'sustainability'
        ]
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches >= 2
    
    def _extract_email(self, address_string: str) -> str:
        """Extract email address from string like 'Name <email@example.com>'."""
        match = re.search(r'<([^>]+)>', address_string)
        if match:
            return match.group(1).lower()
        # Maybe it's just the email
        if '@' in address_string:
            return address_string.strip().lower()
        return address_string
    
    def _extract_name(self, address_string: str) -> Optional[str]:
        """Extract name from email address string."""
        match = re.search(r'^([^<]+)<', address_string)
        if match:
            return match.group(1).strip().strip('"')
        return None
    
    def _parse_headers(self, headers_string: str) -> Dict[str, str]:
        """Parse email headers from string."""
        headers = {}
        if not headers_string:
            return headers
        
        for line in headers_string.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        
        return headers
    
    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return f"<{hashlib.md5(str(datetime.now()).encode()).hexdigest()}@sustainability.local>"
    
    def validate_sender(self, email_address: str) -> bool:
        """Validate that sender is allowed."""
        if not self.ALLOWED_DOMAINS:
            return True
        
        domain = email_address.split('@')[-1].lower()
        return domain in [d.lower() for d in self.ALLOWED_DOMAINS]
    
    def generate_confirmation_email(
        self,
        result: ProcessingResult,
        parsed_email: ParsedEmail
    ) -> Dict[str, str]:
        """Generate a confirmation email to send back to the sender."""
        if result.status == "success":
            subject = f"✅ Sustainability Data Received - {result.items_created} items processed"
            body = f"""Hello,

Your email with subject "{parsed_email.subject}" has been successfully processed.

Summary:
- Items processed: {result.items_created}
- Processing time: {result.processing_time_ms}ms

Items created:
"""
            for item in result.items:
                status_icon = "✅" if item["status"] == "auto_approved" else "⏳"
                body += f"\n{status_icon} {item['filename']}"
                body += f"\n   Type: {item['document_type']}"
                body += f"\n   Confidence: {item['confidence']*100:.0f}%"
                if item.get('co2e_kg'):
                    body += f"\n   Emissions: {item['co2e_kg']:.0f} kg CO2e"
                body += "\n"
            
            body += """
View and approve items at: /api/v1/review/

Thank you for using Sustainability Data Collection!
"""
        
        elif result.status == "partial":
            subject = f"⚠️ Sustainability Data - Partial Success ({result.items_created} items)"
            body = f"""Hello,

Your email was partially processed. Some items encountered errors.

Successfully processed: {result.items_created}
Errors: {len(result.errors)}

Errors:
"""
            for error in result.errors:
                body += f"- {error}\n"
            
            body += "\nPlease review and resubmit failed items."
        
        else:
            subject = "❌ Sustainability Data - Processing Failed"
            body = f"""Hello,

We were unable to process your email with subject "{parsed_email.subject}".

Errors:
"""
            for error in result.errors:
                body += f"- {error}\n"
            
            body += """
Please ensure your attachments are:
- PDF, JPG, PNG, or text files
- Under 10MB in size
- Contain readable sustainability data (utility bills, receipts, etc.)

Need help? Contact sustainability-support@company.com
"""
        
        return {
            "to": parsed_email.from_address,
            "subject": subject,
            "body": body
        }


# Singleton instance
email_processor = EmailProcessor()

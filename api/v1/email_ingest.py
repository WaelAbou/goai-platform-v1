"""
Email Ingestion API

Webhooks and endpoints for processing forwarded emails.

Supports:
- SendGrid Inbound Parse
- Mailgun Routes
- Microsoft Graph (Office 365)
- Raw email upload
- Simulated email for testing

Usage:
1. Configure your email service to forward to /api/v1/email/webhook/{provider}
2. Emails are automatically processed and added to review queue
3. Sender receives confirmation email (optional)
"""

from fastapi import APIRouter, HTTPException, Request, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import base64

from modules.sustainability.email_processor import email_processor, ParsedEmail
from modules.sustainability.smart_ingestion import smart_processor
from modules.sustainability.review_queue import review_queue

# Wire up dependencies
email_processor.set_dependencies(
    smart_processor=smart_processor,
    review_queue=review_queue,
    ocr_engine=None  # Will use basic extraction
)

router = APIRouter()


# ==================== Models ====================

class SimulatedEmail(BaseModel):
    """Simulated email for testing."""
    from_address: str = Field(default="user@company.com")
    from_name: Optional[str] = Field(default="Test User")
    to_address: str = Field(default="sustainability@company.com")
    subject: str = Field(default="FW: Utility Bill")
    body_text: str = Field(default="Please process the attached bill.")
    attachments: List[Dict[str, str]] = Field(
        default=[],
        description="List of {filename, content_type, content_base64}"
    )
    company_id: Optional[str] = None


class EmailTestRequest(BaseModel):
    """Quick test with just text content."""
    email_body: str
    from_address: str = "test@company.com"
    subject: str = "Test Sustainability Document"
    company_id: Optional[str] = None


# ==================== Webhook Endpoints ====================

@router.post("/webhook/sendgrid")
async def sendgrid_webhook(request: Request):
    """
    📧 SendGrid Inbound Parse Webhook
    
    Configure SendGrid to POST to this endpoint:
    1. Go to SendGrid > Settings > Inbound Parse
    2. Add domain (e.g., inbound.yourdomain.com)
    3. Set URL to: https://yourserver.com/api/v1/email/webhook/sendgrid
    
    Forwarded emails will be automatically processed.
    """
    try:
        # Parse form data
        form_data = await request.form()
        payload = {key: form_data[key] for key in form_data}
        
        # Handle file attachments
        for key in form_data:
            if key.startswith('attachment'):
                file = form_data[key]
                if hasattr(file, 'read'):
                    content = await file.read()
                    payload[key] = base64.b64encode(content).decode('utf-8')
        
        # Parse email
        parsed = email_processor.parse_sendgrid(payload)
        
        # Validate sender
        if not email_processor.validate_sender(parsed.from_address):
            return {"status": "rejected", "reason": "Sender not allowed"}
        
        # Process
        result = await email_processor.process_email(parsed)
        
        return {
            "status": result.status,
            "email_id": result.email_id,
            "items_created": result.items_created,
            "items": result.items,
            "errors": result.errors if result.errors else None,
            "processing_time_ms": result.processing_time_ms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/webhook/mailgun")
async def mailgun_webhook(request: Request):
    """
    📧 Mailgun Routes Webhook
    
    Configure Mailgun to POST to this endpoint:
    1. Go to Mailgun > Receiving > Routes
    2. Create route matching your sustainability inbox
    3. Set action to forward to: https://yourserver.com/api/v1/email/webhook/mailgun
    """
    try:
        # Mailgun sends JSON
        payload = await request.json()
        
        parsed = email_processor.parse_mailgun(payload)
        
        if not email_processor.validate_sender(parsed.from_address):
            return {"status": "rejected", "reason": "Sender not allowed"}
        
        result = await email_processor.process_email(parsed)
        
        return {
            "status": result.status,
            "email_id": result.email_id,
            "items_created": result.items_created,
            "items": result.items,
            "errors": result.errors if result.errors else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/webhook/microsoft")
async def microsoft_webhook(request: Request):
    """
    📧 Microsoft Graph Webhook (Office 365)
    
    For Office 365 / Outlook integration:
    1. Register app in Azure AD
    2. Subscribe to mail notifications
    3. Configure webhook URL to this endpoint
    
    Requires additional setup for OAuth and Graph API.
    """
    try:
        # Microsoft sends JSON
        payload = await request.json()
        
        # Handle validation request
        if 'validationToken' in payload:
            return payload['validationToken']
        
        parsed = email_processor.parse_microsoft(payload)
        
        if not email_processor.validate_sender(parsed.from_address):
            return {"status": "rejected", "reason": "Sender not allowed"}
        
        result = await email_processor.process_email(parsed)
        
        return {
            "status": result.status,
            "email_id": result.email_id,
            "items_created": result.items_created
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


# ==================== Testing & Simulation ====================

@router.post("/test")
async def test_email_processing(request: EmailTestRequest):
    """
    🧪 Test email processing with text content.
    
    Simulates receiving an email with sustainability data in the body.
    Useful for testing without setting up full email integration.
    
    Example:
    ```json
    {
        "email_body": "Pacific Gas & Electric\\nUsage: 500 kWh\\nTotal: $100",
        "from_address": "user@company.com",
        "subject": "Utility Bill January 2024"
    }
    ```
    """
    # Create simulated parsed email
    parsed = ParsedEmail(
        message_id=f"<test-{hash(request.email_body)}>",
        from_address=request.from_address,
        from_name=None,
        to_address="sustainability@company.com",
        subject=request.subject,
        body_text=request.email_body,
        body_html=None,
        received_at="",
        attachments=[],
        headers={}
    )
    
    result = await email_processor.process_email(
        parsed,
        company_id=request.company_id
    )
    
    return {
        "status": result.status,
        "items_created": result.items_created,
        "items": result.items,
        "errors": result.errors if result.errors else None,
        "confirmation_email": email_processor.generate_confirmation_email(result, parsed)
    }


@router.post("/simulate")
async def simulate_email(email: SimulatedEmail):
    """
    🎭 Simulate a complete email with attachments.
    
    For testing the full flow including attachments.
    
    Example:
    ```json
    {
        "from_address": "john@company.com",
        "subject": "FW: Electricity Bill",
        "body_text": "Please process attached bill",
        "attachments": [
            {
                "filename": "bill.txt",
                "content_type": "text/plain",
                "content_base64": "UEcmRSBFbGVjdHJpYyBCaWxsCjUwMCBrV2gKJDEwMA=="
            }
        ]
    }
    ```
    """
    from modules.sustainability.email_processor import EmailAttachment
    
    attachments = [
        EmailAttachment(
            filename=att["filename"],
            content_type=att["content_type"],
            content_base64=att["content_base64"],
            size_bytes=len(base64.b64decode(att["content_base64"]))
        )
        for att in email.attachments
    ]
    
    parsed = ParsedEmail(
        message_id=f"<simulated-{hash(email.subject)}>",
        from_address=email.from_address,
        from_name=email.from_name,
        to_address=email.to_address,
        subject=email.subject,
        body_text=email.body_text,
        body_html=None,
        received_at="",
        attachments=attachments,
        headers={}
    )
    
    result = await email_processor.process_email(
        parsed,
        company_id=email.company_id
    )
    
    return {
        "status": result.status,
        "email_id": result.email_id,
        "from": email.from_address,
        "subject": email.subject,
        "attachments_received": len(email.attachments),
        "items_created": result.items_created,
        "items": result.items,
        "errors": result.errors if result.errors else None,
        "processing_time_ms": result.processing_time_ms
    }


@router.post("/upload-raw")
async def upload_raw_email(
    file: UploadFile = File(..., description="Raw .eml file"),
    company_id: Optional[str] = None
):
    """
    📎 Upload a raw .eml file for processing.
    
    Accepts RFC 822 formatted email files.
    Useful for batch processing exported emails.
    """
    content = await file.read()
    
    try:
        parsed = email_processor.parse_raw_email(content)
        
        result = await email_processor.process_email(
            parsed,
            company_id=company_id
        )
        
        return {
            "status": result.status,
            "filename": file.filename,
            "from": parsed.from_address,
            "subject": parsed.subject,
            "attachments_found": len(parsed.attachments),
            "items_created": result.items_created,
            "items": result.items,
            "errors": result.errors if result.errors else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse email: {str(e)}")


# ==================== Configuration & Status ====================

@router.get("/config")
async def get_email_config():
    """
    ⚙️ Get email integration configuration.
    
    Shows setup instructions for each supported provider.
    """
    return {
        "status": "active",
        "supported_providers": ["sendgrid", "mailgun", "microsoft", "raw"],
        "endpoints": {
            "sendgrid": "/api/v1/email/webhook/sendgrid",
            "mailgun": "/api/v1/email/webhook/mailgun",
            "microsoft": "/api/v1/email/webhook/microsoft",
            "raw_upload": "/api/v1/email/upload-raw",
            "test": "/api/v1/email/test",
            "simulate": "/api/v1/email/simulate"
        },
        "setup_instructions": {
            "sendgrid": {
                "steps": [
                    "1. Go to SendGrid Dashboard > Settings > Inbound Parse",
                    "2. Add a domain (e.g., sustainability.yourdomain.com)",
                    "3. Configure MX record for your domain",
                    "4. Set webhook URL to: https://yourserver/api/v1/email/webhook/sendgrid",
                    "5. Enable 'Post the raw, full MIME message'"
                ],
                "required_fields": ["from", "to", "subject", "text", "attachments"]
            },
            "mailgun": {
                "steps": [
                    "1. Go to Mailgun > Receiving > Routes",
                    "2. Create a new route",
                    "3. Match expression: match_recipient('sustainability@yourdomain.com')",
                    "4. Action: forward('https://yourserver/api/v1/email/webhook/mailgun')"
                ]
            },
            "microsoft": {
                "steps": [
                    "1. Register app in Azure AD",
                    "2. Add Mail.Read permission",
                    "3. Create subscription via Graph API",
                    "4. Set notificationUrl to webhook endpoint"
                ],
                "note": "Requires OAuth setup - contact admin"
            }
        },
        "features": {
            "supported_attachments": ["PDF", "JPG", "PNG", "TXT", "CSV"],
            "max_attachment_size": "10MB",
            "auto_approve_threshold": 0.95,
            "ocr_enabled": email_processor.ocr_engine is not None
        }
    }


@router.get("/", response_class=HTMLResponse)
async def email_setup_page():
    """
    📧 Email Integration Setup Page
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>📧 Email Integration Setup</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #10b981;
            --border: #475569;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 40px;
            line-height: 1.6;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { font-size: 2rem; margin-bottom: 10px; }
        .subtitle { color: var(--muted); margin-bottom: 30px; }
        .card {
            background: var(--card);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid var(--border);
        }
        .card h2 {
            font-size: 1.2rem;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .steps {
            list-style: none;
            counter-reset: step;
        }
        .steps li {
            counter-increment: step;
            padding: 10px 0;
            padding-left: 40px;
            position: relative;
            border-bottom: 1px solid var(--border);
        }
        .steps li:last-child { border-bottom: none; }
        .steps li::before {
            content: counter(step);
            position: absolute;
            left: 0;
            width: 28px;
            height: 28px;
            background: var(--accent);
            color: var(--bg);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9rem;
        }
        code {
            background: var(--bg);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9rem;
            color: var(--accent);
        }
        .test-form {
            margin-top: 20px;
        }
        textarea {
            width: 100%;
            height: 150px;
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            resize: vertical;
        }
        button {
            margin-top: 15px;
            padding: 12px 24px;
            background: var(--accent);
            color: var(--bg);
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-size: 1rem;
        }
        button:hover { background: #059669; }
        #result {
            margin-top: 20px;
            padding: 15px;
            background: var(--bg);
            border-radius: 8px;
            font-family: monospace;
            white-space: pre-wrap;
            display: none;
        }
        .email-icon { font-size: 1.5rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Email Integration Setup</h1>
        <p class="subtitle">Forward sustainability documents to process automatically</p>
        
        <div class="card">
            <h2><span class="email-icon">📨</span> How It Works</h2>
            <p style="color: var(--muted); margin-bottom: 15px;">
                Users forward utility bills, receipts, and invoices to a dedicated email address.
                The system automatically extracts data and adds it to the review queue.
            </p>
            <code>sustainability@yourcompany.com → AI Processing → Review Dashboard</code>
        </div>
        
        <div class="card">
            <h2><span class="email-icon">📮</span> SendGrid Setup</h2>
            <ol class="steps">
                <li>Go to SendGrid Dashboard → Settings → Inbound Parse</li>
                <li>Add receiving domain (e.g., <code>inbound.yourcompany.com</code>)</li>
                <li>Configure MX record pointing to <code>mx.sendgrid.net</code></li>
                <li>Set webhook URL: <code>/api/v1/email/webhook/sendgrid</code></li>
                <li>Enable "Post raw MIME" and "Send attachments"</li>
            </ol>
        </div>
        
        <div class="card">
            <h2><span class="email-icon">📬</span> Mailgun Setup</h2>
            <ol class="steps">
                <li>Go to Mailgun → Receiving → Create Route</li>
                <li>Match: <code>match_recipient("sustainability@.*")</code></li>
                <li>Action: <code>forward("/api/v1/email/webhook/mailgun")</code></li>
                <li>Enable "Store and notify"</li>
            </ol>
        </div>
        
        <div class="card">
            <h2><span class="email-icon">🧪</span> Test Email Processing</h2>
            <p style="color: var(--muted); margin-bottom: 15px;">
                Paste sustainability data below to test extraction:
            </p>
            <div class="test-form">
                <textarea id="test-content" placeholder="Pacific Gas & Electric
Account: 1234567890
Billing Period: January 2024
Usage: 500 kWh
Total Due: $95.00">Pacific Gas & Electric
Account: 1234567890
Service Address: 123 Main St, SF
Billing Period: January 2024
Usage: 500 kWh
Total Due: $95.00</textarea>
                <button onclick="testEmail()">🚀 Test Processing</button>
            </div>
            <pre id="result"></pre>
        </div>
    </div>
    
    <script>
        async function testEmail() {
            const content = document.getElementById('test-content').value;
            const result = document.getElementById('result');
            
            result.style.display = 'block';
            result.textContent = 'Processing...';
            
            try {
                const res = await fetch('/api/v1/email/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email_body: content,
                        from_address: 'test@company.com',
                        subject: 'Test Document'
                    })
                });
                
                const data = await res.json();
                result.textContent = JSON.stringify(data, null, 2);
                
            } catch (e) {
                result.textContent = 'Error: ' + e.message;
            }
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


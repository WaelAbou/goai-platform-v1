"""
Review Dashboard API

Enterprise UX for reviewing AI-extracted sustainability data.

Pattern: "AI Assists, Human Approves"
- AI extracts data and assigns confidence
- Items appear in review queue
- Humans approve, reject, or edit
- Approved data flows to system of record

Now uses UNIFIED DATABASE: data/sustainability_unified.db
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Use unified service (single database)
from modules.sustainability.unified_service import unified_service
from modules.sustainability.smart_ingestion import smart_processor

router = APIRouter()


# ==================== Request/Response Models ====================

class SubmitDocumentRequest(BaseModel):
    """Request to submit a document for review."""
    text_content: Optional[str] = None
    image_base64: Optional[str] = None
    source: str = Field(default="api", description="Source: api, email, sharepoint, mobile")
    filename: str = Field(default="document.txt")
    uploaded_by: str = Field(default="anonymous")
    company_id: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request to approve a review item."""
    approved_data: Optional[Dict[str, Any]] = Field(None, description="Modified data if edited")
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    """Request to reject a review item."""
    reason: str


class BulkApproveRequest(BaseModel):
    """Request to bulk approve items."""
    item_ids: List[str]
    min_confidence: float = Field(default=0.9, ge=0, le=1)


class FlagRequest(BaseModel):
    """Request to flag an item."""
    reason: str


# ==================== Queue Endpoints ====================

@router.get("/queue")
async def get_review_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    confidence: Optional[str] = Query(None, description="Filter by confidence level"),
    category: Optional[str] = Query(None, description="Filter by category"),
    company_id: Optional[str] = Query(None, description="Filter by company"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("uploaded_at"),
    sort_order: str = Query("desc")
):
    """
    📋 Get the review queue with filters.
    
    The review queue shows all documents that need human review.
    
    Query Parameters:
    - status: pending, approved, rejected, auto_approved
    - confidence: high (>90%), medium (70-90%), low (<70%)
    - category: energy, travel, fleet, shipping, etc.
    """
    items = unified_service.get_queue(
        status=status,
        confidence_level=confidence,
        category=category,
        company_id=company_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return {
        "items": [item.to_dict() for item in items],
        "count": len(items),
        "filters": {
            "status": status,
            "confidence": confidence,
            "category": category,
            "company_id": company_id
        },
        "pagination": {
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/queue/{item_id}")
async def get_review_item(item_id: str):
    """
    📄 Get a single review item with full details.
    
    Returns the complete item including extracted data and raw text.
    """
    item = unified_service.get_item(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "item": item.to_dict(),
        "audit_log": unified_service.get_audit_log(entity_id=item_id, limit=20)
    }


@router.post("/submit")
async def submit_document(request: SubmitDocumentRequest):
    """
    📤 Submit a document for AI extraction and review.
    
    The document will be:
    1. Processed by AI to extract sustainability data
    2. Assigned a confidence score
    3. Added to the review queue
    
    High confidence items (>95%) may be auto-approved.
    """
    if not request.text_content and not request.image_base64:
        raise HTTPException(status_code=400, detail="Either text_content or image_base64 required")
    
    try:
        # Process with smart ingestion
        result = await smart_processor.process_document(
            text_content=request.text_content,
            image_base64=request.image_base64
        )
        
        # Add to unified database
        item_id = unified_service.submit_document(
            company_id=request.company_id or "default",
            document_type=result.document_type.value,
            category=result.template,
            filename=request.filename,
            raw_text=result.raw_text,
            extracted_data=result.data,
            calculated_co2e_kg=result.calculated_co2e_kg,
            confidence=result.confidence,
            uploaded_by=request.uploaded_by,
            source=request.source
        )
        
        # Get the created item
        item = unified_service.get_item(item_id)
        
        return {
            "status": "success",
            "item_id": item_id,
            "queue_status": item.status if item else "pending",
            "confidence": result.confidence,
            "confidence_level": item.confidence_level if item else "low",
            "document_type": result.document_type.value,
            "extracted_data": result.data,
            "calculated_co2e_kg": result.calculated_co2e_kg,
            "message": "Auto-approved due to high confidence" if (item and item.status == "auto_approved") else "Added to review queue"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ==================== Review Actions ====================

@router.post("/queue/{item_id}/approve")
async def approve_item(
    item_id: str,
    request: ApproveRequest,
    user: str = Query("reviewer", description="User performing the action")
):
    """
    ✅ Approve a review item.
    
    Optionally provide modified data if corrections were made.
    """
    success = unified_service.approve_item(
        item_id=item_id,
        user_email=user,
        approved_data=request.approved_data,
        notes=request.notes
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "status": "success",
        "message": f"Item {item_id} approved",
        "changes_made": request.approved_data is not None
    }


@router.post("/queue/{item_id}/reject")
async def reject_item(
    item_id: str,
    request: RejectRequest,
    user: str = Query("reviewer")
):
    """
    ❌ Reject a review item.
    
    Must provide a reason for rejection.
    """
    success = unified_service.reject_item(
        item_id=item_id,
        user_email=user,
        reason=request.reason
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "status": "success",
        "message": f"Item {item_id} rejected",
        "reason": request.reason
    }


class DeleteRequest(BaseModel):
    """Request to delete a review item."""
    reason: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    """Request to bulk delete items."""
    item_ids: List[str]
    reason: Optional[str] = None


@router.delete("/queue/{item_id}")
async def delete_item(
    item_id: str,
    user: str = Query("admin"),
    reason: Optional[str] = Query(None)
):
    """
    🗑️ Delete a review item from the queue.
    
    Permanently removes the item. This action is logged in the audit trail.
    """
    success = unified_service.delete_item(
        item_id=item_id,
        user_email=user
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "status": "success",
        "message": f"Item {item_id} deleted",
        "deleted_by": user,
        "reason": reason
    }


@router.post("/queue/bulk-delete")
async def bulk_delete_items(
    request: BulkDeleteRequest,
    user: str = Query("admin")
):
    """
    🗑️🗑️ Bulk delete multiple items.
    
    Permanently removes all specified items.
    """
    deleted_count = unified_service.bulk_delete(
        item_ids=request.item_ids,
        user_email=user
    )
    
    return {
        "status": "success",
        "deleted": deleted_count,
        "requested": len(request.item_ids)
    }


@router.post("/queue/{item_id}/flag")
async def flag_item(
    item_id: str,
    request: FlagRequest,
    user: str = Query("reviewer")
):
    """
    🚩 Flag an item for attention.
    
    Use this to mark items that need special handling.
    """
    success = unified_service.flag_item(
        item_id=item_id,
        reason=request.reason,
        user_email=user
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "status": "success",
        "message": f"Item {item_id} flagged"
    }


@router.post("/queue/bulk-approve")
async def bulk_approve_items(
    request: BulkApproveRequest,
    user: str = Query("reviewer")
):
    """
    ✅✅ Bulk approve multiple items.
    
    Only items with confidence >= min_confidence will be approved.
    Others will be skipped with explanation.
    """
    # Bulk approve by approving each item meeting confidence threshold
    approved = 0
    skipped = 0
    for item_id in request.item_ids:
        item = unified_service.get_item(item_id)
        if item and item.confidence >= request.min_confidence:
            unified_service.approve_item(item_id, user)
            approved += 1
        else:
            skipped += 1
    
    return {
        "status": "success",
        "approved": approved,
        "skipped": skipped,
        "min_confidence": request.min_confidence
    }


# ==================== Statistics & Dashboard ====================

@router.get("/stats")
async def get_statistics():
    """
    📊 Get queue statistics for the dashboard.
    
    Returns:
    - Queue summary (pending, approved, rejected counts)
    - Breakdown by confidence level
    - Breakdown by category
    - Emissions totals
    - Recent activity
    """
    return unified_service.get_stats()


@router.get("/audit-log")
async def get_audit_log(
    item_id: Optional[str] = None,
    user: Optional[str] = None,
    limit: int = Query(100, le=500)
):
    """
    📜 Get audit log entries.
    
    Every action is logged for compliance.
    """
    entries = unified_service.get_audit_log(
        entity_id=item_id,
        limit=limit
    )
    
    return {
        "entries": entries,
        "count": len(entries)
    }


# ==================== Analytics Endpoints ====================

@router.get("/analytics")
async def get_analytics(
    time_range: str = Query("6months", description="Time range: 1month, 3months, 6months, 1year"),
    company_id: Optional[str] = Query(None, description="Filter by company")
):
    """
    📊 Get comprehensive analytics data for dashboards.
    
    Returns:
    - Monthly trends (submissions, approvals, rejections)
    - Category distribution
    - Top contributors
    - Review time metrics
    - Overall statistics
    """
    analytics = unified_service.get_analytics(
        time_range=time_range,
        company_id=company_id
    )
    return analytics


@router.get("/analytics/monthly")
async def get_monthly_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to include"),
    company_id: Optional[str] = Query(None)
):
    """
    📈 Get monthly submission trends.
    
    Returns uploads, approved, and rejected counts per month.
    """
    data = unified_service.get_monthly_trends(months=months, company_id=company_id)
    return {"months": data}


@router.get("/analytics/categories")
async def get_category_distribution(
    company_id: Optional[str] = Query(None)
):
    """
    🥧 Get document category distribution.
    
    Returns breakdown by document type/category.
    """
    data = unified_service.get_category_distribution(company_id=company_id)
    return {"categories": data}


@router.get("/analytics/contributors")
async def get_top_contributors(
    limit: int = Query(10, le=50),
    company_id: Optional[str] = Query(None)
):
    """
    👥 Get top document contributors.
    
    Returns users ranked by submissions and approval rates.
    """
    data = unified_service.get_top_contributors(limit=limit, company_id=company_id)
    return {"contributors": data}


@router.get("/analytics/emissions")
async def get_emissions_analytics(
    time_range: str = Query("6months"),
    company_id: Optional[str] = Query(None)
):
    """
    🌱 Get emissions analytics.
    
    Returns CO2e trends and breakdowns.
    """
    data = unified_service.get_emissions_analytics(time_range=time_range, company_id=company_id)
    return data


# ==================== HTML Dashboard ====================

@router.get("/", response_class=HTMLResponse)
async def dashboard_ui():
    """
    🖥️ Interactive Review Dashboard UI
    
    A beautiful, responsive dashboard for reviewing sustainability data.
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌱 Sustainability Data Review Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --border: #475569;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header .badge {
            background: var(--accent-green);
            color: var(--bg-primary);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
        }
        
        .stat-card .value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .stat-card .label {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        .stat-card.pending .value { color: var(--accent-yellow); }
        .stat-card.approved .value { color: var(--accent-green); }
        .stat-card.emissions .value { color: var(--accent-blue); }
        .stat-card.rate .value { color: var(--accent-purple); }
        
        /* Filters */
        .filters {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .filter-select {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.9rem;
            cursor: pointer;
        }
        
        .filter-select:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        
        .bulk-actions {
            margin-left: auto;
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: var(--accent-green);
            color: var(--bg-primary);
        }
        
        .btn-primary:hover {
            background: #059669;
        }
        
        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }
        
        /* Queue Table */
        .queue-table {
            background: var(--bg-secondary);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        
        .queue-header {
            display: grid;
            grid-template-columns: 40px 80px 1fr 120px 150px 150px 150px;
            padding: 15px 20px;
            background: var(--bg-tertiary);
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .queue-item {
            display: grid;
            grid-template-columns: 40px 80px 1fr 120px 150px 150px 150px;
            padding: 15px 20px;
            border-bottom: 1px solid var(--border);
            align-items: center;
            transition: background 0.2s;
        }
        
        .queue-item:hover {
            background: var(--bg-tertiary);
        }
        
        .queue-item:last-child {
            border-bottom: none;
        }
        
        .checkbox {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .confidence {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .confidence-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .confidence-dot.high { background: var(--accent-green); }
        .confidence-dot.medium { background: var(--accent-yellow); }
        .confidence-dot.low { background: var(--accent-red); }
        
        .doc-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        
        .doc-type {
            font-weight: 600;
        }
        
        .doc-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .emissions {
            font-weight: 600;
        }
        
        .emissions.positive {
            color: var(--accent-green);
        }
        
        .category-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            background: var(--bg-tertiary);
        }
        
        .category-badge.energy { background: #fef3c7; color: #92400e; }
        .category-badge.travel { background: #dbeafe; color: #1e40af; }
        .category-badge.fleet { background: #fce7f3; color: #9d174d; }
        .category-badge.shipping { background: #d1fae5; color: #065f46; }
        
        .actions {
            display: flex;
            gap: 8px;
        }
        
        .action-btn {
            padding: 6px 12px;
            border-radius: 6px;
            border: none;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .action-btn.approve {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }
        
        .action-btn.approve:hover {
            background: var(--accent-green);
            color: var(--bg-primary);
        }
        
        .action-btn.review {
            background: rgba(245, 158, 11, 0.2);
            color: var(--accent-yellow);
        }
        
        .action-btn.review:hover {
            background: var(--accent-yellow);
            color: var(--bg-primary);
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal {
            background: var(--bg-secondary);
            border-radius: 16px;
            width: 90%;
            max-width: 1200px;
            max-height: 90vh;
            overflow: hidden;
            display: grid;
            grid-template-columns: 1fr 1fr;
        }
        
        .modal-left, .modal-right {
            padding: 30px;
            overflow-y: auto;
            max-height: 90vh;
        }
        
        .modal-left {
            background: var(--bg-primary);
            border-right: 1px solid var(--border);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .modal-header h2 {
            font-size: 1.3rem;
        }
        
        .close-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
        }
        
        .raw-text {
            background: var(--bg-tertiary);
            padding: 20px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.9rem;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .extracted-fields {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .field-row {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .field-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .field-input {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.95rem;
        }
        
        .field-input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        
        .modal-actions {
            display: flex;
            gap: 10px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }
        
        .modal-actions .btn {
            flex: 1;
        }
        
        .btn-danger {
            background: var(--accent-red);
            color: white;
        }
        
        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--accent-green);
            color: var(--bg-primary);
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: 600;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 2000;
        }
        
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border);
            border-top-color: var(--accent-blue);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .queue-header, .queue-item {
                grid-template-columns: 40px 1fr 120px 120px;
            }
            .queue-header > *:nth-child(2),
            .queue-item > *:nth-child(2),
            .queue-header > *:nth-child(5),
            .queue-item > *:nth-child(5) {
                display: none;
            }
        }
        
        @media (max-width: 768px) {
            .modal {
                grid-template-columns: 1fr;
            }
            .filters {
                flex-direction: column;
            }
            .bulk-actions {
                margin-left: 0;
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>
                🌱 Sustainability Data Review
                <span class="badge" id="pending-badge">0 pending</span>
            </h1>
            <div style="color: var(--text-secondary)">
                <span id="current-time"></span>
            </div>
        </div>
        
        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card pending">
                <div class="value" id="stat-pending">-</div>
                <div class="label">Pending Review</div>
            </div>
            <div class="stat-card approved">
                <div class="value" id="stat-approved">-</div>
                <div class="label">Approved Today</div>
            </div>
            <div class="stat-card emissions">
                <div class="value" id="stat-emissions">-</div>
                <div class="label">CO₂e Tracked (tonnes)</div>
            </div>
            <div class="stat-card rate">
                <div class="value" id="stat-rate">-</div>
                <div class="label">Auto-Approve Rate</div>
            </div>
        </div>
        
        <!-- Filters -->
        <div class="filters">
            <select class="filter-select" id="filter-status">
                <option value="">All Status</option>
                <option value="pending" selected>Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="auto_approved">Auto-Approved</option>
            </select>
            
            <select class="filter-select" id="filter-confidence">
                <option value="">All Confidence</option>
                <option value="high">🟢 High (>90%)</option>
                <option value="medium">🟡 Medium (70-90%)</option>
                <option value="low">🔴 Low (<70%)</option>
            </select>
            
            <select class="filter-select" id="filter-category">
                <option value="">All Categories</option>
                <option value="energy">⚡ Energy</option>
                <option value="travel">✈️ Travel</option>
                <option value="fleet">🚗 Fleet</option>
                <option value="shipping">📦 Shipping</option>
                <option value="waste">♻️ Waste</option>
            </select>
            
            <div class="bulk-actions">
                <button class="btn btn-primary" onclick="bulkApprove()">
                    ✅ Bulk Approve High Confidence
                </button>
                <button class="btn btn-secondary" onclick="loadQueue()">
                    🔄 Refresh
                </button>
            </div>
        </div>
        
        <!-- Queue Table -->
        <div class="queue-table">
            <div class="queue-header">
                <div><input type="checkbox" class="checkbox" id="select-all" onclick="toggleSelectAll()"></div>
                <div>Confidence</div>
                <div>Document</div>
                <div>Category</div>
                <div>Emissions</div>
                <div>Uploaded</div>
                <div>Actions</div>
            </div>
            <div id="queue-body">
                <div class="loading">
                    <div class="spinner"></div>
                    Loading review queue...
                </div>
            </div>
        </div>
    </div>
    
    <!-- Review Modal -->
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <div class="modal-left">
                <div class="modal-header">
                    <h2>📄 Original Document</h2>
                </div>
                <div class="raw-text" id="modal-raw-text">
                    Loading...
                </div>
            </div>
            <div class="modal-right">
                <div class="modal-header">
                    <h2>📋 Extracted Data</h2>
                    <button class="close-btn" onclick="closeModal()">×</button>
                </div>
                <div class="confidence" style="margin-bottom: 20px;">
                    <span class="confidence-dot" id="modal-confidence-dot"></span>
                    <span id="modal-confidence-text">95% Confidence</span>
                </div>
                <div class="extracted-fields" id="modal-fields">
                    Loading...
                </div>
                <div class="modal-actions">
                    <button class="btn btn-danger" onclick="rejectItem()">❌ Reject</button>
                    <button class="btn btn-primary" onclick="approveItem()">✅ Approve</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Toast -->
    <div class="toast" id="toast">Action completed!</div>
    
    <script>
        const API_BASE = '/api/v1/review';
        let currentItemId = null;
        let selectedItems = new Set();
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadQueue();
            updateTime();
            setInterval(updateTime, 1000);
            
            // Filter change handlers
            document.getElementById('filter-status').addEventListener('change', loadQueue);
            document.getElementById('filter-confidence').addEventListener('change', loadQueue);
            document.getElementById('filter-category').addEventListener('change', loadQueue);
        });
        
        function updateTime() {
            document.getElementById('current-time').textContent = 
                new Date().toLocaleString('en-US', {
                    weekday: 'short', month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                });
        }
        
        // XSS Protection: Escape HTML special characters
        function escapeHtml(unsafe) {
            if (unsafe === null || unsafe === undefined) return '';
            return String(unsafe)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
        
        // Safe attribute value (for use in HTML attributes)
        function safeAttr(unsafe) {
            if (unsafe === null || unsafe === undefined) return '';
            return String(unsafe)
                .replace(/&/g, '&amp;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }
        
        async function loadStats() {
            try {
                const res = await fetch(`${API_BASE}/stats`);
                const data = await res.json();
                
                document.getElementById('stat-pending').textContent = data.queue_summary.pending;
                document.getElementById('stat-approved').textContent = 
                    data.queue_summary.approved + data.queue_summary.auto_approved;
                document.getElementById('stat-emissions').textContent = 
                    data.emissions.approved_tonnes.toFixed(1);
                document.getElementById('stat-rate').textContent = 
                    data.activity.auto_approve_rate + '%';
                document.getElementById('pending-badge').textContent = 
                    `${data.queue_summary.pending} pending`;
            } catch (e) {
                console.error('Failed to load stats:', e);
            }
        }
        
        async function loadQueue() {
            const status = document.getElementById('filter-status').value;
            const confidence = document.getElementById('filter-confidence').value;
            const category = document.getElementById('filter-category').value;
            
            let url = `${API_BASE}/queue?limit=50`;
            if (status) url += `&status=${status}`;
            if (confidence) url += `&confidence=${confidence}`;
            if (category) url += `&category=${category}`;
            
            try {
                const res = await fetch(url);
                const data = await res.json();
                
                renderQueue(data.items);
            } catch (e) {
                console.error('Failed to load queue:', e);
                document.getElementById('queue-body').innerHTML = 
                    '<div class="loading">Failed to load queue. Please try again.</div>';
            }
        }
        
        function renderQueue(items) {
            if (items.length === 0) {
                document.getElementById('queue-body').innerHTML = 
                    '<div class="loading">🎉 No items to review!</div>';
                return;
            }
            
            const html = items.map(item => {
                // Sanitize all user-controlled data
                const safeId = safeAttr(item.id);
                const safeFilename = escapeHtml(item.filename);
                const safeUploadedBy = escapeHtml(item.uploaded_by);
                const safeDocType = escapeHtml(formatDocType(item.document_type));
                const safeCategory = safeAttr(item.category);
                const safeCategoryDisplay = escapeHtml(item.category);
                const safeConfidenceLevel = safeAttr(item.confidence_level);
                
                return `
                <div class="queue-item" data-id="${safeId}">
                    <div>
                        <input type="checkbox" class="checkbox item-checkbox" 
                               data-id="${safeId}" onchange="toggleSelect('${safeId}')">
                    </div>
                    <div class="confidence">
                        <span class="confidence-dot ${safeConfidenceLevel}"></span>
                        <span>${Math.round(Number(item.confidence) * 100) || 0}%</span>
                    </div>
                    <div class="doc-info">
                        <span class="doc-type">${safeDocType}</span>
                        <span class="doc-meta">${safeFilename} • ${safeUploadedBy}</span>
                    </div>
                    <div>
                        <span class="category-badge ${safeCategory}">${safeCategoryDisplay}</span>
                    </div>
                    <div class="emissions ${item.calculated_co2e_kg ? 'positive' : ''}">
                        ${item.calculated_co2e_kg ? formatEmissions(Number(item.calculated_co2e_kg)) : '-'}
                    </div>
                    <div class="doc-meta">
                        ${formatDate(item.uploaded_at)}
                    </div>
                    <div class="actions">
                        ${item.confidence >= 0.9 ? 
                            `<button class="action-btn approve" onclick="quickApprove('${safeId}')">Approve</button>` :
                            `<button class="action-btn review" onclick="openReview('${safeId}')">Review</button>`
                        }
                    </div>
                </div>`;
            }).join('');
            
            document.getElementById('queue-body').innerHTML = html;
        }
        
        function formatDocType(type) {
            return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        
        function formatEmissions(kg) {
            if (kg >= 1000) {
                return (kg / 1000).toFixed(2) + ' t CO₂e';
            }
            return kg.toFixed(0) + ' kg CO₂e';
        }
        
        function formatDate(isoString) {
            const date = new Date(isoString);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
        
        async function openReview(itemId) {
            currentItemId = itemId;
            
            try {
                const res = await fetch(`${API_BASE}/queue/${itemId}`);
                const data = await res.json();
                const item = data.item;
                
                // Show raw text
                document.getElementById('modal-raw-text').textContent = 
                    item.raw_text || 'No raw text available';
                
                // Show confidence
                const dot = document.getElementById('modal-confidence-dot');
                dot.className = `confidence-dot ${item.confidence_level}`;
                document.getElementById('modal-confidence-text').textContent = 
                    `${Math.round(item.confidence * 100)}% Confidence`;
                
                // Build fields with XSS protection
                const fields = Object.entries(item.extracted_data || {}).map(([key, value]) => {
                    const safeKey = safeAttr(key);
                    const safeKeyDisplay = escapeHtml(formatDocType(key));
                    const safeValue = safeAttr(value ?? '');
                    
                    return `
                    <div class="field-row">
                        <label class="field-label">${safeKeyDisplay}</label>
                        <input type="text" class="field-input" 
                               data-field="${safeKey}" value="${safeValue}">
                    </div>`;
                }).join('');
                
                document.getElementById('modal-fields').innerHTML = fields || 
                    '<p style="color: var(--text-secondary)">No data extracted</p>';
                
                // Show modal
                document.getElementById('modal').classList.add('active');
                
            } catch (e) {
                console.error('Failed to load item:', e);
                showToast('Failed to load item');
            }
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
            currentItemId = null;
        }
        
        async function approveItem() {
            if (!currentItemId) return;
            
            // Collect edited data
            const inputs = document.querySelectorAll('#modal-fields .field-input');
            const approvedData = {};
            inputs.forEach(input => {
                approvedData[input.dataset.field] = input.value;
            });
            
            try {
                const res = await fetch(`${API_BASE}/queue/${currentItemId}/approve?user=dashboard_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ approved_data: approvedData })
                });
                
                if (res.ok) {
                    showToast('✅ Item approved!');
                    closeModal();
                    loadQueue();
                    loadStats();
                }
            } catch (e) {
                console.error('Failed to approve:', e);
                showToast('Failed to approve item');
            }
        }
        
        async function rejectItem() {
            if (!currentItemId) return;
            
            const reason = prompt('Reason for rejection:');
            if (!reason) return;
            
            try {
                const res = await fetch(`${API_BASE}/queue/${currentItemId}/reject?user=dashboard_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason })
                });
                
                if (res.ok) {
                    showToast('❌ Item rejected');
                    closeModal();
                    loadQueue();
                    loadStats();
                }
            } catch (e) {
                console.error('Failed to reject:', e);
            }
        }
        
        async function quickApprove(itemId) {
            try {
                const res = await fetch(`${API_BASE}/queue/${itemId}/approve?user=dashboard_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                
                if (res.ok) {
                    showToast('✅ Approved!');
                    loadQueue();
                    loadStats();
                }
            } catch (e) {
                console.error('Failed to approve:', e);
            }
        }
        
        async function bulkApprove() {
            const checkboxes = document.querySelectorAll('.item-checkbox:checked');
            const ids = Array.from(checkboxes).map(cb => cb.dataset.id);
            
            if (ids.length === 0) {
                // If nothing selected, approve all high confidence
                const res = await fetch(`${API_BASE}/queue?status=pending&confidence=high&limit=100`);
                const data = await res.json();
                ids.push(...data.items.map(i => i.id));
            }
            
            if (ids.length === 0) {
                showToast('No items to approve');
                return;
            }
            
            try {
                const res = await fetch(`${API_BASE}/queue/bulk-approve?user=dashboard_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_ids: ids, min_confidence: 0.9 })
                });
                
                const data = await res.json();
                showToast(`✅ Approved ${data.approved} items`);
                loadQueue();
                loadStats();
                
            } catch (e) {
                console.error('Failed to bulk approve:', e);
            }
        }
        
        function toggleSelect(itemId) {
            if (selectedItems.has(itemId)) {
                selectedItems.delete(itemId);
            } else {
                selectedItems.add(itemId);
            }
        }
        
        function toggleSelectAll() {
            const checkAll = document.getElementById('select-all').checked;
            const checkboxes = document.querySelectorAll('.item-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = checkAll;
                if (checkAll) {
                    selectedItems.add(cb.dataset.id);
                } else {
                    selectedItems.delete(cb.dataset.id);
                }
            });
        }
        
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
        
        // Close modal on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


"""
Review Queue System for Enterprise Sustainability Data

Implements the "AI Assists, Human Approves" pattern:
1. Documents are processed by AI
2. Placed in review queue with confidence scores
3. Humans review and approve/reject/edit
4. Approved data flows to system of record

Enterprise features:
- Confidence-based routing
- Bulk operations
- Audit trail
- Role-based access
- Notifications
"""

import json
import os
import sqlite3
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum


class ReviewStatus(str, Enum):
    """Status of a document in the review queue."""
    PENDING = "pending"           # Awaiting review
    APPROVED = "approved"         # Human approved
    REJECTED = "rejected"         # Human rejected
    NEEDS_EDIT = "needs_edit"     # Requires corrections
    AUTO_APPROVED = "auto_approved"  # High confidence auto-approve
    EXPORTED = "exported"         # Sent to system of record


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    HIGH = "high"       # >90% - Auto-approve candidate
    MEDIUM = "medium"   # 70-90% - Quick review
    LOW = "low"         # <70% - Manual review required
    UNKNOWN = "unknown" # New document type


class DocumentCategory(str, Enum):
    """Document categories for filtering."""
    ENERGY = "energy"
    TRAVEL = "travel"
    FLEET = "fleet"
    SHIPPING = "shipping"
    WASTE = "waste"
    CARBON_OFFSET = "carbon_offset"
    ESG_REPORT = "esg_report"
    OTHER = "other"


@dataclass
class ReviewItem:
    """A document in the review queue."""
    id: str
    document_type: str
    category: str
    source: str  # email, sharepoint, upload, api
    filename: str
    uploaded_by: str
    uploaded_at: str
    
    # AI Extraction Results
    confidence: float
    confidence_level: str
    extracted_data: Dict[str, Any]
    raw_text: str
    calculated_co2e_kg: Optional[float]
    
    # Review Status
    status: str = ReviewStatus.PENDING.value
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    approved_data: Optional[Dict[str, Any]] = None
    changes_made: bool = False
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    
    # Metadata
    company_id: Optional[str] = None
    location_id: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    
    # Flags
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    is_anomaly: bool = False
    anomaly_details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewItem":
        return cls(**data)


@dataclass
class AuditLogEntry:
    """Audit trail entry."""
    id: str
    timestamp: str
    user: str
    action: str  # created, viewed, approved, rejected, edited, exported
    review_item_id: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReviewQueueManager:
    """
    Manages the document review queue.
    
    Features:
    - SQLite persistence
    - Confidence-based routing
    - Bulk operations
    - Full audit trail
    - Statistics and analytics
    """
    
    def __init__(self, db_path: str = "data/review_queue.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Review items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_items (
                id TEXT PRIMARY KEY,
                document_type TEXT,
                category TEXT,
                source TEXT,
                filename TEXT,
                uploaded_by TEXT,
                uploaded_at TEXT,
                confidence REAL,
                confidence_level TEXT,
                extracted_data TEXT,
                raw_text TEXT,
                calculated_co2e_kg REAL,
                status TEXT DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at TEXT,
                approved_data TEXT,
                changes_made INTEGER DEFAULT 0,
                rejection_reason TEXT,
                notes TEXT,
                company_id TEXT,
                location_id TEXT,
                period_start TEXT,
                period_end TEXT,
                is_flagged INTEGER DEFAULT 0,
                flag_reason TEXT,
                is_anomaly INTEGER DEFAULT 0,
                anomaly_details TEXT
            )
        """)
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                user TEXT,
                action TEXT,
                review_item_id TEXT,
                details TEXT,
                ip_address TEXT,
                FOREIGN KEY (review_item_id) REFERENCES review_items(id)
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON review_items(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON review_items(confidence_level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON review_items(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_at ON review_items(uploaded_at)")
        
        conn.commit()
        conn.close()
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Determine confidence level from score."""
        if confidence >= 0.9:
            return ConfidenceLevel.HIGH.value
        elif confidence >= 0.7:
            return ConfidenceLevel.MEDIUM.value
        elif confidence > 0:
            return ConfidenceLevel.LOW.value
        return ConfidenceLevel.UNKNOWN.value
    
    def add_item(
        self,
        document_type: str,
        category: str,
        source: str,
        filename: str,
        uploaded_by: str,
        confidence: float,
        extracted_data: Dict[str, Any],
        raw_text: str,
        calculated_co2e_kg: Optional[float] = None,
        company_id: Optional[str] = None,
        auto_approve_threshold: float = 0.95
    ) -> ReviewItem:
        """
        Add a new item to the review queue.
        
        Args:
            document_type: Type of document
            category: Document category
            source: Where the document came from
            filename: Original filename
            uploaded_by: User who uploaded
            confidence: AI confidence score (0-1)
            extracted_data: AI-extracted data
            raw_text: Original document text
            calculated_co2e_kg: Calculated emissions
            company_id: Associated company
            auto_approve_threshold: Auto-approve if confidence >= this
            
        Returns:
            ReviewItem object
        """
        item_id = str(uuid.uuid4())
        confidence_level = self._get_confidence_level(confidence)
        
        # Auto-approve high confidence items
        status = ReviewStatus.PENDING.value
        if confidence >= auto_approve_threshold:
            status = ReviewStatus.AUTO_APPROVED.value
        
        # Check for anomalies
        is_anomaly = False
        anomaly_details = None
        if calculated_co2e_kg and calculated_co2e_kg > 10000:  # >10 tonnes
            is_anomaly = True
            anomaly_details = f"High emissions detected: {calculated_co2e_kg:.0f} kg CO2e"
        
        item = ReviewItem(
            id=item_id,
            document_type=document_type,
            category=category,
            source=source,
            filename=filename,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now().isoformat(),
            confidence=confidence,
            confidence_level=confidence_level,
            extracted_data=extracted_data,
            raw_text=raw_text,
            calculated_co2e_kg=calculated_co2e_kg,
            status=status,
            company_id=company_id,
            is_anomaly=is_anomaly,
            anomaly_details=anomaly_details
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO review_items (
                id, document_type, category, source, filename, uploaded_by,
                uploaded_at, confidence, confidence_level, extracted_data,
                raw_text, calculated_co2e_kg, status, company_id,
                is_anomaly, anomaly_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id, item.document_type, item.category, item.source,
            item.filename, item.uploaded_by, item.uploaded_at,
            item.confidence, item.confidence_level,
            json.dumps(item.extracted_data), item.raw_text,
            item.calculated_co2e_kg, item.status, item.company_id,
            1 if item.is_anomaly else 0, item.anomaly_details
        ))
        
        conn.commit()
        conn.close()
        
        # Log the action
        self._log_action(item_id, uploaded_by, "created", {
            "source": source,
            "confidence": confidence,
            "auto_approved": status == ReviewStatus.AUTO_APPROVED.value
        })
        
        return item
    
    def get_queue(
        self,
        status: Optional[str] = None,
        confidence_level: Optional[str] = None,
        category: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "uploaded_at",
        sort_order: str = "desc"
    ) -> List[ReviewItem]:
        """
        Get items from the review queue with filters.
        
        Args:
            status: Filter by status
            confidence_level: Filter by confidence level
            category: Filter by category
            company_id: Filter by company
            limit: Max items to return
            offset: Pagination offset
            sort_by: Field to sort by
            sort_order: asc or desc
            
        Returns:
            List of ReviewItem objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM review_items WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if confidence_level:
            query += " AND confidence_level = ?"
            params.append(confidence_level)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        
        # Validate sort_by to prevent SQL injection
        allowed_sort = ["uploaded_at", "confidence", "status", "category", "calculated_co2e_kg"]
        if sort_by not in allowed_sort:
            sort_by = "uploaded_at"
        
        query += f" ORDER BY {sort_by} {sort_order.upper()}"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            item_dict = dict(row)
            item_dict["extracted_data"] = json.loads(item_dict["extracted_data"] or "{}")
            item_dict["approved_data"] = json.loads(item_dict["approved_data"]) if item_dict["approved_data"] else None
            item_dict["changes_made"] = bool(item_dict["changes_made"])
            item_dict["is_flagged"] = bool(item_dict["is_flagged"])
            item_dict["is_anomaly"] = bool(item_dict["is_anomaly"])
            items.append(ReviewItem.from_dict(item_dict))
        
        return items
    
    def get_item(self, item_id: str) -> Optional[ReviewItem]:
        """Get a single review item by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM review_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        item_dict = dict(row)
        item_dict["extracted_data"] = json.loads(item_dict["extracted_data"] or "{}")
        item_dict["approved_data"] = json.loads(item_dict["approved_data"]) if item_dict["approved_data"] else None
        item_dict["changes_made"] = bool(item_dict["changes_made"])
        item_dict["is_flagged"] = bool(item_dict["is_flagged"])
        item_dict["is_anomaly"] = bool(item_dict["is_anomaly"])
        
        return ReviewItem.from_dict(item_dict)
    
    def approve_item(
        self,
        item_id: str,
        user: str,
        approved_data: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a review item.
        
        Args:
            item_id: Item to approve
            user: User approving
            approved_data: Modified data (if edited)
            notes: Optional notes
            
        Returns:
            True if successful
        """
        item = self.get_item(item_id)
        if not item:
            return False
        
        # Determine if changes were made
        final_data = approved_data or item.extracted_data
        changes_made = approved_data is not None and approved_data != item.extracted_data
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE review_items
            SET status = ?, reviewed_by = ?, reviewed_at = ?,
                approved_data = ?, changes_made = ?, notes = ?
            WHERE id = ?
        """, (
            ReviewStatus.APPROVED.value, user, datetime.now().isoformat(),
            json.dumps(final_data), 1 if changes_made else 0, notes, item_id
        ))
        
        conn.commit()
        conn.close()
        
        self._log_action(item_id, user, "approved", {
            "changes_made": changes_made,
            "notes": notes
        })
        
        return True
    
    def reject_item(
        self,
        item_id: str,
        user: str,
        reason: str
    ) -> bool:
        """Reject a review item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE review_items
            SET status = ?, reviewed_by = ?, reviewed_at = ?, rejection_reason = ?
            WHERE id = ?
        """, (
            ReviewStatus.REJECTED.value, user, datetime.now().isoformat(),
            reason, item_id
        ))
        
        conn.commit()
        conn.close()
        
        self._log_action(item_id, user, "rejected", {"reason": reason})
        
        return True
    
    def delete_item(
        self,
        item_id: str,
        user: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Delete a review item from the queue.
        
        Args:
            item_id: Item to delete
            user: User performing deletion
            reason: Optional reason for deletion
            
        Returns:
            True if successful, False if item not found
        """
        item = self.get_item(item_id)
        if not item:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete the item
        cursor.execute("DELETE FROM review_items WHERE id = ?", (item_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            self._log_action(item_id, user, "deleted", {
                "filename": item.filename,
                "document_type": item.document_type,
                "reason": reason
            })
        
        return deleted
    
    def bulk_delete(
        self,
        item_ids: List[str],
        user: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk delete multiple items.
        
        Args:
            item_ids: List of item IDs to delete
            user: User performing deletion
            reason: Optional reason
            
        Returns:
            Summary of results
        """
        deleted = []
        not_found = []
        
        for item_id in item_ids:
            if self.delete_item(item_id, user, reason):
                deleted.append(item_id)
            else:
                not_found.append(item_id)
        
        return {
            "deleted": len(deleted),
            "not_found": len(not_found),
            "deleted_ids": deleted,
            "not_found_ids": not_found
        }
    
    def bulk_approve(
        self,
        item_ids: List[str],
        user: str,
        min_confidence: float = 0.9
    ) -> Dict[str, Any]:
        """
        Bulk approve multiple items.
        
        Only approves items with confidence >= min_confidence.
        
        Returns:
            Summary of results
        """
        approved = []
        skipped = []
        
        for item_id in item_ids:
            item = self.get_item(item_id)
            if not item:
                skipped.append({"id": item_id, "reason": "not found"})
                continue
            
            if item.confidence < min_confidence:
                skipped.append({
                    "id": item_id,
                    "reason": f"confidence {item.confidence:.0%} < {min_confidence:.0%}"
                })
                continue
            
            if item.status != ReviewStatus.PENDING.value:
                skipped.append({"id": item_id, "reason": f"status is {item.status}"})
                continue
            
            self.approve_item(item_id, user)
            approved.append(item_id)
        
        self._log_action("bulk", user, "bulk_approved", {
            "approved_count": len(approved),
            "skipped_count": len(skipped)
        })
        
        return {
            "approved": len(approved),
            "skipped": len(skipped),
            "approved_ids": approved,
            "skipped_details": skipped
        }
    
    def flag_item(
        self,
        item_id: str,
        user: str,
        reason: str
    ) -> bool:
        """Flag an item for attention."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE review_items
            SET is_flagged = 1, flag_reason = ?
            WHERE id = ?
        """, (reason, item_id))
        
        conn.commit()
        conn.close()
        
        self._log_action(item_id, user, "flagged", {"reason": reason})
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics for dashboard."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total counts by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM review_items 
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Counts by confidence level
        cursor.execute("""
            SELECT confidence_level, COUNT(*) as count 
            FROM review_items 
            WHERE status = 'pending'
            GROUP BY confidence_level
        """)
        confidence_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Counts by category
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM review_items 
            GROUP BY category
        """)
        category_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total emissions
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'approved' THEN calculated_co2e_kg ELSE 0 END) as approved_co2e,
                SUM(CASE WHEN status = 'pending' THEN calculated_co2e_kg ELSE 0 END) as pending_co2e
            FROM review_items
        """)
        emissions = cursor.fetchone()
        
        # Recent activity (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT DATE(uploaded_at) as date, COUNT(*) as count
            FROM review_items
            WHERE uploaded_at >= ?
            GROUP BY DATE(uploaded_at)
            ORDER BY date
        """, (week_ago,))
        daily_uploads = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Auto-approve rate
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'auto_approved' THEN 1 END) as auto,
                COUNT(*) as total
            FROM review_items
        """)
        auto_stats = cursor.fetchone()
        auto_approve_rate = (auto_stats[0] / auto_stats[1] * 100) if auto_stats[1] > 0 else 0
        
        conn.close()
        
        return {
            "queue_summary": {
                "pending": status_counts.get("pending", 0),
                "approved": status_counts.get("approved", 0),
                "auto_approved": status_counts.get("auto_approved", 0),
                "rejected": status_counts.get("rejected", 0),
                "total": sum(status_counts.values())
            },
            "pending_by_confidence": confidence_counts,
            "by_category": category_counts,
            "emissions": {
                "approved_kg": emissions[0] or 0,
                "approved_tonnes": (emissions[0] or 0) / 1000,
                "pending_kg": emissions[1] or 0,
                "pending_tonnes": (emissions[1] or 0) / 1000
            },
            "activity": {
                "daily_uploads": daily_uploads,
                "auto_approve_rate": round(auto_approve_rate, 1)
            }
        }
    
    def _log_action(
        self,
        item_id: str,
        user: str,
        action: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        """Log an audit trail entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log (id, timestamp, user, action, review_item_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            datetime.now().isoformat(),
            user,
            action,
            item_id,
            json.dumps(details),
            ip_address
        ))
        
        conn.commit()
        conn.close()
    
    def get_audit_log(
        self,
        item_id: Optional[str] = None,
        user: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get audit log entries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if item_id:
            query += " AND review_item_id = ?"
            params.append(item_id)
        
        if user:
            query += " AND user = ?"
            params.append(user)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entry_dict = dict(row)
            entry_dict["details"] = json.loads(entry_dict["details"])
            entries.append(AuditLogEntry(**entry_dict))
        
        return entries


# Singleton instance
review_queue = ReviewQueueManager()


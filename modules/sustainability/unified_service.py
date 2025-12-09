"""
Unified Sustainability Service

Service layer that provides a clean interface to the unified database.
Used by all sustainability APIs.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from .unified_database import (
    UnifiedSustainabilityDB, 
    DocumentStatus, 
    EmissionCategory,
    EmissionScope,
    CATEGORY_SCOPE_MAP
)


class ConfidenceLevel(str, Enum):
    HIGH = "high"       # >= 90%
    MEDIUM = "medium"   # 70-90%
    LOW = "low"         # < 70%


@dataclass
class ReviewItem:
    """A document in the review queue."""
    id: str
    company_id: str
    document_type: str
    category: str
    filename: str
    source: str
    raw_text: str
    extracted_data: Dict[str, Any]
    calculated_co2e_kg: float
    confidence: float
    confidence_level: str
    status: str
    uploaded_by: str
    uploaded_at: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    notes: Optional[str] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    emission_scope: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Parse extracted_data if it's a string
        if isinstance(d.get('extracted_data'), str):
            try:
                d['extracted_data'] = json.loads(d['extracted_data'])
            except:
                pass
        return d


class UnifiedSustainabilityService:
    """
    Unified service for all sustainability operations.
    
    Replaces:
    - review_queue.ReviewQueueManager
    - database.SustainabilityDatabase
    """
    
    def __init__(self, db_path: str = "data/sustainability_unified.db"):
        self.db = UnifiedSustainabilityDB(db_path)
    
    # ==================== DOCUMENT SUBMISSION ====================
    
    def submit_document(
        self,
        company_id: str,
        document_type: str,
        category: str,
        filename: str,
        raw_text: str,
        extracted_data: Dict[str, Any],
        calculated_co2e_kg: float,
        confidence: float,
        uploaded_by: str = "system",
        source: str = "upload",
        location_id: str = None,
        is_personal: bool = False,
        auto_approve_threshold: float = 0.95
    ) -> str:
        """
        Submit a document for review.
        
        Returns: document_id
        """
        return self.db.add_emission_document(
            company_id=company_id,
            document_type=document_type,
            category=category,
            filename=filename,
            raw_text=raw_text,
            extracted_data=extracted_data,
            calculated_co2e_kg=calculated_co2e_kg,
            confidence=confidence,
            uploaded_by=uploaded_by,
            location_id=location_id,
            source=source,
            is_personal=is_personal,
            auto_approve_threshold=auto_approve_threshold
        )
    
    # ==================== REVIEW QUEUE ====================
    
    def get_queue(
        self,
        status: str = None,
        confidence_level: str = None,
        category: str = None,
        company_id: str = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "uploaded_at",
        sort_order: str = "desc"
    ) -> List[ReviewItem]:
        """Get items from the review queue."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM emission_documents WHERE 1=1"
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
        
        # Sort
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        query += f" ORDER BY {sort_by} {order}"
        
        # Pagination
        query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        
        items = []
        for row in cursor.fetchall():
            data = dict(zip(columns, row))
            items.append(ReviewItem(
                id=data['id'],
                company_id=data['company_id'] or 'unknown',
                document_type=data['document_type'] or 'unknown',
                category=data['category'] or 'other',
                filename=data['filename'] or 'unnamed',
                source=data['source'] or 'upload',
                raw_text=data.get('raw_text', ''),
                extracted_data=json.loads(data.get('extracted_data', '{}')) if data.get('extracted_data') else {},
                calculated_co2e_kg=data.get('calculated_co2e_kg', 0) or 0,
                confidence=data.get('confidence', 0) or 0,
                confidence_level=data.get('confidence_level', 'low'),
                status=data['status'] or 'pending',
                uploaded_by=data.get('uploaded_by', 'unknown'),
                uploaded_at=data.get('uploaded_at', ''),
                reviewed_by=data.get('reviewed_by'),
                reviewed_at=data.get('reviewed_at'),
                notes=data.get('notes'),
                is_flagged=bool(data.get('is_flagged', 0)),
                flag_reason=data.get('flag_reason'),
                emission_scope=data.get('emission_scope')
            ))
        
        conn.close()
        return items
    
    def get_item(self, item_id: str) -> Optional[ReviewItem]:
        """Get a specific review item."""
        items = self.get_queue(limit=1)
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM emission_documents WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))
        conn.close()
        
        return ReviewItem(
            id=data['id'],
            company_id=data['company_id'] or 'unknown',
            document_type=data['document_type'] or 'unknown',
            category=data['category'] or 'other',
            filename=data['filename'] or 'unnamed',
            source=data['source'] or 'upload',
            raw_text=data.get('raw_text', ''),
            extracted_data=json.loads(data.get('extracted_data', '{}')) if data.get('extracted_data') else {},
            calculated_co2e_kg=data.get('calculated_co2e_kg', 0) or 0,
            confidence=data.get('confidence', 0) or 0,
            confidence_level=data.get('confidence_level', 'low'),
            status=data['status'] or 'pending',
            uploaded_by=data.get('uploaded_by', 'unknown'),
            uploaded_at=data.get('uploaded_at', ''),
            reviewed_by=data.get('reviewed_by'),
            reviewed_at=data.get('reviewed_at'),
            notes=data.get('notes'),
            is_flagged=bool(data.get('is_flagged', 0)),
            flag_reason=data.get('flag_reason'),
            emission_scope=data.get('emission_scope')
        )
    
    def approve_item(
        self, 
        item_id: str, 
        user_email: str,
        approved_data: Dict[str, Any] = None,
        notes: str = None
    ) -> bool:
        """Approve a review item and create emission entry."""
        return self.db.approve_document(item_id, user_email, approved_data, notes)
    
    def reject_item(
        self,
        item_id: str,
        user_email: str,
        reason: str
    ) -> bool:
        """Reject a review item."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE emission_documents
            SET status = 'rejected', reviewed_by = ?, reviewed_at = ?, rejection_reason = ?
            WHERE id = ?
        """, (user_email, datetime.now().isoformat(), reason, item_id))
        
        conn.commit()
        conn.close()
        
        self.db.log_action("document_rejected", "emission_document", item_id, user_email, {"reason": reason})
        return True
    
    def delete_item(self, item_id: str, user_email: str = None) -> bool:
        """Delete a review item."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM emission_documents WHERE id = ?", (item_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if deleted:
            self.db.log_action("document_deleted", "emission_document", item_id, user_email)
        
        return deleted
    
    def bulk_delete(self, item_ids: List[str], user_email: str = None) -> int:
        """Delete multiple items."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in item_ids])
        cursor.execute(f"DELETE FROM emission_documents WHERE id IN ({placeholders})", item_ids)
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        self.db.log_action("bulk_delete", "emission_document", ",".join(item_ids[:5]), user_email, {"count": deleted})
        return deleted
    
    def flag_item(self, item_id: str, reason: str, user_email: str = None) -> bool:
        """Flag an item for attention."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE emission_documents SET is_flagged = 1, flag_reason = ? WHERE id = ?
        """, (reason, item_id))
        
        conn.commit()
        conn.close()
        
        self.db.log_action("document_flagged", "emission_document", item_id, user_email, {"reason": reason})
        return True
    
    # ==================== STATISTICS ====================
    
    def get_stats(self, company_id: str = None) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Document counts by status
        if company_id:
            cursor.execute("""
                SELECT status, COUNT(*) FROM emission_documents WHERE company_id = ? GROUP BY status
            """, (company_id,))
        else:
            cursor.execute("SELECT status, COUNT(*) FROM emission_documents GROUP BY status")
        
        status_counts = dict(cursor.fetchall())
        stats['documents'] = status_counts
        stats['total_documents'] = sum(status_counts.values())
        stats['pending_count'] = status_counts.get('pending', 0)
        stats['approved_count'] = status_counts.get('approved', 0) + status_counts.get('auto_approved', 0)
        stats['rejected_count'] = status_counts.get('rejected', 0)
        
        # Emissions by scope
        if company_id:
            cursor.execute("""
                SELECT emission_scope, SUM(co2e_kg) FROM emission_entries WHERE company_id = ? GROUP BY emission_scope
            """, (company_id,))
        else:
            cursor.execute("SELECT emission_scope, SUM(co2e_kg) FROM emission_entries GROUP BY emission_scope")
        
        scope_totals = dict(cursor.fetchall())
        stats['emissions_by_scope'] = {
            'scope_1_kg': scope_totals.get('scope_1', 0) or 0,
            'scope_2_kg': scope_totals.get('scope_2', 0) or 0,
            'scope_3_kg': scope_totals.get('scope_3', 0) or 0,
        }
        stats['total_emissions_kg'] = sum(stats['emissions_by_scope'].values())
        stats['total_emissions_tonnes'] = stats['total_emissions_kg'] / 1000
        
        # Emissions by category
        if company_id:
            cursor.execute("""
                SELECT category, SUM(co2e_kg) FROM emission_entries WHERE company_id = ? GROUP BY category
            """, (company_id,))
        else:
            cursor.execute("SELECT category, SUM(co2e_kg) FROM emission_entries GROUP BY category")
        
        stats['emissions_by_category'] = dict(cursor.fetchall())
        
        # Confidence distribution
        if company_id:
            cursor.execute("""
                SELECT confidence_level, COUNT(*) FROM emission_documents WHERE company_id = ? GROUP BY confidence_level
            """, (company_id,))
        else:
            cursor.execute("SELECT confidence_level, COUNT(*) FROM emission_documents GROUP BY confidence_level")
        
        stats['confidence_distribution'] = dict(cursor.fetchall())
        
        conn.close()
        return stats
    
    # ==================== COMPANIES ====================
    
    def get_companies(self) -> List[Dict[str, Any]]:
        """Get all companies."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM companies ORDER BY name")
        companies = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return companies
    
    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific company."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def create_company(self, data: Dict[str, Any]) -> str:
        """Create a new company."""
        import sqlite3
        
        company_id = data.get('id') or str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO companies (id, name, industry, sub_industry, employees, revenue_usd, headquarters, website, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('name', 'Unnamed Company'),
            data.get('industry'),
            data.get('sub_industry'),
            data.get('employees'),
            data.get('revenue_usd'),
            data.get('headquarters'),
            data.get('website'),
            data.get('description')
        ))
        
        conn.commit()
        conn.close()
        
        self.db.log_action("company_created", "company", company_id, details=data)
        return company_id
    
    # ==================== CARBON FOOTPRINTS ====================
    
    def get_carbon_footprint(self, company_id: str, year: int = None) -> Dict[str, Any]:
        """Get carbon footprint for a company."""
        return self.db.get_carbon_footprint(company_id, year)
    
    def get_emissions_history(self, company_id: str, years: int = 5) -> List[Dict[str, Any]]:
        """Get emissions history for multiple years."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM carbon_footprints 
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT ?
        """, (company_id, years))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # ==================== ESG SCORES ====================
    
    def get_esg_score(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get latest ESG score for a company."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM esg_scores 
            WHERE company_id = ?
            ORDER BY assessment_date DESC
            LIMIT 1
        """, (company_id,))
        
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    # ==================== KNOWLEDGE BASE ====================
    
    def add_knowledge_document(
        self,
        title: str,
        doc_type: str,
        content: str,
        category: str = None,
        source: str = None,
        company_id: str = None
    ) -> str:
        """Add a document to the knowledge base."""
        import sqlite3
        
        doc_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO knowledge_documents (id, company_id, title, doc_type, category, source, content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, company_id, title, doc_type, category, source, content))
        
        conn.commit()
        conn.close()
        
        self.db.log_action("knowledge_added", "knowledge_document", doc_id, details={"title": title})
        return doc_id
    
    def get_knowledge_documents(self, category: str = None, company_id: str = None) -> List[Dict[str, Any]]:
        """Get knowledge base documents."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge_documents WHERE is_active = 1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if company_id:
            query += " AND (company_id = ? OR company_id IS NULL)"
            params.append(company_id)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    # ==================== AUDIT LOG ====================
    
    def get_audit_log(
        self,
        entity_type: str = None,
        entity_id: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    # ==================== REDUCTION PLANS ====================
    
    def get_reduction_plans(self, company_id: str) -> List[Dict[str, Any]]:
        """Get reduction plans for a company."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reduction_plans WHERE company_id = ? ORDER BY created_at DESC
        """, (company_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # ==================== REPORTS ====================
    
    def create_report(
        self,
        company_id: str,
        report_type: str,
        title: str,
        year: int,
        content: Dict[str, Any]
    ) -> str:
        """Create a sustainability report."""
        import sqlite3
        
        report_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reports (id, company_id, report_type, title, year, content_json, status, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'generated', ?)
        """, (
            report_id,
            company_id,
            report_type,
            title,
            year,
            json.dumps(content),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        self.db.log_action("report_created", "report", report_id, details={"type": report_type, "year": year})
        return report_id
    
    def get_reports(self, company_id: str) -> List[Dict[str, Any]]:
        """Get reports for a company."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reports WHERE company_id = ? ORDER BY year DESC, generated_at DESC
        """, (company_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


# Singleton instance
unified_service = UnifiedSustainabilityService()


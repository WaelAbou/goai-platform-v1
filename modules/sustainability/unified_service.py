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
        
        # Queue summary (for HTML dashboard compatibility)
        stats['queue_summary'] = {
            'pending': status_counts.get('pending', 0),
            'approved': status_counts.get('approved', 0),
            'auto_approved': status_counts.get('auto_approved', 0),
            'rejected': status_counts.get('rejected', 0),
            'total': sum(status_counts.values())
        }
        
        # Emissions totals from documents (approved only)
        if company_id:
            cursor.execute("""
                SELECT SUM(calculated_co2e_kg) FROM emission_documents 
                WHERE company_id = ? AND status IN ('approved', 'auto_approved')
            """, (company_id,))
        else:
            cursor.execute("""
                SELECT SUM(calculated_co2e_kg) FROM emission_documents 
                WHERE status IN ('approved', 'auto_approved')
            """)
        
        approved_co2e = cursor.fetchone()[0] or 0
        
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
        
        # Emissions summary (for HTML dashboard compatibility)
        stats['emissions'] = {
            'approved_kg': approved_co2e,
            'approved_tonnes': round(approved_co2e / 1000, 2),
            'by_scope': stats['emissions_by_scope']
        }
        
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
        
        # Activity metrics (for HTML dashboard compatibility)
        auto_approved = status_counts.get('auto_approved', 0)
        total_approved = stats['approved_count']
        auto_rate = round((auto_approved / total_approved * 100), 1) if total_approved > 0 else 0
        
        stats['activity'] = {
            'auto_approve_rate': auto_rate,
            'total_reviewed': stats['approved_count'] + stats['rejected_count']
        }
        
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
    
    # ==================== ANALYTICS ====================
    
    def get_analytics(self, time_range: str = "6months", company_id: str = None) -> Dict[str, Any]:
        """
        Get comprehensive analytics for dashboards.
        
        Returns:
        - overview: Total documents, approval rate, avg review time, growth
        - monthly_trends: Submissions by month
        - category_distribution: Breakdown by document type
        - top_contributors: Top submitters
        - emissions_trends: CO2e over time
        """
        import sqlite3
        from datetime import timedelta
        
        # Parse time range
        months = {"1month": 1, "3months": 3, "6months": 6, "1year": 12}.get(time_range, 6)
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Calculate date cutoff
        cutoff_date = (datetime.now() - timedelta(days=months * 30)).isoformat()
        
        # Base filter
        base_filter = "uploaded_at >= ?"
        params = [cutoff_date]
        if company_id:
            base_filter += " AND company_id = ?"
            params.append(company_id)
        
        # 1. Overview Statistics
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('approved', 'auto_approved') THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                AVG(confidence) as avg_confidence,
                SUM(calculated_co2e_kg) as total_co2e
            FROM emission_documents WHERE {base_filter}
        """, params)
        
        row = cursor.fetchone()
        total, approved, rejected, pending, avg_confidence, total_co2e = row
        
        overview = {
            "total_documents": total or 0,
            "approved": approved or 0,
            "rejected": rejected or 0,
            "pending": pending or 0,
            "approval_rate": round((approved / total * 100), 1) if total else 0,
            "avg_confidence": round((avg_confidence or 0) * 100, 1),
            "total_co2e_kg": total_co2e or 0,
            "total_co2e_tonnes": round((total_co2e or 0) / 1000, 2),
        }
        
        # Calculate growth (compare current month to previous)
        cursor.execute(f"""
            SELECT COUNT(*) FROM emission_documents 
            WHERE strftime('%Y-%m', uploaded_at) = strftime('%Y-%m', 'now')
            {' AND company_id = ?' if company_id else ''}
        """, [company_id] if company_id else [])
        current_month = cursor.fetchone()[0] or 0
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM emission_documents 
            WHERE strftime('%Y-%m', uploaded_at) = strftime('%Y-%m', 'now', '-1 month')
            {' AND company_id = ?' if company_id else ''}
        """, [company_id] if company_id else [])
        prev_month = cursor.fetchone()[0] or 0
        
        if prev_month > 0:
            overview["monthly_growth"] = round((current_month - prev_month) / prev_month * 100, 1)
        else:
            overview["monthly_growth"] = 100 if current_month > 0 else 0
        
        conn.close()
        
        return {
            "overview": overview,
            "monthly_trends": self.get_monthly_trends(months, company_id),
            "category_distribution": self.get_category_distribution(company_id),
            "top_contributors": self.get_top_contributors(10, company_id),
            "emissions_by_scope": self._get_emissions_by_scope(company_id),
            "time_range": time_range
        }
    
    def get_monthly_trends(self, months: int = 6, company_id: str = None) -> List[Dict[str, Any]]:
        """Get monthly submission trends."""
        import sqlite3
        from datetime import timedelta
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get data grouped by month
        company_filter = "AND company_id = ?" if company_id else ""
        params = [company_id] if company_id else []
        
        cursor.execute(f"""
            SELECT 
                strftime('%Y-%m', uploaded_at) as month,
                COUNT(*) as uploads,
                SUM(CASE WHEN status IN ('approved', 'auto_approved') THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(calculated_co2e_kg) as co2e_kg
            FROM emission_documents
            WHERE uploaded_at >= date('now', '-{months} months')
            {company_filter}
            GROUP BY strftime('%Y-%m', uploaded_at)
            ORDER BY month ASC
        """, params)
        
        results = []
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        for row in cursor.fetchall():
            year_month, uploads, approved, rejected, co2e = row
            month_num = int(year_month.split('-')[1])
            results.append({
                "month": month_names[month_num - 1],
                "year_month": year_month,
                "uploads": uploads or 0,
                "approved": approved or 0,
                "rejected": rejected or 0,
                "co2e_kg": co2e or 0
            })
        
        conn.close()
        
        # Ensure we have all months (fill gaps with zeros)
        if len(results) < months:
            all_months = []
            for i in range(months - 1, -1, -1):
                d = datetime.now() - timedelta(days=i * 30)
                ym = d.strftime('%Y-%m')
                existing = next((r for r in results if r['year_month'] == ym), None)
                if existing:
                    all_months.append(existing)
                else:
                    all_months.append({
                        "month": month_names[d.month - 1],
                        "year_month": ym,
                        "uploads": 0,
                        "approved": 0,
                        "rejected": 0,
                        "co2e_kg": 0
                    })
            results = all_months
        
        return results
    
    def get_category_distribution(self, company_id: str = None) -> List[Dict[str, Any]]:
        """Get document category distribution."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        company_filter = "WHERE company_id = ?" if company_id else ""
        params = [company_id] if company_id else []
        
        # Define colors for categories
        category_colors = {
            "flight_receipt": {"name": "Air Travel", "color": "hsl(199, 89%, 48%)"},
            "utility_bill": {"name": "Utilities", "color": "hsl(38, 92%, 50%)"},
            "utility_bill_electric": {"name": "Electricity", "color": "hsl(45, 93%, 47%)"},
            "utility_bill_gas": {"name": "Natural Gas", "color": "hsl(24, 94%, 50%)"},
            "fuel_receipt": {"name": "Fleet Fuel", "color": "hsl(350, 84%, 60%)"},
            "shipping_invoice": {"name": "Shipping", "color": "hsl(160, 84%, 39%)"},
            "travel": {"name": "Travel", "color": "hsl(199, 89%, 48%)"},
            "energy": {"name": "Energy", "color": "hsl(45, 93%, 47%)"},
            "esg_report": {"name": "ESG Report", "color": "hsl(280, 84%, 60%)"},
            "other": {"name": "Other", "color": "hsl(215, 20%, 55%)"},
        }
        
        cursor.execute(f"""
            SELECT document_type, COUNT(*) as count, SUM(calculated_co2e_kg) as co2e
            FROM emission_documents
            {company_filter}
            GROUP BY document_type
            ORDER BY count DESC
        """, params)
        
        results = []
        for row in cursor.fetchall():
            doc_type, count, co2e = row
            cat_info = category_colors.get(doc_type, {"name": doc_type or "Unknown", "color": "hsl(215, 20%, 55%)"})
            results.append({
                "name": cat_info["name"],
                "document_type": doc_type,
                "value": count,
                "co2e_kg": co2e or 0,
                "color": cat_info["color"]
            })
        
        conn.close()
        return results
    
    def get_top_contributors(self, limit: int = 10, company_id: str = None) -> List[Dict[str, Any]]:
        """Get top document contributors."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        company_filter = "WHERE company_id = ?" if company_id else ""
        params = [company_id] if company_id else []
        
        cursor.execute(f"""
            SELECT 
                uploaded_by,
                COUNT(*) as submissions,
                SUM(CASE WHEN status IN ('approved', 'auto_approved') THEN 1 ELSE 0 END) as approved,
                SUM(calculated_co2e_kg) as co2e_contributed
            FROM emission_documents
            {company_filter}
            GROUP BY uploaded_by
            ORDER BY submissions DESC
            LIMIT ?
        """, params + [limit])
        
        results = []
        for row in cursor.fetchall():
            user, submissions, approved, co2e = row
            results.append({
                "name": user or "Unknown",
                "submissions": submissions,
                "approved": approved or 0,
                "approval_rate": round((approved / submissions * 100), 1) if submissions else 0,
                "co2e_contributed": co2e or 0
            })
        
        conn.close()
        return results
    
    def get_emissions_analytics(self, time_range: str = "6months", company_id: str = None) -> Dict[str, Any]:
        """Get emissions-focused analytics."""
        import sqlite3
        
        months = {"1month": 1, "3months": 3, "6months": 6, "1year": 12}.get(time_range, 6)
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        company_filter = "AND company_id = ?" if company_id else ""
        params = [company_id] if company_id else []
        
        # Emissions by month
        cursor.execute(f"""
            SELECT 
                strftime('%Y-%m', uploaded_at) as month,
                SUM(calculated_co2e_kg) as co2e_kg,
                COUNT(*) as documents
            FROM emission_documents
            WHERE status IN ('approved', 'auto_approved')
            AND uploaded_at >= date('now', '-{months} months')
            {company_filter}
            GROUP BY strftime('%Y-%m', uploaded_at)
            ORDER BY month ASC
        """, params)
        
        monthly_emissions = []
        for row in cursor.fetchall():
            month, co2e, docs = row
            monthly_emissions.append({
                "month": month,
                "co2e_kg": co2e or 0,
                "co2e_tonnes": round((co2e or 0) / 1000, 2),
                "documents": docs
            })
        
        # By scope
        scope_data = self._get_emissions_by_scope(company_id)
        
        # By category
        cursor.execute(f"""
            SELECT 
                category,
                SUM(calculated_co2e_kg) as co2e_kg
            FROM emission_documents
            WHERE status IN ('approved', 'auto_approved')
            {company_filter}
            GROUP BY category
            ORDER BY co2e_kg DESC
        """, params)
        
        by_category = []
        for row in cursor.fetchall():
            cat, co2e = row
            by_category.append({
                "category": cat or "other",
                "co2e_kg": co2e or 0,
                "co2e_tonnes": round((co2e or 0) / 1000, 2)
            })
        
        conn.close()
        
        return {
            "monthly_emissions": monthly_emissions,
            "by_scope": scope_data,
            "by_category": by_category,
            "time_range": time_range
        }
    
    def _get_emissions_by_scope(self, company_id: str = None) -> Dict[str, Any]:
        """Get emissions breakdown by scope."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        company_filter = "WHERE company_id = ?" if company_id else ""
        params = [company_id] if company_id else []
        
        cursor.execute(f"""
            SELECT emission_scope, SUM(co2e_kg) 
            FROM emission_entries 
            {company_filter}
            GROUP BY emission_scope
        """, params)
        
        scope_totals = dict(cursor.fetchall())
        conn.close()
        
        return {
            "scope_1": {
                "kg": scope_totals.get('scope_1', 0) or 0,
                "tonnes": round((scope_totals.get('scope_1', 0) or 0) / 1000, 2),
                "description": "Direct emissions (fuel, fleet)"
            },
            "scope_2": {
                "kg": scope_totals.get('scope_2', 0) or 0,
                "tonnes": round((scope_totals.get('scope_2', 0) or 0) / 1000, 2),
                "description": "Indirect emissions (electricity, heating)"
            },
            "scope_3": {
                "kg": scope_totals.get('scope_3', 0) or 0,
                "tonnes": round((scope_totals.get('scope_3', 0) or 0) / 1000, 2),
                "description": "Value chain emissions (travel, shipping)"
            },
            "total": {
                "kg": sum(v or 0 for v in scope_totals.values()),
                "tonnes": round(sum(v or 0 for v in scope_totals.values()) / 1000, 2)
            }
        }


# Singleton instance
unified_service = UnifiedSustainabilityService()


"""
Unified Sustainability Database

Single source of truth for all sustainability data:
- Companies & Locations
- Emission Sources (documents, invoices, receipts)
- Carbon Footprints (aggregated)
- ESG Scores & Reports
- Knowledge Base
- Reduction Plans & Initiatives
- Audit Trail

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                   UNIFIED SUSTAINABILITY DB                      │
├─────────────────────────────────────────────────────────────────┤
│  CORE ENTITIES                                                   │
│  ├── companies          - Company profiles                       │
│  ├── locations          - Office/facility locations              │
│  └── users              - System users                           │
├─────────────────────────────────────────────────────────────────┤
│  EMISSION SOURCES (Raw Data)                                     │
│  ├── emission_documents - All uploaded documents                 │
│  ├── emission_entries   - Individual emission records            │
│  └── emission_factors   - CO2e conversion factors                │
├─────────────────────────────────────────────────────────────────┤
│  AGGREGATED DATA                                                 │
│  ├── carbon_footprints  - Annual summaries by scope              │
│  ├── monthly_emissions  - Monthly breakdowns                     │
│  └── category_emissions - By category (travel, energy, etc.)     │
├─────────────────────────────────────────────────────────────────┤
│  ESG & REPORTING                                                 │
│  ├── esg_scores         - ESG ratings                            │
│  ├── reports            - Generated reports                      │
│  └── benchmarks         - Industry comparisons                   │
├─────────────────────────────────────────────────────────────────┤
│  KNOWLEDGE BASE                                                  │
│  ├── knowledge_documents- Reference documents                    │
│  ├── knowledge_chunks   - Indexed chunks for RAG                 │
│  └── knowledge_embeddings- Vector embeddings                     │
├─────────────────────────────────────────────────────────────────┤
│  PLANNING & TRACKING                                             │
│  ├── reduction_plans    - Net zero plans                         │
│  ├── initiatives        - Specific actions                       │
│  └── milestones         - Progress tracking                      │
├─────────────────────────────────────────────────────────────────┤
│  AUDIT & COMPLIANCE                                              │
│  ├── audit_log          - All actions                            │
│  ├── approvals          - Review history                         │
│  └── compliance_checks  - Regulatory compliance                  │
└─────────────────────────────────────────────────────────────────┘
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class EmissionScope(str, Enum):
    SCOPE_1 = "scope_1"  # Direct emissions
    SCOPE_2 = "scope_2"  # Indirect from energy
    SCOPE_3 = "scope_3"  # Other indirect


class DocumentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class EmissionCategory(str, Enum):
    ENERGY = "energy"           # Scope 2
    TRAVEL = "travel"           # Scope 3
    FLEET = "fleet"             # Scope 1
    SHIPPING = "shipping"       # Scope 3
    COMMUTING = "commuting"     # Scope 3
    HEATING = "heating"         # Scope 1
    WASTE = "waste"             # Scope 3
    PURCHASED_GOODS = "purchased_goods"  # Scope 3
    OTHER = "other"


# Category to Scope mapping
CATEGORY_SCOPE_MAP = {
    EmissionCategory.ENERGY: EmissionScope.SCOPE_2,
    EmissionCategory.TRAVEL: EmissionScope.SCOPE_3,
    EmissionCategory.FLEET: EmissionScope.SCOPE_1,
    EmissionCategory.SHIPPING: EmissionScope.SCOPE_3,
    EmissionCategory.COMMUTING: EmissionScope.SCOPE_3,
    EmissionCategory.HEATING: EmissionScope.SCOPE_1,
    EmissionCategory.WASTE: EmissionScope.SCOPE_3,
    EmissionCategory.PURCHASED_GOODS: EmissionScope.SCOPE_3,
    EmissionCategory.OTHER: EmissionScope.SCOPE_3,
}


class UnifiedSustainabilityDB:
    """
    Single unified database for all sustainability data.
    """
    
    def __init__(self, db_path: str = "data/sustainability_unified.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize all tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ==================== CORE ENTITIES ====================
        
        # Companies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                industry TEXT,
                sub_industry TEXT,
                employees INTEGER,
                revenue_usd REAL,
                headquarters TEXT,
                founded_year INTEGER,
                website TEXT,
                description TEXT,
                logo_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Locations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'office',
                address TEXT,
                city TEXT,
                state TEXT,
                country TEXT,
                postal_code TEXT,
                latitude REAL,
                longitude REAL,
                square_meters REAL,
                employee_count INTEGER,
                is_headquarters INTEGER DEFAULT 0,
                energy_provider TEXT,
                renewable_percent REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                company_id TEXT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'user',
                department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # ==================== EMISSION SOURCES ====================
        
        # Emission Documents (all uploaded docs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emission_documents (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                location_id TEXT,
                
                -- Document Info
                document_type TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT DEFAULT 'upload',
                filename TEXT,
                file_path TEXT,
                file_size INTEGER,
                mime_type TEXT,
                
                -- Processing Info
                raw_text TEXT,
                extracted_data TEXT,
                confidence REAL,
                confidence_level TEXT,
                
                -- Emission Data
                calculated_co2e_kg REAL,
                emission_scope TEXT,
                period_start DATE,
                period_end DATE,
                
                -- Workflow
                status TEXT DEFAULT 'pending',
                uploaded_by TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP,
                approved_data TEXT,
                rejection_reason TEXT,
                notes TEXT,
                
                -- Flags
                is_flagged INTEGER DEFAULT 0,
                flag_reason TEXT,
                is_anomaly INTEGER DEFAULT 0,
                anomaly_details TEXT,
                is_personal INTEGER DEFAULT 0,
                
                FOREIGN KEY (company_id) REFERENCES companies(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_company ON emission_documents(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_status ON emission_documents(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_category ON emission_documents(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_period ON emission_documents(period_start, period_end)")
        
        # Individual Emission Entries (line items from documents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emission_entries (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                company_id TEXT NOT NULL,
                location_id TEXT,
                
                -- Emission Details
                category TEXT NOT NULL,
                subcategory TEXT,
                emission_scope TEXT NOT NULL,
                description TEXT,
                
                -- Quantities
                quantity REAL,
                unit TEXT,
                co2e_kg REAL NOT NULL,
                
                -- Time
                entry_date DATE,
                period_start DATE,
                period_end DATE,
                
                -- Source
                data_source TEXT,
                emission_factor_id TEXT,
                calculation_method TEXT,
                
                -- Metadata
                is_estimated INTEGER DEFAULT 0,
                confidence REAL DEFAULT 1.0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (document_id) REFERENCES emission_documents(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_company ON emission_entries(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_scope ON emission_entries(emission_scope)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_date ON emission_entries(entry_date)")
        
        # Emission Factors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emission_factors (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                subcategory TEXT,
                activity_type TEXT NOT NULL,
                unit TEXT NOT NULL,
                co2e_per_unit REAL NOT NULL,
                source TEXT,
                region TEXT DEFAULT 'global',
                valid_from DATE,
                valid_to DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ==================== AGGREGATED DATA ====================
        
        # Carbon Footprints (annual)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carbon_footprints (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                year INTEGER NOT NULL,
                
                -- Emissions by Scope (kg)
                scope_1_kg REAL DEFAULT 0,
                scope_2_kg REAL DEFAULT 0,
                scope_3_kg REAL DEFAULT 0,
                total_kg REAL DEFAULT 0,
                
                -- Breakdown by Category
                breakdown_json TEXT,
                
                -- Methodology
                methodology TEXT DEFAULT 'GHG Protocol',
                verification_status TEXT DEFAULT 'self-reported',
                verified_by TEXT,
                verification_date DATE,
                
                -- Comparison
                previous_year_kg REAL,
                change_percent REAL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, year)
            )
        """)
        
        # Monthly Emissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_emissions (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                
                scope_1_kg REAL DEFAULT 0,
                scope_2_kg REAL DEFAULT 0,
                scope_3_kg REAL DEFAULT 0,
                total_kg REAL DEFAULT 0,
                
                breakdown_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, year, month)
            )
        """)
        
        # ==================== ESG & REPORTING ====================
        
        # ESG Scores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS esg_scores (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                assessment_date DATE NOT NULL,
                
                -- Scores
                overall_score REAL,
                environmental_score REAL,
                social_score REAL,
                governance_score REAL,
                rating TEXT,
                
                -- Detailed Metrics
                environmental_metrics TEXT,
                social_metrics TEXT,
                governance_metrics TEXT,
                
                -- Analysis
                strengths TEXT,
                weaknesses TEXT,
                recommendations TEXT,
                industry_percentile REAL,
                
                -- Source
                assessor TEXT,
                methodology TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                
                -- Report Info
                report_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                year INTEGER,
                period_start DATE,
                period_end DATE,
                
                -- Content
                content_json TEXT,
                file_path TEXT,
                format TEXT DEFAULT 'pdf',
                
                -- Status
                status TEXT DEFAULT 'draft',
                generated_at TIMESTAMP,
                published_at TIMESTAMP,
                generated_by TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Industry Benchmarks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmarks (
                id TEXT PRIMARY KEY,
                industry TEXT NOT NULL,
                sub_industry TEXT,
                year INTEGER NOT NULL,
                
                -- Metrics
                avg_co2e_per_employee REAL,
                avg_co2e_per_revenue REAL,
                avg_esg_score REAL,
                top_quartile_threshold REAL,
                
                -- Source
                source TEXT,
                sample_size INTEGER,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(industry, year)
            )
        """)
        
        # ==================== KNOWLEDGE BASE ====================
        
        # Knowledge Documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id TEXT PRIMARY KEY,
                company_id TEXT,
                
                -- Document Info
                title TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                category TEXT,
                source TEXT,
                source_url TEXT,
                
                -- Content
                content TEXT,
                summary TEXT,
                
                -- Metadata
                author TEXT,
                published_date DATE,
                version TEXT,
                language TEXT DEFAULT 'en',
                
                -- Status
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Knowledge Chunks (for RAG)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                
                -- Chunk Info
                chunk_index INTEGER,
                content TEXT NOT NULL,
                token_count INTEGER,
                
                -- Embedding
                embedding BLOB,
                embedding_model TEXT,
                
                -- Metadata
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON knowledge_chunks(document_id)")
        
        # ==================== PLANNING & TRACKING ====================
        
        # Reduction Plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reduction_plans (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                
                -- Plan Info
                name TEXT NOT NULL,
                description TEXT,
                plan_type TEXT DEFAULT 'net_zero',
                
                -- Targets
                base_year INTEGER,
                target_year INTEGER,
                base_emissions_kg REAL,
                target_emissions_kg REAL,
                target_reduction_percent REAL,
                
                -- Strategy
                strategy TEXT,
                methodology TEXT,
                is_sbti_aligned INTEGER DEFAULT 0,
                
                -- Status
                status TEXT DEFAULT 'active',
                progress_percent REAL DEFAULT 0,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Initiatives
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS initiatives (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                company_id TEXT NOT NULL,
                
                -- Initiative Info
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                scope_impact TEXT,
                
                -- Targets
                target_reduction_kg REAL,
                actual_reduction_kg REAL,
                investment_usd REAL,
                roi_percent REAL,
                
                -- Timeline
                start_date DATE,
                end_date DATE,
                status TEXT DEFAULT 'planned',
                
                -- Responsible
                owner TEXT,
                department TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (plan_id) REFERENCES reduction_plans(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Milestones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                
                -- Milestone Info
                name TEXT NOT NULL,
                description TEXT,
                target_date DATE,
                target_value REAL,
                actual_value REAL,
                
                -- Status
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES reduction_plans(id)
            )
        """)
        
        # ==================== AUDIT & COMPLIANCE ====================
        
        # Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Actor
                user_id TEXT,
                user_email TEXT,
                ip_address TEXT,
                
                -- Action
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                
                -- Details
                old_value TEXT,
                new_value TEXT,
                details TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)")
        
        # Compliance Checks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_checks (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                
                -- Framework
                framework TEXT NOT NULL,
                requirement TEXT,
                
                -- Status
                status TEXT DEFAULT 'pending',
                checked_at TIMESTAMP,
                checked_by TEXT,
                
                -- Evidence
                evidence TEXT,
                gaps TEXT,
                recommendations TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Unified Sustainability Database initialized: {self.db_path}")
    
    # ==================== HELPER METHODS ====================
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
    
    def log_action(self, action: str, entity_type: str, entity_id: str, 
                   user_email: str = None, details: dict = None):
        """Log an action to the audit trail."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        import uuid
        cursor.execute("""
            INSERT INTO audit_log (id, user_email, action, entity_type, entity_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            user_email,
            action,
            entity_type,
            entity_id,
            json.dumps(details) if details else None
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== DOCUMENT METHODS ====================
    
    def add_emission_document(
        self,
        company_id: str,
        document_type: str,
        category: str,
        filename: str,
        raw_text: str,
        extracted_data: dict,
        calculated_co2e_kg: float,
        confidence: float,
        uploaded_by: str,
        location_id: str = None,
        source: str = "upload",
        period_start: str = None,
        period_end: str = None,
        is_personal: bool = False,
        auto_approve_threshold: float = 0.95
    ) -> str:
        """Add a new emission document to the database."""
        import uuid
        
        doc_id = str(uuid.uuid4())
        emission_scope = CATEGORY_SCOPE_MAP.get(
            EmissionCategory(category) if category in [e.value for e in EmissionCategory] else EmissionCategory.OTHER,
            EmissionScope.SCOPE_3
        ).value
        
        # Determine confidence level
        if confidence >= 0.9:
            confidence_level = "high"
        elif confidence >= 0.7:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        # Determine status
        status = DocumentStatus.PENDING.value
        if confidence >= auto_approve_threshold and not is_personal:
            status = DocumentStatus.AUTO_APPROVED.value
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO emission_documents (
                id, company_id, location_id, document_type, category, source,
                filename, raw_text, extracted_data, confidence, confidence_level,
                calculated_co2e_kg, emission_scope, period_start, period_end,
                status, uploaded_by, is_personal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id, company_id, location_id, document_type, category, source,
            filename, raw_text, json.dumps(extracted_data), confidence, confidence_level,
            calculated_co2e_kg, emission_scope, period_start, period_end,
            status, uploaded_by, 1 if is_personal else 0
        ))
        
        conn.commit()
        conn.close()
        
        # Log action
        self.log_action("document_added", "emission_document", doc_id, uploaded_by, {
            "document_type": document_type,
            "category": category,
            "confidence": confidence,
            "status": status,
            "co2e_kg": calculated_co2e_kg
        })
        
        # If auto-approved and not personal, create emission entry
        if status == DocumentStatus.AUTO_APPROVED.value and not is_personal:
            self._create_emission_entry_from_document(doc_id)
        
        return doc_id
    
    def approve_document(self, doc_id: str, user_email: str, 
                         approved_data: dict = None, notes: str = None) -> bool:
        """Approve a document and create emission entry."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE emission_documents
            SET status = ?, reviewed_by = ?, reviewed_at = ?, 
                approved_data = ?, notes = ?
            WHERE id = ?
        """, (
            DocumentStatus.APPROVED.value,
            user_email,
            datetime.now().isoformat(),
            json.dumps(approved_data) if approved_data else None,
            notes,
            doc_id
        ))
        
        conn.commit()
        conn.close()
        
        # Log and create entry
        self.log_action("document_approved", "emission_document", doc_id, user_email)
        self._create_emission_entry_from_document(doc_id)
        
        return True
    
    def _create_emission_entry_from_document(self, doc_id: str):
        """Create an emission entry from an approved document."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM emission_documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        
        columns = [desc[0] for desc in cursor.description]
        doc = dict(zip(columns, row))
        
        # Skip personal expenses
        if doc.get('is_personal'):
            conn.close()
            return
        
        import uuid
        entry_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO emission_entries (
                id, document_id, company_id, location_id,
                category, emission_scope, description,
                co2e_kg, period_start, period_end, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            doc_id,
            doc['company_id'],
            doc.get('location_id'),
            doc['category'],
            doc['emission_scope'],
            f"{doc['document_type']} - {doc['filename']}",
            doc['calculated_co2e_kg'],
            doc.get('period_start'),
            doc.get('period_end'),
            doc['source']
        ))
        
        conn.commit()
        conn.close()
        
        # Update aggregates
        self._update_aggregates(doc['company_id'])
    
    def _update_aggregates(self, company_id: str):
        """Update carbon footprint aggregates for a company."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        year = datetime.now().year
        
        # Calculate totals by scope
        cursor.execute("""
            SELECT emission_scope, SUM(co2e_kg) as total
            FROM emission_entries
            WHERE company_id = ?
            GROUP BY emission_scope
        """, (company_id,))
        
        totals = {row[0]: row[1] for row in cursor.fetchall()}
        
        scope_1 = totals.get('scope_1', 0) or 0
        scope_2 = totals.get('scope_2', 0) or 0
        scope_3 = totals.get('scope_3', 0) or 0
        total = scope_1 + scope_2 + scope_3
        
        # Upsert carbon footprint
        import uuid
        cursor.execute("""
            INSERT INTO carbon_footprints (id, company_id, year, scope_1_kg, scope_2_kg, scope_3_kg, total_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id, year) DO UPDATE SET
                scope_1_kg = excluded.scope_1_kg,
                scope_2_kg = excluded.scope_2_kg,
                scope_3_kg = excluded.scope_3_kg,
                total_kg = excluded.total_kg,
                updated_at = CURRENT_TIMESTAMP
        """, (
            f"{company_id}-{year}",
            company_id,
            year,
            scope_1,
            scope_2,
            scope_3,
            total
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== QUERY METHODS ====================
    
    def get_pending_documents(self, company_id: str = None, limit: int = 50) -> List[Dict]:
        """Get pending documents for review."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if company_id:
            cursor.execute("""
                SELECT * FROM emission_documents 
                WHERE status = 'pending' AND company_id = ?
                ORDER BY uploaded_at DESC LIMIT ?
            """, (company_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM emission_documents 
                WHERE status = 'pending'
                ORDER BY uploaded_at DESC LIMIT ?
            """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_carbon_footprint(self, company_id: str, year: int = None) -> Dict:
        """Get carbon footprint for a company."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if year:
            cursor.execute("""
                SELECT * FROM carbon_footprints 
                WHERE company_id = ? AND year = ?
            """, (company_id, year))
        else:
            cursor.execute("""
                SELECT * FROM carbon_footprints 
                WHERE company_id = ?
                ORDER BY year DESC LIMIT 1
            """, (company_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {}
        
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
        
        conn.close()
        return result
    
    def get_emissions_by_category(self, company_id: str, year: int = None) -> Dict:
        """Get emissions breakdown by category."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        year = year or datetime.now().year
        
        cursor.execute("""
            SELECT category, SUM(co2e_kg) as total_kg
            FROM emission_entries
            WHERE company_id = ?
            GROUP BY category
            ORDER BY total_kg DESC
        """, (company_id,))
        
        results = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return results
    
    def get_stats(self, company_id: str = None) -> Dict:
        """Get overall statistics."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        stats = {}
        
        # Document counts
        if company_id:
            cursor.execute("""
                SELECT status, COUNT(*) FROM emission_documents 
                WHERE company_id = ? GROUP BY status
            """, (company_id,))
        else:
            cursor.execute("SELECT status, COUNT(*) FROM emission_documents GROUP BY status")
        
        stats['documents'] = dict(cursor.fetchall())
        
        # Total emissions
        if company_id:
            cursor.execute("""
                SELECT SUM(co2e_kg) FROM emission_entries WHERE company_id = ?
            """, (company_id,))
        else:
            cursor.execute("SELECT SUM(co2e_kg) FROM emission_entries")
        
        stats['total_emissions_kg'] = cursor.fetchone()[0] or 0
        stats['total_emissions_tonnes'] = stats['total_emissions_kg'] / 1000
        
        conn.close()
        return stats


# Singleton instance
unified_db = UnifiedSustainabilityDB()


"""
Sustainability Database Models

SQLite-based structured storage for sustainability data including:
- Companies and their profiles
- Carbon footprints (Scope 1, 2, 3)
- ESG scores and metrics
- Reduction plans and initiatives
- Industry benchmarks
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum


class Scope(str, Enum):
    """GHG Protocol emission scopes."""
    SCOPE_1 = "scope_1"  # Direct emissions
    SCOPE_2 = "scope_2"  # Indirect from energy
    SCOPE_3 = "scope_3"  # Value chain


class ESGRating(str, Enum):
    """ESG rating scale."""
    AAA = "AAA"  # Leader
    AA = "AA"
    A = "A"
    BBB = "BBB"  # Average
    BB = "BB"
    B = "B"
    CCC = "CCC"  # Laggard
    CC = "CC"


# ==================== Data Models ====================

@dataclass
class Company:
    """Company profile."""
    id: str
    name: str
    industry: str
    sub_industry: Optional[str] = None
    employees: Optional[int] = None
    revenue_usd: Optional[float] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = None
    website: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Location:
    """Company location/facility."""
    id: str
    company_id: str
    name: str
    location_type: str  # headquarters, regional, warehouse, factory
    country: str
    city: Optional[str] = None
    employees: Optional[int] = None
    sqft: Optional[float] = None
    renewable_energy_percent: float = 0.0


@dataclass
class CarbonFootprint:
    """Annual carbon footprint record."""
    id: str
    company_id: str
    year: int
    scope_1_kg: float = 0.0
    scope_2_kg: float = 0.0
    scope_3_kg: float = 0.0
    total_kg: float = 0.0
    methodology: str = "GHG Protocol"
    verification_status: str = "self-reported"
    verified_by: Optional[str] = None
    breakdown: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmissionSource:
    """Individual emission source within a footprint."""
    id: str
    footprint_id: str
    category: str  # business_travel, employee_commuting, office_energy, etc.
    scope: str  # scope_1, scope_2, scope_3
    co2e_kg: float
    activity_data: Dict[str, Any] = field(default_factory=dict)
    emission_factor: Optional[float] = None
    emission_factor_source: Optional[str] = None


@dataclass 
class ESGScore:
    """ESG assessment record."""
    id: str
    company_id: str
    assessment_date: datetime
    overall_score: float
    rating: str
    environmental_score: float
    social_score: float
    governance_score: float
    environmental_metrics: Dict[str, float] = field(default_factory=dict)
    social_metrics: Dict[str, float] = field(default_factory=dict)
    governance_metrics: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    industry_percentile: Optional[float] = None


@dataclass
class ReductionPlan:
    """Carbon reduction plan."""
    id: str
    company_id: str
    name: str
    base_year: int
    target_year: int
    base_emissions_kg: float
    target_emissions_kg: float
    target_reduction_percent: float
    strategy: str
    status: str = "active"  # active, completed, cancelled
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReductionInitiative:
    """Individual initiative within a reduction plan."""
    id: str
    plan_id: str
    name: str
    description: str
    category: str  # energy, travel, supply_chain, waste, etc.
    target_reduction_kg: float
    target_reduction_percent: float
    timeline_months: int
    estimated_cost_usd: Optional[float] = None
    actual_reduction_kg: Optional[float] = None
    status: str = "planned"  # planned, in_progress, completed, cancelled
    start_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None


@dataclass
class IndustryBenchmark:
    """Industry benchmark data."""
    id: str
    industry: str
    year: int
    metric_name: str  # carbon_intensity, renewable_percent, etc.
    metric_unit: str
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_90: float
    sample_size: int
    source: str


# ==================== Database Service ====================

class SustainabilityDB:
    """
    SQLite database service for sustainability data.
    
    Features:
    - CRUD operations for all sustainability entities
    - Company profiles with locations
    - Carbon footprint tracking by year
    - ESG scoring history
    - Reduction plans and initiatives
    - Industry benchmarks for comparison
    """
    
    def __init__(self, db_path: str = "data/sustainability.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                industry TEXT NOT NULL,
                sub_industry TEXT,
                employees INTEGER,
                revenue_usd REAL,
                headquarters TEXT,
                founded_year INTEGER,
                website TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                location_type TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT,
                employees INTEGER,
                sqft REAL,
                renewable_energy_percent REAL DEFAULT 0,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Carbon footprints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carbon_footprints (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                year INTEGER NOT NULL,
                scope_1_kg REAL DEFAULT 0,
                scope_2_kg REAL DEFAULT 0,
                scope_3_kg REAL DEFAULT 0,
                total_kg REAL DEFAULT 0,
                methodology TEXT DEFAULT 'GHG Protocol',
                verification_status TEXT DEFAULT 'self-reported',
                verified_by TEXT,
                breakdown TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, year)
            )
        """)
        
        # Emission sources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emission_sources (
                id TEXT PRIMARY KEY,
                footprint_id TEXT NOT NULL,
                category TEXT NOT NULL,
                scope TEXT NOT NULL,
                co2e_kg REAL NOT NULL,
                activity_data TEXT,
                emission_factor REAL,
                emission_factor_source TEXT,
                FOREIGN KEY (footprint_id) REFERENCES carbon_footprints(id)
            )
        """)
        
        # ESG scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS esg_scores (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                assessment_date TIMESTAMP NOT NULL,
                overall_score REAL NOT NULL,
                rating TEXT NOT NULL,
                environmental_score REAL NOT NULL,
                social_score REAL NOT NULL,
                governance_score REAL NOT NULL,
                environmental_metrics TEXT,
                social_metrics TEXT,
                governance_metrics TEXT,
                strengths TEXT,
                weaknesses TEXT,
                industry_percentile REAL,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Reduction plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reduction_plans (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                base_year INTEGER NOT NULL,
                target_year INTEGER NOT NULL,
                base_emissions_kg REAL NOT NULL,
                target_emissions_kg REAL NOT NULL,
                target_reduction_percent REAL NOT NULL,
                strategy TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Reduction initiatives table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reduction_initiatives (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                target_reduction_kg REAL NOT NULL,
                target_reduction_percent REAL NOT NULL,
                timeline_months INTEGER,
                estimated_cost_usd REAL,
                actual_reduction_kg REAL,
                status TEXT DEFAULT 'planned',
                start_date TIMESTAMP,
                completion_date TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES reduction_plans(id)
            )
        """)
        
        # Industry benchmarks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_benchmarks (
                id TEXT PRIMARY KEY,
                industry TEXT NOT NULL,
                year INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_unit TEXT NOT NULL,
                percentile_25 REAL,
                percentile_50 REAL,
                percentile_75 REAL,
                percentile_90 REAL,
                sample_size INTEGER,
                source TEXT,
                UNIQUE(industry, year, metric_name)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_footprints_company ON carbon_footprints(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_footprints_year ON carbon_footprints(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_esg_company ON esg_scores(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_company ON locations(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_benchmarks_industry ON industry_benchmarks(industry)")
        
        conn.commit()
        conn.close()
    
    # ==================== Company Operations ====================
    
    def create_company(self, company: Company) -> str:
        """Create a new company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO companies (id, name, industry, sub_industry, employees, 
                                   revenue_usd, headquarters, founded_year, website, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company.id, company.name, company.industry, company.sub_industry,
              company.employees, company.revenue_usd, company.headquarters,
              company.founded_year, company.website, company.description))
        
        conn.commit()
        conn.close()
        return company.id
    
    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get company by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def list_companies(self, industry: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all companies, optionally filtered by industry."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if industry:
            cursor.execute("SELECT * FROM companies WHERE industry = ?", (industry,))
        else:
            cursor.execute("SELECT * FROM companies")
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_company(self, company_id: str, updates: Dict[str, Any]) -> bool:
        """Update company fields."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [company_id]
        
        cursor.execute(f"UPDATE companies SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # ==================== Location Operations ====================
    
    def add_location(self, location: Location) -> str:
        """Add a company location."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO locations (id, company_id, name, location_type, country, city, 
                                   employees, sqft, renewable_energy_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (location.id, location.company_id, location.name, location.location_type,
              location.country, location.city, location.employees, location.sqft,
              location.renewable_energy_percent))
        
        conn.commit()
        conn.close()
        return location.id
    
    def get_company_locations(self, company_id: str) -> List[Dict[str, Any]]:
        """Get all locations for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM locations WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ==================== Carbon Footprint Operations ====================
    
    def record_footprint(self, footprint: CarbonFootprint) -> str:
        """Record annual carbon footprint."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        breakdown_json = json.dumps(footprint.breakdown) if footprint.breakdown else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO carbon_footprints 
            (id, company_id, year, scope_1_kg, scope_2_kg, scope_3_kg, total_kg,
             methodology, verification_status, verified_by, breakdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (footprint.id, footprint.company_id, footprint.year,
              footprint.scope_1_kg, footprint.scope_2_kg, footprint.scope_3_kg,
              footprint.total_kg, footprint.methodology, footprint.verification_status,
              footprint.verified_by, breakdown_json))
        
        conn.commit()
        conn.close()
        return footprint.id
    
    def get_footprint(self, company_id: str, year: int) -> Optional[Dict[str, Any]]:
        """Get carbon footprint for a specific year."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM carbon_footprints 
            WHERE company_id = ? AND year = ?
        """, (company_id, year))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get('breakdown'):
                result['breakdown'] = json.loads(result['breakdown'])
            return result
        return None
    
    def get_footprint_history(self, company_id: str, years: int = 5) -> List[Dict[str, Any]]:
        """Get carbon footprint history for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM carbon_footprints 
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT ?
        """, (company_id, years))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('breakdown'):
                result['breakdown'] = json.loads(result['breakdown'])
            results.append(result)
        return results
    
    def add_emission_source(self, source: EmissionSource) -> str:
        """Add an emission source to a footprint."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        activity_json = json.dumps(source.activity_data) if source.activity_data else None
        
        cursor.execute("""
            INSERT INTO emission_sources 
            (id, footprint_id, category, scope, co2e_kg, activity_data, 
             emission_factor, emission_factor_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (source.id, source.footprint_id, source.category, source.scope,
              source.co2e_kg, activity_json, source.emission_factor,
              source.emission_factor_source))
        
        conn.commit()
        conn.close()
        return source.id
    
    def get_emission_sources(self, footprint_id: str) -> List[Dict[str, Any]]:
        """Get all emission sources for a footprint."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM emission_sources WHERE footprint_id = ?", (footprint_id,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('activity_data'):
                result['activity_data'] = json.loads(result['activity_data'])
            results.append(result)
        return results
    
    # ==================== ESG Score Operations ====================
    
    def record_esg_score(self, score: ESGScore) -> str:
        """Record ESG assessment."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO esg_scores 
            (id, company_id, assessment_date, overall_score, rating,
             environmental_score, social_score, governance_score,
             environmental_metrics, social_metrics, governance_metrics,
             strengths, weaknesses, industry_percentile)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (score.id, score.company_id, score.assessment_date, score.overall_score,
              score.rating, score.environmental_score, score.social_score,
              score.governance_score, json.dumps(score.environmental_metrics),
              json.dumps(score.social_metrics), json.dumps(score.governance_metrics),
              json.dumps(score.strengths), json.dumps(score.weaknesses),
              score.industry_percentile))
        
        conn.commit()
        conn.close()
        return score.id
    
    def get_latest_esg_score(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest ESG score for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM esg_scores 
            WHERE company_id = ?
            ORDER BY assessment_date DESC
            LIMIT 1
        """, (company_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            for field in ['environmental_metrics', 'social_metrics', 'governance_metrics', 'strengths', 'weaknesses']:
                if result.get(field):
                    result[field] = json.loads(result[field])
            return result
        return None
    
    def get_esg_history(self, company_id: str) -> List[Dict[str, Any]]:
        """Get ESG score history for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM esg_scores 
            WHERE company_id = ?
            ORDER BY assessment_date DESC
        """, (company_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            for field in ['environmental_metrics', 'social_metrics', 'governance_metrics', 'strengths', 'weaknesses']:
                if result.get(field):
                    result[field] = json.loads(result[field])
            results.append(result)
        return results
    
    # ==================== Reduction Plan Operations ====================
    
    def create_reduction_plan(self, plan: ReductionPlan) -> str:
        """Create a reduction plan."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reduction_plans 
            (id, company_id, name, base_year, target_year, base_emissions_kg,
             target_emissions_kg, target_reduction_percent, strategy, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (plan.id, plan.company_id, plan.name, plan.base_year, plan.target_year,
              plan.base_emissions_kg, plan.target_emissions_kg, plan.target_reduction_percent,
              plan.strategy, plan.status))
        
        conn.commit()
        conn.close()
        return plan.id
    
    def add_initiative(self, initiative: ReductionInitiative) -> str:
        """Add an initiative to a reduction plan."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reduction_initiatives 
            (id, plan_id, name, description, category, target_reduction_kg,
             target_reduction_percent, timeline_months, estimated_cost_usd,
             actual_reduction_kg, status, start_date, completion_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (initiative.id, initiative.plan_id, initiative.name, initiative.description,
              initiative.category, initiative.target_reduction_kg, initiative.target_reduction_percent,
              initiative.timeline_months, initiative.estimated_cost_usd, initiative.actual_reduction_kg,
              initiative.status, initiative.start_date, initiative.completion_date))
        
        conn.commit()
        conn.close()
        return initiative.id
    
    def get_reduction_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a reduction plan with its initiatives."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM reduction_plans WHERE id = ?", (plan_id,))
        plan_row = cursor.fetchone()
        
        if not plan_row:
            conn.close()
            return None
        
        plan = dict(plan_row)
        
        cursor.execute("SELECT * FROM reduction_initiatives WHERE plan_id = ?", (plan_id,))
        initiatives = [dict(row) for row in cursor.fetchall()]
        plan['initiatives'] = initiatives
        
        conn.close()
        return plan
    
    def get_company_plans(self, company_id: str) -> List[Dict[str, Any]]:
        """Get all reduction plans for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM reduction_plans WHERE company_id = ?", (company_id,))
        plans = []
        
        for plan_row in cursor.fetchall():
            plan = dict(plan_row)
            cursor.execute("SELECT * FROM reduction_initiatives WHERE plan_id = ?", (plan['id'],))
            plan['initiatives'] = [dict(row) for row in cursor.fetchall()]
            plans.append(plan)
        
        conn.close()
        return plans
    
    # ==================== Benchmark Operations ====================
    
    def add_benchmark(self, benchmark: IndustryBenchmark) -> str:
        """Add industry benchmark data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO industry_benchmarks 
            (id, industry, year, metric_name, metric_unit, percentile_25,
             percentile_50, percentile_75, percentile_90, sample_size, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (benchmark.id, benchmark.industry, benchmark.year, benchmark.metric_name,
              benchmark.metric_unit, benchmark.percentile_25, benchmark.percentile_50,
              benchmark.percentile_75, benchmark.percentile_90, benchmark.sample_size,
              benchmark.source))
        
        conn.commit()
        conn.close()
        return benchmark.id
    
    def get_benchmarks(self, industry: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get benchmarks for an industry."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if year:
            cursor.execute("""
                SELECT * FROM industry_benchmarks 
                WHERE industry = ? AND year = ?
            """, (industry, year))
        else:
            cursor.execute("""
                SELECT * FROM industry_benchmarks 
                WHERE industry = ?
                ORDER BY year DESC, metric_name
            """, (industry,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def compare_to_benchmark(self, company_id: str, metric_name: str, value: float) -> Dict[str, Any]:
        """Compare a company's metric to industry benchmark."""
        company = self.get_company(company_id)
        if not company:
            return {"error": "Company not found"}
        
        benchmarks = self.get_benchmarks(company['industry'])
        metric_benchmarks = [b for b in benchmarks if b['metric_name'] == metric_name]
        
        if not metric_benchmarks:
            return {"error": f"No benchmark data for {metric_name} in {company['industry']}"}
        
        latest = metric_benchmarks[0]
        
        # Determine percentile
        if value <= latest['percentile_25']:
            percentile = "Top 25%"
            rating = "Excellent"
        elif value <= latest['percentile_50']:
            percentile = "Top 50%"
            rating = "Good"
        elif value <= latest['percentile_75']:
            percentile = "Top 75%"
            rating = "Average"
        else:
            percentile = "Bottom 25%"
            rating = "Below Average"
        
        return {
            "company": company['name'],
            "industry": company['industry'],
            "metric": metric_name,
            "value": value,
            "unit": latest['metric_unit'],
            "percentile": percentile,
            "rating": rating,
            "benchmark": {
                "p25": latest['percentile_25'],
                "p50": latest['percentile_50'],
                "p75": latest['percentile_75'],
                "p90": latest['percentile_90'],
                "year": latest['year'],
                "source": latest['source']
            }
        }
    
    # ==================== Analytics ====================
    
    def get_company_dashboard(self, company_id: str) -> Dict[str, Any]:
        """Get comprehensive sustainability dashboard for a company."""
        company = self.get_company(company_id)
        if not company:
            return {"error": "Company not found"}
        
        locations = self.get_company_locations(company_id)
        footprint_history = self.get_footprint_history(company_id)
        latest_esg = self.get_latest_esg_score(company_id)
        plans = self.get_company_plans(company_id)
        
        # Calculate trends
        if len(footprint_history) >= 2:
            latest = footprint_history[0]['total_kg']
            previous = footprint_history[1]['total_kg']
            yoy_change = ((latest - previous) / previous) * 100 if previous else 0
        else:
            yoy_change = None
        
        return {
            "company": company,
            "locations": locations,
            "carbon_footprint": {
                "current": footprint_history[0] if footprint_history else None,
                "history": footprint_history,
                "yoy_change_percent": yoy_change
            },
            "esg": {
                "current": latest_esg,
                "rating": latest_esg['rating'] if latest_esg else None
            },
            "reduction_plans": plans,
            "summary": {
                "total_emissions_kg": footprint_history[0]['total_kg'] if footprint_history else 0,
                "esg_score": latest_esg['overall_score'] if latest_esg else None,
                "active_initiatives": sum(
                    len([i for i in p.get('initiatives', []) if i['status'] == 'in_progress'])
                    for p in plans
                )
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        for table in ['companies', 'locations', 'carbon_footprints', 'esg_scores', 'reduction_plans', 'industry_benchmarks']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        conn.close()
        return stats


# Singleton instance
sustainability_db = SustainabilityDB()


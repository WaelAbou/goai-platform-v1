"""
Migration Script: Consolidate all sustainability data into unified database.

Migrates data from:
- review_queue.db → emission_documents
- sustainability.db → companies, locations, carbon_footprints, esg_scores, etc.
"""

import sqlite3
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.sustainability.unified_database import UnifiedSustainabilityDB


def migrate_data():
    """Run the migration."""
    print("🔄 Starting migration to unified sustainability database...")
    print("=" * 60)
    
    # Initialize unified DB
    unified_db = UnifiedSustainabilityDB("data/sustainability_unified.db")
    unified_conn = sqlite3.connect("data/sustainability_unified.db")
    unified_cursor = unified_conn.cursor()
    
    # ==================== MIGRATE FROM sustainability.db ====================
    print("\n📦 Migrating from sustainability.db...")
    
    old_sustainability = "data/sustainability.db"
    if os.path.exists(old_sustainability):
        old_conn = sqlite3.connect(old_sustainability)
        old_cursor = old_conn.cursor()
        
        # Migrate companies
        print("  → Companies...")
        old_cursor.execute("SELECT * FROM companies")
        columns = [desc[0] for desc in old_cursor.description]
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO companies (id, name, industry, sub_industry, employees, 
                        revenue_usd, headquarters, founded_year, website, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('name'), data.get('industry'), data.get('sub_industry'),
                    data.get('employees'), data.get('revenue_usd'), data.get('headquarters'),
                    data.get('founded_year'), data.get('website'), data.get('description'),
                    data.get('created_at')
                ))
                print(f"    ✓ {data.get('name')}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        # Migrate locations
        print("  → Locations...")
        old_cursor.execute("SELECT * FROM locations")
        columns = [desc[0] for desc in old_cursor.description]
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO locations (id, company_id, name, type, city, country, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('company_id'), data.get('name'),
                    data.get('type', 'office'), data.get('city'), data.get('country'),
                    data.get('created_at')
                ))
                print(f"    ✓ {data.get('name')}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        # Migrate carbon footprints
        print("  → Carbon Footprints...")
        old_cursor.execute("SELECT * FROM carbon_footprints")
        columns = [desc[0] for desc in old_cursor.description]
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO carbon_footprints (
                        id, company_id, year, scope_1_kg, scope_2_kg, scope_3_kg, total_kg,
                        methodology, verification_status, breakdown_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('company_id'), data.get('year'),
                    data.get('scope_1_kg', 0), data.get('scope_2_kg', 0), data.get('scope_3_kg', 0),
                    data.get('total_kg', 0), data.get('methodology'), data.get('verification_status'),
                    data.get('breakdown'), data.get('created_at')
                ))
                print(f"    ✓ {data.get('company_id')} - {data.get('year')}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        # Migrate ESG scores
        print("  → ESG Scores...")
        old_cursor.execute("SELECT * FROM esg_scores")
        columns = [desc[0] for desc in old_cursor.description]
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO esg_scores (
                        id, company_id, assessment_date, overall_score, environmental_score,
                        social_score, governance_score, rating, environmental_metrics,
                        social_metrics, governance_metrics, strengths, weaknesses, industry_percentile
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('company_id'), data.get('assessment_date'),
                    data.get('overall_score'), data.get('environmental_score'),
                    data.get('social_score'), data.get('governance_score'), data.get('rating'),
                    data.get('environmental_metrics'), data.get('social_metrics'),
                    data.get('governance_metrics'), data.get('strengths'), data.get('weaknesses'),
                    data.get('industry_percentile')
                ))
                print(f"    ✓ {data.get('company_id')} - Score: {data.get('overall_score')}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        # Migrate reduction plans
        print("  → Reduction Plans...")
        old_cursor.execute("SELECT * FROM reduction_plans")
        columns = [desc[0] for desc in old_cursor.description]
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO reduction_plans (
                        id, company_id, name, base_year, target_year, base_emissions_kg,
                        target_emissions_kg, target_reduction_percent, strategy, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('company_id'), data.get('name'),
                    data.get('base_year'), data.get('target_year'), data.get('base_emissions_kg'),
                    data.get('target_emissions_kg'), data.get('target_reduction_percent'),
                    data.get('strategy'), data.get('status'), data.get('created_at')
                ))
                print(f"    ✓ {data.get('name')}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        old_conn.close()
        print("  ✅ sustainability.db migration complete")
    else:
        print("  ⚠️ sustainability.db not found, skipping")
    
    # ==================== MIGRATE FROM review_queue.db ====================
    print("\n📦 Migrating from review_queue.db...")
    
    old_queue = "data/review_queue.db"
    if os.path.exists(old_queue):
        old_conn = sqlite3.connect(old_queue)
        old_cursor = old_conn.cursor()
        
        # Migrate review items → emission_documents
        print("  → Review Items → Emission Documents...")
        old_cursor.execute("SELECT * FROM review_items")
        columns = [desc[0] for desc in old_cursor.description]
        
        migrated = 0
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                # Map category to scope
                category = data.get('category', 'other')
                scope_map = {
                    'energy': 'scope_2',
                    'travel': 'scope_3',
                    'fleet': 'scope_1',
                    'shipping': 'scope_3',
                    'commuting': 'scope_3',
                }
                emission_scope = scope_map.get(category, 'scope_3')
                
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO emission_documents (
                        id, company_id, location_id, document_type, category, source,
                        filename, raw_text, extracted_data, confidence, confidence_level,
                        calculated_co2e_kg, emission_scope, period_start, period_end,
                        status, uploaded_by, uploaded_at, reviewed_by, reviewed_at,
                        approved_data, rejection_reason, notes, is_flagged, flag_reason,
                        is_anomaly, anomaly_details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('company_id') or 'xyz-corp-001', data.get('location_id'),
                    data.get('document_type'), category, data.get('source'),
                    data.get('filename'), data.get('raw_text'), data.get('extracted_data'),
                    data.get('confidence'), data.get('confidence_level'),
                    data.get('calculated_co2e_kg'), emission_scope,
                    data.get('period_start'), data.get('period_end'),
                    data.get('status'), data.get('uploaded_by'), data.get('uploaded_at'),
                    data.get('reviewed_by'), data.get('reviewed_at'),
                    data.get('approved_data'), data.get('rejection_reason'), data.get('notes'),
                    data.get('is_flagged', 0), data.get('flag_reason'),
                    data.get('is_anomaly', 0), data.get('anomaly_details')
                ))
                migrated += 1
            except Exception as e:
                print(f"    ✗ Error migrating {data.get('filename')}: {e}")
        
        print(f"    ✓ Migrated {migrated} documents")
        
        # Migrate audit log
        print("  → Audit Log...")
        old_cursor.execute("SELECT * FROM audit_log")
        columns = [desc[0] for desc in old_cursor.description]
        
        audit_count = 0
        for row in old_cursor.fetchall():
            data = dict(zip(columns, row))
            try:
                unified_cursor.execute("""
                    INSERT OR REPLACE INTO audit_log (
                        id, timestamp, user_email, action, entity_type, entity_id, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('id'), data.get('timestamp'), data.get('user'),
                    data.get('action'), 'emission_document', data.get('review_item_id'),
                    data.get('details')
                ))
                audit_count += 1
            except Exception as e:
                pass
        
        print(f"    ✓ Migrated {audit_count} audit entries")
        
        old_conn.close()
        print("  ✅ review_queue.db migration complete")
    else:
        print("  ⚠️ review_queue.db not found, skipping")
    
    # ==================== CREATE EMISSION ENTRIES ====================
    print("\n📦 Creating emission entries from approved documents...")
    
    unified_cursor.execute("""
        SELECT id, company_id, location_id, category, calculated_co2e_kg, 
               document_type, filename, source, period_start, period_end
        FROM emission_documents 
        WHERE status IN ('approved', 'auto_approved') 
        AND calculated_co2e_kg IS NOT NULL
        AND calculated_co2e_kg > 0
    """)
    
    entries_created = 0
    for row in unified_cursor.fetchall():
        doc_id, company_id, location_id, category, co2e_kg, doc_type, filename, source, period_start, period_end = row
        
        # Check if entry already exists
        unified_cursor.execute("SELECT id FROM emission_entries WHERE document_id = ?", (doc_id,))
        if unified_cursor.fetchone():
            continue
        
        import uuid
        scope_map = {
            'energy': 'scope_2',
            'travel': 'scope_3',
            'fleet': 'scope_1',
            'shipping': 'scope_3',
        }
        emission_scope = scope_map.get(category, 'scope_3')
        
        unified_cursor.execute("""
            INSERT INTO emission_entries (
                id, document_id, company_id, location_id, category, emission_scope,
                description, co2e_kg, period_start, period_end, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), doc_id, company_id or 'xyz-corp-001', location_id,
            category, emission_scope, f"{doc_type} - {filename}",
            co2e_kg, period_start, period_end, source
        ))
        entries_created += 1
    
    print(f"  ✓ Created {entries_created} emission entries")
    
    # ==================== FINALIZE ====================
    unified_conn.commit()
    unified_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    
    # Show summary
    show_summary()


def show_summary():
    """Show summary of unified database."""
    conn = sqlite3.connect("data/sustainability_unified.db")
    cursor = conn.cursor()
    
    print("\n📊 UNIFIED DATABASE SUMMARY")
    print("-" * 40)
    
    tables = [
        ("companies", "🏢"),
        ("locations", "📍"),
        ("emission_documents", "📋"),
        ("emission_entries", "📊"),
        ("carbon_footprints", "🌍"),
        ("esg_scores", "📈"),
        ("reduction_plans", "🎯"),
        ("knowledge_documents", "📚"),
        ("audit_log", "📜"),
    ]
    
    for table, icon in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {icon} {table}: {count} records")
    
    # Total emissions
    cursor.execute("SELECT SUM(co2e_kg) FROM emission_entries")
    total = cursor.fetchone()[0] or 0
    print(f"\n  🌍 Total Tracked Emissions: {total/1000:.2f} tonnes CO₂e")
    
    conn.close()
    
    print("\n📁 Database location: data/sustainability_unified.db")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    migrate_data()


#!/usr/bin/env python3
"""
Database Table Creation Script
Creates all tables defined in the models.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database import db, Base
from core.database.models import *  # Import all models

def create_tables():
    """Create all database tables."""
    print("🗄️  Creating database tables...")
    print(f"   Database URL: {db.config.url.replace(db.config.password, '***')}")
    
    try:
        # Create all tables
        db.create_tables()
        print("✅ Tables created successfully!")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n📋 Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

def drop_tables():
    """Drop all database tables (use with caution!)."""
    print("⚠️  Dropping all tables...")
    confirm = input("Are you sure? Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        db.drop_tables()
        print("✅ Tables dropped!")
    else:
        print("Cancelled.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_tables()
    else:
        create_tables()


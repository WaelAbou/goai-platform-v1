#!/usr/bin/env python3
"""
Database Seed Script
Populates the database with sample data.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database import db, DocumentService, SchemaService
from core.database.models import DocumentStatus

def seed_documents():
    """Add sample documents."""
    with db.session() as session:
        doc_service = DocumentService(session)
        
        samples = [
            {
                "filename": "ai_overview.txt",
                "content": """Artificial Intelligence (AI) is a branch of computer science focused on creating intelligent machines.

Machine Learning is a subset of AI that enables systems to learn from data without explicit programming. Key types include:
- Supervised Learning: Learning from labeled examples
- Unsupervised Learning: Finding patterns in unlabeled data
- Reinforcement Learning: Learning through trial and error

Deep Learning uses neural networks with multiple layers to learn hierarchical representations. Applications include:
- Natural Language Processing (NLP)
- Computer Vision
- Speech Recognition
- Autonomous Systems

Popular frameworks: TensorFlow, PyTorch, scikit-learn, Keras."""
            },
            {
                "filename": "python_guide.txt", 
                "content": """Python is a high-level programming language created by Guido van Rossum in 1991.

Key Features:
- Simple, readable syntax
- Dynamic typing
- Extensive standard library
- Cross-platform compatibility

Popular Frameworks:
- Django: Full-stack web framework
- Flask: Lightweight web framework
- FastAPI: Modern API framework with automatic docs
- PyTorch/TensorFlow: Machine learning
- Pandas/NumPy: Data science

Best Practices:
- Follow PEP 8 style guide
- Use virtual environments
- Write docstrings and tests
- Use type hints for clarity"""
            },
            {
                "filename": "cloud_computing.txt",
                "content": """Cloud Computing delivers computing services over the internet.

Service Models:
- IaaS (Infrastructure): VMs, storage, networks
- PaaS (Platform): Development environments
- SaaS (Software): Ready-to-use applications

Major Providers:
- AWS: Amazon Web Services (market leader)
- Azure: Microsoft's cloud platform
- GCP: Google Cloud Platform

Benefits:
- Scalability on demand
- Cost efficiency (pay-as-you-go)
- Global availability
- Built-in security and compliance

Key Services: EC2, S3, Lambda, Kubernetes, Serverless"""
            }
        ]
        
        for sample in samples:
            existing = doc_service.get_by_hash(
                __import__('hashlib').sha256(sample["content"].encode()).hexdigest()
            )
            if not existing:
                doc = doc_service.create(
                    filename=sample["filename"],
                    content=sample["content"],
                    file_type="txt",
                    metadata={"source": "seed_data"}
                )
                doc_service.update_status(doc.id, DocumentStatus.COMPLETED, chunk_count=1)
                print(f"   ✅ Created: {sample['filename']}")
            else:
                print(f"   ⏭️  Skipped (exists): {sample['filename']}")

def seed_schemas():
    """Add sample database schemas."""
    with db.session() as session:
        schema_service = SchemaService(session)
        
        ecommerce_schema = {
            "tables": {
                "customers": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "name", "type": "VARCHAR(100)"},
                        {"name": "email", "type": "VARCHAR(100)", "unique": True},
                        {"name": "created_at", "type": "TIMESTAMP"}
                    ]
                },
                "orders": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "customer_id", "type": "INTEGER", "foreign_key": "customers.id"},
                        {"name": "total", "type": "DECIMAL(10,2)"},
                        {"name": "status", "type": "VARCHAR(50)"},
                        {"name": "created_at", "type": "TIMESTAMP"}
                    ]
                },
                "products": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "name", "type": "VARCHAR(200)"},
                        {"name": "price", "type": "DECIMAL(10,2)"},
                        {"name": "category", "type": "VARCHAR(50)"},
                        {"name": "stock", "type": "INTEGER"}
                    ]
                },
                "order_items": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "order_id", "type": "INTEGER", "foreign_key": "orders.id"},
                        {"name": "product_id", "type": "INTEGER", "foreign_key": "products.id"},
                        {"name": "quantity", "type": "INTEGER"},
                        {"name": "unit_price", "type": "DECIMAL(10,2)"}
                    ]
                }
            }
        }
        
        if not schema_service.get("ecommerce"):
            schema_service.create(
                name="ecommerce",
                db_type="postgresql",
                schema_json=ecommerce_schema,
                description="Sample e-commerce database with customers, orders, and products"
            )
            print("   ✅ Created: ecommerce schema")
        else:
            print("   ⏭️  Skipped (exists): ecommerce schema")

def main():
    print("🌱 Seeding database...")
    print("\n📄 Documents:")
    seed_documents()
    print("\n🗄️  Schemas:")
    seed_schemas()
    print("\n✅ Seeding complete!")

if __name__ == "__main__":
    main()


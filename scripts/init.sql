-- GoAI Platform Database Initialization Script
-- This runs automatically when PostgreSQL container starts

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create indexes for full-text search (will be created after tables exist)
-- These are just placeholders; actual indexes are in SQLAlchemy models

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE goai_platform TO goai;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'GoAI Platform database initialized successfully';
END $$;


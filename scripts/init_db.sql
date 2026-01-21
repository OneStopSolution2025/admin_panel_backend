-- Database initialization script
-- This script is executed when PostgreSQL container starts

-- Create database if not exists
SELECT 'CREATE DATABASE admin_panel_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'admin_panel_db')\gexec

-- Connect to the database
\c admin_panel_db

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance
-- These will be created by Alembic migrations, but kept here as reference

-- Log successful initialization
SELECT 'Database initialized successfully' AS status;

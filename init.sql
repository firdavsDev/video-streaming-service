-- This file will be executed when PostgreSQL container starts

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE video_streaming'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'video_streaming');

-- Create test database
SELECT 'CREATE DATABASE video_streaming_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'video_streaming_test');

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Migration 003: Fix universe_scan_log schema to match pipeline expectations
-- Version: 2.7
-- Purpose: Add missing columns that pipeline tries to insert

-- Add missing columns to universe_scan_log
ALTER TABLE universe_scan_log ADD COLUMN scanned INTEGER DEFAULT 1;
ALTER TABLE universe_scan_log ADD COLUMN exclusion_reason TEXT;
ALTER TABLE universe_scan_log ADD COLUMN included_in_screening INTEGER DEFAULT 0;

-- Note: filter_reason column already exists and can serve same purpose as exclusion_reason
-- The pipeline will use exclusion_reason going forward

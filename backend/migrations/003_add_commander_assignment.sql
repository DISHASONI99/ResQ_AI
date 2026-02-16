-- Migration 003: Add commander assignment support
-- Created: 2026-01-21
-- Adds columns for dispatcher workflow and commander assignment

-- Add commander assignment columns to incidents
ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS assigned_commander VARCHAR(50);

ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMP;

ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;

-- Create index for commander queries
CREATE INDEX IF NOT EXISTS idx_incidents_assigned_commander ON incidents(assigned_commander);
CREATE INDEX IF NOT EXISTS idx_incidents_dispatched_at ON incidents(dispatched_at);

-- Migration: Add chat support to incidents table
-- Created: 2026-01-18

-- Add session_id and conversation_history columns
ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS session_id UUID,
ADD COLUMN IF NOT EXISTS conversation_history JSONB,
ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;

-- Create index on session_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_incidents_session_id ON incidents(session_id);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);

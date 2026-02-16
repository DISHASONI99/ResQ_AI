-- Migration 002: Add approval history for HITL
-- Created: 2026-01-19
-- ResQ AI Emergency Response System - Human-in-the-Loop Approvals

-- ============ APPROVAL HISTORY TABLE ============
CREATE TABLE IF NOT EXISTS approval_history (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) REFERENCES incidents(incident_id) ON DELETE CASCADE,
    decision VARCHAR(20) NOT NULL,  -- approved, edited, rejected
    approved_by VARCHAR(100) DEFAULT 'dispatcher',
    original_priority VARCHAR(10),
    edited_priority VARCHAR(10),
    original_assets JSONB,
    edited_assets JSONB,
    notes TEXT,
    approved_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for approval history
CREATE INDEX IF NOT EXISTS idx_approval_incident ON approval_history(incident_id);
CREATE INDEX IF NOT EXISTS idx_approval_decision ON approval_history(decision);
CREATE INDEX IF NOT EXISTS idx_approval_time ON approval_history(approved_at);

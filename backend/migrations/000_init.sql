-- Migration 000: Initial schema
-- Created: 2026-01-18
-- ResQ AI Emergency Response System

-- ============ INCIDENTS TABLE ============
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) UNIQUE NOT NULL,
    session_id UUID,
    priority VARCHAR(10),
    incident_type VARCHAR(100),
    location JSONB,
    address TEXT,
    conversation_history JSONB,
    recommended_assets JSONB,
    critical_instructions TEXT,
    reasoning TEXT,
    quality_score FLOAT,
    message_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============ DISPATCHED SERVICES TABLE ============
CREATE TABLE IF NOT EXISTS dispatched_services (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) REFERENCES incidents(incident_id) ON DELETE CASCADE,
    service_type VARCHAR(100) NOT NULL,
    service_name VARCHAR(200),
    quantity INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'dispatched',
    dispatched_at TIMESTAMP DEFAULT NOW(),
    arrived_at TIMESTAMP,
    resolved_at TIMESTAMP,
    notes TEXT
);

-- ============ INDEXES ============
CREATE INDEX IF NOT EXISTS idx_incidents_incident_id ON incidents(incident_id);
CREATE INDEX IF NOT EXISTS idx_incidents_session_id ON incidents(session_id);
CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(priority);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_dispatched_incident ON dispatched_services(incident_id);
CREATE INDEX IF NOT EXISTS idx_dispatched_status ON dispatched_services(status);

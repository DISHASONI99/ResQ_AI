"""
Postgres Service - Database operations for ResQ AI
"""
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import json
from pathlib import Path

_postgres_pool: Optional[asyncpg.Pool] = None


async def get_postgres_client() -> asyncpg.Pool:
    """Get or create Postgres connection pool."""
    global _postgres_pool
    
    if _postgres_pool is None:
        postgres_url = os.getenv("POSTGRES_URL", "postgresql://resq:resq@localhost:5432/resq")
        _postgres_pool = await asyncpg.create_pool(postgres_url)
        # Initialize database on first connection
        await init_database()
    
    return _postgres_pool


async def close_postgres():
    """Close Postgres connection pool."""
    global _postgres_pool
    if _postgres_pool:
        await _postgres_pool.close()
        _postgres_pool = None


async def init_database():
    """Run database migrations on startup."""
    global _postgres_pool
    if not _postgres_pool:
        return
    
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    
    async with _postgres_pool.acquire() as conn:
        # Run migrations in order
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            try:
                sql = migration_file.read_text()
                await conn.execute(sql)
                print(f"✅ Migration applied: {migration_file.name}")
            except Exception as e:
                # Ignore errors for already-applied migrations
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    print(f"⚠️ Migration warning ({migration_file.name}): {e}")


# ============ INCIDENTS ============

async def save_incident(
    incident_id: str,
    session_id: str,
    priority: str,
    incident_type: str,
    location: Dict,
    address: str = "",
    conversation_history: List[Dict] = None,
    recommended_assets: List[Dict] = None,
    critical_instructions: str = "",
    reasoning: str = "",
    quality_score: float = 0.0,
    status: str = "pending_dispatch",  # Default for dispatcher workflow
) -> bool:
    """Save or update an incident."""
    db = await get_postgres_client()
    
    query = """
        INSERT INTO incidents (
            incident_id, session_id, priority, incident_type, 
            location, address, conversation_history, recommended_assets,
            critical_instructions, reasoning, quality_score, status, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (incident_id) DO UPDATE SET
            priority = EXCLUDED.priority,
            incident_type = EXCLUDED.incident_type,
            location = EXCLUDED.location,
            address = EXCLUDED.address,
            conversation_history = EXCLUDED.conversation_history,
            recommended_assets = EXCLUDED.recommended_assets,
            critical_instructions = EXCLUDED.critical_instructions,
            reasoning = EXCLUDED.reasoning,
            quality_score = EXCLUDED.quality_score,
            status = EXCLUDED.status,
            updated_at = NOW()
    """
    
    try:
        await db.execute(
            query,
            incident_id,
            session_id,
            priority,
            incident_type,
            json.dumps(location) if location else "{}",
            address,
            json.dumps(conversation_history or []),
            json.dumps(recommended_assets or []),
            critical_instructions,
            reasoning,
            quality_score,
            status,
            datetime.utcnow(),
        )
        return True
    except Exception as e:
        print(f"❌ Failed to save incident: {e}")
        return False


async def get_all_incidents(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all incidents for dashboard."""
    db = await get_postgres_client()
    
    query = """
        SELECT 
            incident_id, session_id, priority, incident_type,
            location, address, recommended_assets, critical_instructions,
            quality_score, status, created_at, updated_at
        FROM incidents 
        ORDER BY created_at DESC 
        LIMIT $1 OFFSET $2
    """
    
    try:
        rows = await db.fetch(query, limit, offset)
        return [
            {
                "incident_id": row["incident_id"],
                "session_id": str(row["session_id"]) if row["session_id"] else None,
                "priority": row["priority"],
                "incident_type": row["incident_type"],
                "location": json.loads(row["location"]) if row["location"] else None,
                "address": row["address"],
                "recommended_assets": json.loads(row["recommended_assets"]) if row["recommended_assets"] else [],
                "critical_instructions": row["critical_instructions"],
                "quality_score": row["quality_score"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ Failed to fetch incidents: {e}")
        return []


async def update_incident_status(incident_id: str, status: str) -> bool:
    """Update incident status."""
    db = await get_postgres_client()
    
    try:
        await db.execute(
            "UPDATE incidents SET status = $1, updated_at = NOW() WHERE incident_id = $2",
            status,
            incident_id,
        )
        return True
    except Exception as e:
        print(f"❌ Failed to update incident status: {e}")
        return False


# ============ DISPATCHED SERVICES ============

async def save_dispatch(
    incident_id: str,
    service_type: str,
    service_name: str,
    quantity: int = 1,
    notes: str = "",
) -> bool:
    """Save a dispatched service."""
    db = await get_postgres_client()
    
    query = """
        INSERT INTO dispatched_services (
            incident_id, service_type, service_name, quantity, notes, dispatched_at
        ) VALUES ($1, $2, $3, $4, $5, $6)
    """
    
    try:
        await db.execute(
            query,
            incident_id,
            service_type,
            service_name,
            quantity,
            notes,
            datetime.utcnow(),
        )
        return True
    except Exception as e:
        print(f"❌ Failed to save dispatch: {e}")
        return False


async def get_all_dispatches(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all dispatched services for dashboard."""
    db = await get_postgres_client()
    
    query = """
        SELECT 
            d.id, d.incident_id, d.service_type, d.service_name, 
            d.quantity, d.status, d.dispatched_at, d.arrived_at, d.resolved_at,
            i.priority, i.incident_type, i.address
        FROM dispatched_services d
        LEFT JOIN incidents i ON d.incident_id = i.incident_id
        ORDER BY d.dispatched_at DESC 
        LIMIT $1 OFFSET $2
    """
    
    try:
        rows = await db.fetch(query, limit, offset)
        return [
            {
                "id": row["id"],
                "incident_id": row["incident_id"],
                "service_type": row["service_type"],
                "service_name": row["service_name"],
                "quantity": row["quantity"],
                "status": row["status"],
                "dispatched_at": row["dispatched_at"].isoformat() if row["dispatched_at"] else None,
                "arrived_at": row["arrived_at"].isoformat() if row["arrived_at"] else None,
                "resolved_at": row["resolved_at"].isoformat() if row["resolved_at"] else None,
                "priority": row["priority"],
                "incident_type": row["incident_type"],
                "address": row["address"],
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ Failed to fetch dispatches: {e}")
        return []


async def update_dispatch_status(dispatch_id: int, status: str) -> bool:
    """Update dispatch status (e.g., arrived, resolved)."""
    db = await get_postgres_client()
    
    update_field = ""
    if status == "arrived":
        update_field = ", arrived_at = NOW()"
    elif status == "resolved":
        update_field = ", resolved_at = NOW()"
    
    try:
        await db.execute(
            f"UPDATE dispatched_services SET status = $1{update_field} WHERE id = $2",
            status,
            dispatch_id,
        )
        return True
    except Exception as e:
        print(f"❌ Failed to update dispatch status: {e}")
        return False


# ============ APPROVAL HISTORY ============

async def save_approval(
    incident_id: str,
    decision: str,
    approved_by: str = "dispatcher",
    original_priority: str = None,
    edited_priority: str = None,
    original_assets: List[Dict] = None,
    edited_assets: List[Dict] = None,
    notes: str = "",
) -> bool:
    """Save HITL approval decision to history."""
    db = await get_postgres_client()
    
    query = """
        INSERT INTO approval_history (
            incident_id, decision, approved_by,
            original_priority, edited_priority,
            original_assets, edited_assets, notes, approved_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """
    
    try:
        await db.execute(
            query,
            incident_id,
            decision,
            approved_by,
            original_priority,
            edited_priority,
            json.dumps(original_assets or []),
            json.dumps(edited_assets or []),
            notes,
            datetime.utcnow(),
        )
        return True
    except Exception as e:
        print(f"❌ Failed to save approval: {e}")
        return False


async def get_approval_history(incident_id: str) -> List[Dict]:
    """Get approval history for an incident."""
    db = await get_postgres_client()
    
    query = """
        SELECT * FROM approval_history 
        WHERE incident_id = $1 
        ORDER BY approved_at DESC
    """
    
    try:
        rows = await db.fetch(query, incident_id)
        return [
            {
                "id": row["id"],
                "incident_id": row["incident_id"],
                "decision": row["decision"],
                "approved_by": row["approved_by"],
                "original_priority": row["original_priority"],
                "edited_priority": row["edited_priority"],
                "original_assets": json.loads(row["original_assets"]) if row["original_assets"] else [],
                "edited_assets": json.loads(row["edited_assets"]) if row["edited_assets"] else [],
                "notes": row["notes"],
                "approved_at": row["approved_at"].isoformat() if row["approved_at"] else None,
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ Failed to fetch approval history: {e}")
        return []

"""
Health check endpoint
"""
from fastapi import APIRouter, Depends
from src.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for Docker/K8s."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check - verifies all dependencies are available."""
    checks = {
        "qdrant": False,
        "groq": False,
    }
    
    # Check Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )
        client.get_collections()
        checks["qdrant"] = True
    except Exception:
        pass
    
    # Check Groq API key exists
    checks["groq"] = bool(settings.GROQ_API_KEY)
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks,
    }

"""
ResQ AI Backend - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.routes import health, incidents, search, media, chat, dispatcher, commander, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown."""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📦 Qdrant: {settings.QDRANT_URL}")
    print(f"🤖 LLM: Groq ({settings.LLM_MODEL})")
    
    # Initialize services
    from src.services.qdrant_service import QdrantService
    from src.services.llm_service import PortkeyLLMService
    from src.services.embedding_service import get_embedding_service
    from src.services.postgres_service import get_postgres_client
    
    app.state.qdrant = QdrantService()
    await app.state.qdrant.initialize()
    
    # Initialize PostgreSQL (runs migrations)
    print("📊 Initializing PostgreSQL...")
    await get_postgres_client()
    print("✅ PostgreSQL ready")
    
    app.state.llm = PortkeyLLMService()
    
    # Initialize embedding service
    print("📊 Pre-loading embedding model...")
    app.state.embedding = get_embedding_service()
    # Force model load
    _ = app.state.embedding.embed_text("warmup")
    print("✅ Embedding model loaded")
    
    # Log LLM service status
    if app.state.llm._portkey_available:
        print(f"🚀 Portkey AI Gateway: CONNECTED")
        print(f"   Config ID: {app.state.llm.portkey_config_id}")
    else:
        print(f"⚠️ Portkey: Not configured, using direct Groq API")
    
    # Load commanders from CSV
    from src.services.commander_service import load_commanders
    load_commanders()
    print("👮 Commanders loaded from CSV")
    
    yield
    
    # Shutdown
    print("👋 Shutting down ResQ AI...")


app = FastAPI(
    title="ResQ AI",
    description="Emergency Response Agentic RAG System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(incidents.router, prefix="/api/incidents", tags=["Incidents"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(media.router, prefix="/api", tags=["Media"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(dispatcher.router, prefix="/api/dispatcher", tags=["Dispatcher"])
app.include_router(commander.router, prefix="/api/commander", tags=["Commander"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
    }
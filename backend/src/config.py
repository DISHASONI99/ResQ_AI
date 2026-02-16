"""
Application Configuration - Pydantic Settings
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "ResQ AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False)
    APP_ENV: str = Field(default="development")
    
    # Qdrant Cloud
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str = Field(default="")
    
    # Groq LLM
    GROQ_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="llama-3.3-70b-versatile")
    LLM_FALLBACK_MODEL: str = Field(default="llama-3.1-8b-instant")
    LLM_TEMPERATURE: float = Field(default=0.3)
    LLM_MAX_TOKENS: int = Field(default=2048)
    
    # Portkey AI Gateway - Multi-tier configs
    PORTKEY_API_KEY: str = Field(default="")
    PORTKEY_CONFIG_ID: str = Field(default="")  # Default/fallback config
    PORTKEY_CONFIG_FAST: str = Field(default="")  # 8B models (Supervisor, Geo, Protocol, Vision)
    PORTKEY_CONFIG_MEDIUM: str = Field(default="")  # 32B models (Triage)
    PORTKEY_CONFIG_HEAVY: str = Field(default="")  # 70B models (Reflector)
    
    # Agent Mode: "prod" (multi-agent workflow) or "test" (single LLM call)
    AGENT_MODE: str = Field(default="prod")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    
    # PostgreSQL
    POSTGRES_URL: str = Field(default="postgresql://resq:resq@localhost:5432/resq")
    
    # Embeddings
    TEXT_EMBEDDING_MODEL: str = Field(default="BAAI/bge-base-en-v1.5")
    IMAGE_EMBEDDING_MODEL: str = Field(default="openai/clip-vit-base-patch32")
    
    # Audio
    WHISPER_MODEL: str = Field(default="base")
    
    # Agents
    MAX_REFLECTION_LOOPS: int = Field(default=2)
    HITL_ENABLED: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()

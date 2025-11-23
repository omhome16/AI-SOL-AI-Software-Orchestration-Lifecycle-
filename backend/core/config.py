"""
Configuration management for AI-SOL backend.
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Central configuration class for AI-SOL"""
    
    # API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # Model Configuration
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "google")
    MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.5-pro")  # For agents
    ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "models/gemini-2.5-pro")  # For intent classification
    EMBEDDING_MODEL = "models/embedding-001"  # Google's embedding model
    
    # LLM Parameters
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    WORKSPACE_DIR = BASE_DIR / "workspace"
    CHROMA_DB_DIR = BASE_DIR / "chroma_db"
    STATE_DIR = BASE_DIR / "project_states"
    CONVERSATIONS_DIR = BASE_DIR / "conversations"
    
    # Ensure directories exist
    WORKSPACE_DIR.mkdir(exist_ok=True)
    CHROMA_DB_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    
    # Server Configuration
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8003"))
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    
    # Workflow Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "2"))
    
    # Feature Flags
    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"
    ENABLE_WEBSOCKET_EVENTS = os.getenv("ENABLE_WEBSOCKET_EVENTS", "true").lower() == "true"
    ENABLE_PROACTIVE_NOTIFICATIONS = os.getenv("ENABLE_PROACTIVE_NOTIFICATIONS", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        return True
    
    @classmethod
    def get_agent_llm_config(cls) -> dict:
        """Get LLM configuration for agents"""
        return {
            "model": cls.MODEL_NAME,
            "temperature": cls.DEFAULT_TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS,
            "google_api_key": cls.GOOGLE_API_KEY
        }
    
    @classmethod
    def get_orchestrator_llm_config(cls) -> dict:
        """Get LLM configuration for orchestrator (faster model)"""
        return {
            "model": cls.ORCHESTRATOR_MODEL,
            "temperature": 0.3,  # Lower temperature for classification
            "max_tokens": 2048,  # Smaller responses for intent classification
            "google_api_key": cls.GOOGLE_API_KEY
        }

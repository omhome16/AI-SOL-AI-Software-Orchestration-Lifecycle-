from fastapi import APIRouter
from backend.core.state_manager import StateManager
from backend.core.config import Config

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    state_manager = StateManager()
    return {
        "status": "healthy",
        "service": "AI-SOL Backend",
        "version": "2.0.0",
        "projects_count": len(state_manager.projects)
    }

@router.get("/config")
async def get_config():
    """Get system configuration."""
    return {
        "model_provider": Config.MODEL_PROVIDER,
        "model_name": Config.MODEL_NAME,
        "features": {
            "web_search": Config.ENABLE_WEB_SEARCH,
            "code_analysis": Config.ENABLE_CODE_ANALYSIS
        }
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import sys
from pathlib import Path

# Add project root to python path to allow imports from agents/core/etc
sys.path.append(str(Path(__file__).parent.parent))
# Add backend directory to python path to allow imports of core, agents, etc.
sys.path.append(str(Path(__file__).parent))

from backend.api import websocket
from backend.api.routers import projects, files, workflow, health, configuration, export, templates
from backend.api.error_handler import register_exception_handlers
from backend.core.config import Config
from backend.utils.websocket_broadcaster import setup_websocket_broadcaster
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-SOL Backend",
    description="Backend for AI Software Orchestration Lifecycle",
    version="2.0.0"
)

# Register Exception Handlers
register_exception_handlers(app)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for workspace (generated files and images)
workspace_path = Path(Config.WORKSPACE_DIR)
workspace_path.mkdir(parents=True, exist_ok=True)
app.mount("/workspace", StaticFiles(directory=str(workspace_path)), name="workspace")

# Include Routers
# API v1 prefix
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(files.router, prefix="/api/v1", tags=["Files"])
app.include_router(workflow.router, prefix="/api/v1", tags=["Workflow"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(configuration.router, prefix="/api/v1", tags=["Configuration"])
app.include_router(export.router, prefix="/api/v1", tags=["Export"])
app.include_router(templates.router, prefix="/api/v1", tags=["Templates"])

app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

# Setup WebSocket event broadcaster on startup
@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket event broadcasting on app startup"""
    setup_websocket_broadcaster(websocket.manager)
    logger.info("WebSocket event broadcasting initialized")
    logger.info(f"AI-SOL Backend v2.0.0 started on port {Config.PORT}")

@app.get("/")
async def root():
    return {"message": "AI-SOL Backend is running", "status": "active"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

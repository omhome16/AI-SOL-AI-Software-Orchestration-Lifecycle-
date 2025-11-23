"""
Simple fix to make chromadb import optional in project_service.py
"""

# Find the line with: from backend.core.context_store import ProjectContextStore
# Replace the import section in process_chat_message with:

try:
    from backend.core.context_store import ProjectContextStore
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    ProjectContextStore = None

# Then in the function, replace:
# context_store = ProjectContextStore()
# with:
# context_store = ProjectContextStore() if CHROMADB_AVAILABLE else None

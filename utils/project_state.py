from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
from pathlib import Path
from enum import Enum

class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Stage(BaseModel):
    name: str
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    agent_output: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)

class ProjectState(BaseModel):
    project_id: str
    project_name: str
    requirements: str
    current_stage: str = "requirements"
    stage_status: Dict[str, Stage] = Field(default_factory=dict)
    overall_status: StageStatus = StageStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    errors: List[Dict[str, Any]] = Field(default_factory=list)

    def get_completed_stages(self) -> List[str]:
        return [name for name, stage in self.stage_status.items() if stage.status == StageStatus.COMPLETED]

class ProjectStateManager:
    def __init__(self, base_dir: str = "./workspace/.state"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}_state.json"

    def save_project_state(self, state: ProjectState):
        state.updated_at = datetime.now().isoformat()
        with open(self._get_state_path(state.project_id), "w") as f:
            json.dump(state.dict(), f, indent=2)

    def load_project_state(self, project_id: str) -> Optional[ProjectState]:
        state_path = self._get_state_path(project_id)
        if state_path.exists():
            with open(state_path, "r") as f:
                data = json.load(f)
                # Ensure stage_status is loaded correctly as Stage objects
                if "stage_status" in data:
                    data["stage_status"] = {k: Stage(**v) for k, v in data["stage_status"].items()}
                return ProjectState(**data)
        return None

    def create_initial_state(self, project_id: str, project_name: str, requirements: str) -> ProjectState:
        state = ProjectState(
            project_id=project_id,
            project_name=project_name,
            requirements=requirements,
            stage_status={
                "requirements": Stage(name="requirements"),
                "architecture": Stage(name="architecture"),
                "development": Stage(name="development"),
                "qa": Stage(name="qa"),
                "devops": Stage(name="devops")
            }
        )
        self.save_project_state(state)
        return state

    def update_stage_status(self, project_id: str, stage_name: str, status: StageStatus, 
                           agent_output: Dict[str, Any] = None, errors: List[str] = None) -> bool:
        state = self.load_project_state(project_id)
        if not state:
            return False

        if stage_name not in state.stage_status:
            state.stage_status[stage_name] = Stage(name=stage_name)

        stage = state.stage_status[stage_name]
        stage.status = status
        stage.agent_output = agent_output or {}
        stage.errors = errors or []

        now = datetime.now().isoformat()
        if status == StageStatus.IN_PROGRESS and not stage.start_time:
            stage.start_time = now
        elif status in [StageStatus.COMPLETED, StageStatus.FAILED] and not stage.end_time:
            stage.end_time = now

        # Update overall project status
        self._update_overall_status(state)
        self.save_project_state(state)
        return True

    def _update_overall_status(self, state: ProjectState):
        all_stages_completed = all(s.status == StageStatus.COMPLETED for s in state.stage_status.values())
        any_stage_failed = any(s.status == StageStatus.FAILED for s in state.stage_status.values())

        if all_stages_completed:
            state.overall_status = StageStatus.COMPLETED
        elif any_stage_failed:
            state.overall_status = StageStatus.FAILED
        else:
            state.overall_status = StageStatus.IN_PROGRESS

    def add_error(self, project_id: str, agent_name: str, error_message: str, details: Dict[str, Any] = None):
        state = self.load_project_state(project_id)
        if state:
            state.errors.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "error_message": error_message,
                "details": details or {}
            })
            self.save_project_state(state)
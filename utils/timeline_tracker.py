from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

class Milestone(BaseModel):
    name: str
    timestamp: str
    description: Optional[str] = None

class StageProgress(BaseModel):
    name: str
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration: Optional[str] = None
    actual_duration: Optional[str] = None
    milestones: List[Milestone] = Field(default_factory=list)

class ProjectTimeline(BaseModel):
    project_id: str
    stages: List[StageProgress] = Field(default_factory=list)
    overall_progress: float = Field(default=0.0, ge=0.0, le=100.0)
    estimated_completion: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TimelineManager:
    def __init__(self, base_dir: str = "./workspace/.timelines"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tz = ZoneInfo("Asia/Kolkata")

    def _get_timeline_path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}_timeline.json"

    def save_timeline(self, timeline: ProjectTimeline):
        timeline.updated_at = datetime.now(self.tz).isoformat()
        with open(self._get_timeline_path(timeline.project_id), "w") as f:
            # Use model_dump for Pydantic v2
            data = timeline.model_dump() if hasattr(timeline, 'model_dump') else timeline.dict()
            json.dump(data, f, indent=2)

    def load_timeline(self, project_id: str) -> Optional[ProjectTimeline]:
        timeline_path = self._get_timeline_path(project_id)
        if timeline_path.exists():
            with open(timeline_path, "r") as f:
                data = json.load(f)
                # Ensure stages are loaded correctly as StageProgress objects
                if "stages" in data:
                    data["stages"] = [StageProgress(**s) for s in data["stages"]]
                return ProjectTimeline(**data)
        return None

    def create_timeline(self, project_id: str) -> ProjectTimeline:
        now = datetime.now(self.tz).isoformat()
        timeline = ProjectTimeline(
            project_id=project_id,
            stages=[
                StageProgress(name="requirements", status="pending"),
                StageProgress(name="architecture", status="pending"),
                StageProgress(name="development", status="pending"),
                StageProgress(name="qa", status="pending"),
                StageProgress(name="devops", status="pending")
            ],
            created_at=now,
            updated_at=now
        )
        self.save_timeline(timeline)
        return timeline

    def update_stage_progress(self, project_id: str, stage_name: str, 
                              progress_percentage: float, milestone: Optional[str] = None) -> bool:
        timeline = self.load_timeline(project_id)
        if not timeline:
            return False

        for stage in timeline.stages:
            if stage.name == stage_name:
                stage.progress = progress_percentage
                if progress_percentage == 0 and stage.status == "pending":
                    stage.status = "pending"
                elif progress_percentage > 0 and stage.status == "pending":
                    stage.status = "in_progress"
                    stage.started_at = datetime.now(self.tz).isoformat()
                elif progress_percentage == 100 and stage.status != "completed":
                    stage.status = "completed"
                    stage.completed_at = datetime.now(self.tz).isoformat()
                elif progress_percentage < 100 and stage.status == "completed":
                    stage.status = "in_progress" # Re-opened

                if milestone:
                    stage.milestones.append(Milestone(name=milestone, timestamp=datetime.now(self.tz).isoformat()))
                break
        
        self._update_overall_progress(timeline)
        self.save_timeline(timeline)
        return True

    def _update_overall_progress(self, timeline: ProjectTimeline):
        total_progress = sum(stage.progress for stage in timeline.stages)
        timeline.overall_progress = total_progress / len(timeline.stages)

        # Estimate completion date (very basic, can be improved)
        if timeline.overall_progress > 0 and timeline.overall_progress < 100:
            elapsed_time = datetime.now(self.tz) - datetime.fromisoformat(timeline.created_at)
            remaining_progress = 100 - timeline.overall_progress
            if timeline.overall_progress > 0:
                estimated_total_time = elapsed_time / (timeline.overall_progress / 100)
                estimated_remaining_time = estimated_total_time - elapsed_time
                timeline.estimated_completion = (datetime.now(self.tz) + estimated_remaining_time).isoformat()
        elif timeline.overall_progress == 100:
            timeline.estimated_completion = timeline.updated_at
        else:
            timeline.estimated_completion = None
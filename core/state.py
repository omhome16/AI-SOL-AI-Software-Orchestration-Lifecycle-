
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime
from zoneinfo import ZoneInfo
import operator

tz = ZoneInfo("Asia/Kolkata")

class AgentOutput(TypedDict):
    """Output from a single agent"""
    agent_name: str
    success: bool
    data: Dict[str, Any]
    artifacts: List[Dict[str, str]]  # Generated files/docs
    errors: List[str]
    timestamp: str


class WorkflowState(TypedDict):

    # Core identifiers
    task_id: str
    project_name: str
    workspace_path: str

    # User inputs
    requirements: str
    user_context: Dict[str, Any]

    # Workflow control
    current_step: str
    next_step: Optional[str]
    steps_completed: Annotated[List[str], operator.add]

    # Agent outputs (accumulated)
    requirements_output: Optional[AgentOutput]
    architecture_output: Optional[AgentOutput]
    developer_output: Optional[AgentOutput]
    qa_output: Optional[AgentOutput]
    devops_output: Optional[AgentOutput]

    # All generated files tracked here
    generated_files: Annotated[List[str], operator.add]

    # Human interaction
    requires_human_input: bool
    human_interrupt_message: Optional[str]
    human_response: Optional[str]

    # Error handling
    errors: Annotated[List[Dict[str, Any]], operator.add]
    retry_count: Dict[str, int]  # Per-agent retry counter

    # Metadata/time
    started_at: str
    updated_at: str


def create_initial_state(
        task_id: str,
        project_name: str,
        requirements: str,
        workspace_path: str,
        user_context: Dict[str, Any] = None
) -> WorkflowState:

    now = datetime.now(tz).isoformat()

    return WorkflowState(
        task_id=task_id,
        project_name=project_name,
        workspace_path=workspace_path,
        requirements=requirements,
        user_context=user_context or {},
        current_step="start",
        next_step="requirements",
        steps_completed=[],
        requirements_output=None,
        architecture_output=None,
        developer_output=None,
        qa_output=None,
        devops_output=None,
        generated_files=[],
        requires_human_input=False,
        human_interrupt_message=None,
        human_response=None,
        errors=[],
        retry_count={},
        started_at=now,
        updated_at=now
    )


def update_state(
        state: WorkflowState,
        **updates
) -> WorkflowState:
    """Update state with new values"""
    state["updated_at"] = datetime.now(tz).isoformat()

    for key, value in updates.items():
        if key in state:
            state[key] = value

    return state
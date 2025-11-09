from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime
import operator
from enum import Enum
from zoneinfo import ZoneInfo

tz = ZoneInfo("Asia/Kolkata")

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentOutput(TypedDict):
    """Standardized agent output"""
    agent_name: str
    success: bool
    data: Dict[str, Any]
    documents: List[Dict[str, str]]  # Generated documents
    artifacts: List[str]  # File paths
    errors: List[str]
    timestamp: str


class WorkflowState(TypedDict):
    def get_task_status(self) -> TaskStatus:
        """Get the current task status."""
        return self["status"]

    def get_current_step(self) -> str:
        """Get the current step."""
        return self["current_step"]

    # Identifiers
    task_id: str
    project_name: str
    workspace_path: str

    # Inputs
    requirements: str
    user_context: Dict[str, Any]

    # Workflow control
    current_step: str
    steps_completed: Annotated[List[str], operator.add]
    status: TaskStatus

    # Central orchestrator memory
    orchestrator_thoughts: Annotated[List[Dict[str, Any]], operator.add]  # ReAct reasoning
    web_search_results: Dict[str, Any]  # Cached search results

    # Agent outputs
    requirements_output: Optional[AgentOutput]
    architecture_output: Optional[AgentOutput]
    developer_output: Optional[AgentOutput]
    qa_output: Optional[AgentOutput]
    devops_output: Optional[AgentOutput]

    # Generated artifacts
    generated_files: Annotated[List[str], operator.add]
    generated_documents: Annotated[List[Dict[str, str]], operator.add]

    # Code quality tracking
    code_quality_score: float  # 0-100
    security_issues: List[Dict[str, Any]]
    test_coverage: float  # 0-100

    # GitHub integration
    github_repo_url: Optional[str]
    github_commit_sha: Optional[str]

    # Human interaction
    requires_human_input: bool
    human_prompt: Optional[str]
    human_response: Optional[str]

    # Vector memory (for self-improvement)
    similar_projects: List[str]  # Similar past projects
    learned_patterns: List[Dict[str, Any]]  # Successful patterns

    # Error handling
    errors: Annotated[List[Dict[str, Any]], operator.add]
    retry_count: Dict[str, int]

    # Metadata
    created_at: str
    updated_at: str
    completed_at: Optional[str]


def create_initial_state(
        task_id: str,
        project_name: str,
        requirements: str,
        workspace_path: str = "./workspace",
        user_context: Dict[str, Any] = None
) -> WorkflowState:
    """Initialize workflow state"""

    now = datetime.now(tz).isoformat()

    return WorkflowState(
        task_id=task_id,
        project_name=project_name,
        workspace_path=workspace_path,
        requirements=requirements,
        user_context=user_context or {},
        current_step="initialize",
        steps_completed=[],
        status=TaskStatus.PENDING,
        orchestrator_thoughts=[],
        web_search_results={},
        requirements_output=None,
        architecture_output=None,
        developer_output=None,
        qa_output=None,
        devops_output=None,
        generated_files=[],
        generated_documents=[],
        code_quality_score=0.0,
        security_issues=[],
        test_coverage=0.0,
        github_repo_url=None,
        github_commit_sha=None,
        requires_human_input=False,
        human_prompt=None,
        human_response=None,
        similar_projects=[],
        learned_patterns=[],
        errors=[],
        retry_count={},
        created_at=now,
        updated_at=now,
        completed_at=None
    )


def record_thought(
        state: WorkflowState,
        thought: str,
        action: str,
        observation: str = ""
) -> WorkflowState:
    """Record ReAct loop thought"""
    # Normalize values to strings to avoid nested objects in orchestrator_thoughts
    thought_text = str(thought) if thought is not None else ""
    action_text = str(action) if action is not None else ""
    observation_text = str(observation) if observation is not None else ""

    entry = {
        "thought": thought_text,
        "action": action_text,
        "observation": observation_text,
        "timestamp": datetime.now(tz).isoformat()
    }

    state["orchestrator_thoughts"].append(entry)
    state["updated_at"] = datetime.now(tz).isoformat()
    return state


def update_quality_metrics(
        state: WorkflowState,
        code_quality: float = None,
        test_coverage: float = None,
        security_issues: List[Dict[str, Any]] = None
) -> WorkflowState:
    """Update quality metrics"""
    if code_quality is not None:
        state["code_quality_score"] = code_quality
    if test_coverage is not None:
        state["test_coverage"] = test_coverage
    if security_issues is not None:
        # Ensure we extend with normalized list entries
        for s in security_issues:
            state["security_issues"].append(s)

    state["updated_at"] = datetime.now(tz).isoformat()
    return state

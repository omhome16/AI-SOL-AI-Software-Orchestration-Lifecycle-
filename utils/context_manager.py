from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
from pathlib import Path

from .project_classifier import ProjectType, ComplexityLevel


class FunctionalRequirement(BaseModel):
    id: str = Field(description="Unique identifier for the requirement")
    description: str = Field(description="Detailed description of the functional requirement")
    priority: str = Field(description="Priority of the requirement (e.g., high, medium, low)")
    acceptance_criteria: List[str] = Field(description="List of acceptance criteria for the requirement")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "acceptance_criteria": self.acceptance_criteria
        }


class NonFunctionalRequirement(BaseModel):
    category: str = Field(description="Category of the non-functional requirement (e.g., performance, security)")
    description: str = Field(description="Detailed description of the non-functional requirement")
    metrics: List[str] = Field(description="Measurable metrics for the non-functional requirement")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "description": self.description,
            "metrics": self.metrics
        }


class TechnologyStack(BaseModel):
    backend: List[str] = Field(default_factory=list, description="List of backend technologies used")
    frontend: List[str] = Field(default_factory=list, description="List of frontend technologies used")
    database: List[str] = Field(default_factory=list, description="List of database technologies used")
    devops: List[str] = Field(default_factory=list, description="List of DevOps tools and practices used")

    def to_dict(self):
        return {
            "backend": self.backend,
            "frontend": self.frontend,
            "database": self.database,
            "devops": self.devops
        }


class ComponentSpecification(BaseModel):
    name: str = Field(description="Name of the component")
    description: str = Field(description="Description of the component's role and responsibilities")
    technologies: List[str] = Field(default_factory=list, description="Technologies used in this component")
    interfaces: List[str] = Field(default_factory=list, description="APIs or communication methods")
    dependencies: List[str] = Field(default_factory=list, description="Other components or services it depends on")


class FileTask(BaseModel):
    path: str = Field(..., description="The full relative path to the file (e.g., 'src/models/user_model.py')")
    purpose: str = Field(..., description="A clear, LLM-generated one-sentence purpose for this file.")
    dependencies: List[str] = Field(default_factory=list, description="A list of other file paths in the plan that this file must import or depend on.")


class ProjectBlueprint(BaseModel):
    explanation: str = Field(..., description="A brief explanation of the chosen architecture and technology stack.")
    folder_structure: List[str] = Field(default_factory=list, description="A list of all directories to be created, e.g., ['src/models', 'src/services']")
    build_plan: List[FileTask] = Field(default_factory=list, description="The complete, dependency-sorted list of all files to be generated.")


class AgentContext(BaseModel):
    """
    Central context object that stores all project information and is passed between agents.
    """
    # Core project information
    project_id: str = Field(description="Unique identifier for the project")
    project_name: str = Field(description="Name of the project")
    requirements: str = Field(description="Original user requirements")
    project_type: ProjectType = Field(description="Classified project type")
    complexity_level: ComplexityLevel = Field(description="Classified complexity level")
    
    # Requirements and specifications
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    technology_stack: TechnologyStack = Field(default_factory=TechnologyStack)
    
    # Architecture
    architecture_pattern: Optional[str] = Field(default=None)
    component_specifications: List[ComponentSpecification] = Field(default_factory=list)
    data_models: List[Dict[str, Any]] = Field(default_factory=list)
    blueprint: Optional[ProjectBlueprint] = Field(default=None, description="Project blueprint from architect")
    
    # Generated artifacts
    generated_files: List[str] = Field(default_factory=list)
    
    # Testing and quality
    test_results: Dict[str, Any] = Field(default_factory=dict)
    test_coverage: float = Field(default=0.0)
    security_report: Dict[str, Any] = Field(default_factory=dict)
    
    # Deployment
    deployment_strategy: Optional[str] = Field(default=None)
    
    # Domain information
    domain: Optional[str] = Field(default=None)
    
    # Project filesystem
    project_root: Optional[str] = Field(default='.', description="Filesystem path used as project root for generated files")
    
    # Timeline
    estimated_timeline: Optional[str] = Field(default=None, description="Estimated project timeline")
    
    # User context and modifications
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User-provided configuration and context")
    modification_context: Dict[str, Any] = Field(default_factory=dict, description="User modification requests by agent")
    
    # Timestamps
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        arbitrary_types_allowed = True


class ContextManager:
    def __init__(self, base_dir: str = "./workspace/.context"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_context_path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}_context.json"

    def save_context(self, project_id: str, context: AgentContext):
        context.updated_at = datetime.now().isoformat()
        # Build a safe serializable dict without invoking pydantic's internal
        # validation/serialization (which can emit enum-related warnings).
        def _serialize_value(v):
            # Enums
            if hasattr(v, 'value'):
                return v.value
            # Pydantic models
            if isinstance(v, BaseModel):
                return _serialize_model(v)
            # Lists / tuples
            if isinstance(v, (list, tuple)):
                return [_serialize_value(x) for x in v]
            # Dicts
            if isinstance(v, dict):
                return {k: _serialize_value(val) for k, val in v.items()}
            # Path, datetime, etc.
            try:
                json.dumps(v)
                return v
            except Exception:
                return str(v)

        def _serialize_model(m: BaseModel):
            out = {}
            for name, field in m.__fields__.items():
                val = getattr(m, name, None)
                out[name] = _serialize_value(val)
            return out

        data = _serialize_model(context)
        with open(self._get_context_path(project_id), "w") as f:
            json.dump(data, f, indent=2)

    def load_context(self, project_id: str) -> Optional[AgentContext]:
        context_path = self._get_context_path(project_id)
        if context_path.exists():
            with open(context_path, "r") as f:
                data = json.load(f)
                # Be tolerant: if complexity_level was saved as a string,
                # coerce it back to the ComplexityLevel enum to avoid
                # pydantic enum validation warnings elsewhere.
                if 'complexity_level' in data and isinstance(data['complexity_level'], str):
                    try:
                        data['complexity_level'] = ComplexityLevel(data['complexity_level'])
                    except Exception:
                        # leave as-is; AgentContext will validate/convert if possible
                        pass
                return AgentContext(**data)
        return None

    def create_initial_context(self, project_id: str, project_name: str, requirements: str,
                               project_type: ProjectType) -> AgentContext:
        context = AgentContext(
            project_id=project_id,
            project_name=project_name,
            requirements=requirements,
            project_type=project_type,
            complexity_level=ComplexityLevel.MEDIUM,  # Default, can be updated later
            domain="general"  # Default, can be updated later
        )
        self.save_context(project_id, context)
        return context

    def update_context(self, project_id: str, updates: Dict[str, Any]):
        context = self.load_context(project_id)
        if context:
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
            self.save_context(project_id, context)

    def get_requirements_context(self, project_id: str) -> Dict[str, Any]:
        context = self.load_context(project_id)
        if context:
            return {
                "project_type": context.project_type.value,
                "complexity_level": context.complexity_level.value,
                "requirements": context.requirements
            }
        return {}

    def get_architecture_context(self, project_id: str) -> Dict[str, Any]:
        context = self.load_context(project_id)
        if context:
            return {
                "project_type": context.project_type.value,
                "complexity_level": context.complexity_level.value,
                "functional_requirements": [req.dict() for req in context.functional_requirements],
                "non_functional_requirements": [nfr.dict() for nfr in context.non_functional_requirements],
                "technology_stack": context.technology_stack.to_dict()
            }
        return {}

    def get_development_context(self, project_id: str) -> Dict[str, Any]:
        context = self.load_context(project_id)
        if context:
            return {
                "project_type": context.project_type.value,
                "complexity_level": context.complexity_level.value,
                "functional_requirements": [req.dict() for req in context.functional_requirements],
                "technology_stack": context.technology_stack.to_dict(),
                "architecture_pattern": context.architecture_pattern,
                "component_specifications": [comp.dict() for comp in context.component_specifications],
                "data_models": context.data_models
            }
        return {}

    def get_qa_context(self, project_id: str) -> Dict[str, Any]:
        context = self.load_context(project_id)
        if context:
            return {
                "project_type": context.project_type.value,
                "complexity_level": context.complexity_level.value,
                "functional_requirements": [req.dict() for req in context.functional_requirements],
                "technology_stack": context.technology_stack.to_dict(),
                "architecture_pattern": context.architecture_pattern,
                "generated_files": context.generated_files,
                "data_models": context.data_models,
                "component_specifications": [comp.dict() for comp in context.component_specifications]
            }
        return {}

    def get_devops_context(self, project_id: str) -> Dict[str, Any]:
        context = self.load_context(project_id)
        if context:
            return {
                "project_type": context.project_type.value,
                "complexity_level": context.complexity_level.value,
                "technology_stack": context.technology_stack.to_dict(),
                "architecture_pattern": context.architecture_pattern,
                "generated_files": context.generated_files,
                "test_results": context.test_results,
                "security_report": context.security_report
            }
        return {}
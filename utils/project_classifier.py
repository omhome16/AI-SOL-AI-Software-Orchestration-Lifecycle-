from typing import Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field

class ProjectType(str, Enum):
    WEB_APPLICATION = "web_application"
    BACKEND_API = "backend_api"
    MOBILE_APP = "mobile_app"
    FULL_STACK = "full_stack"
    CLI_TOOL = "cli_tool"
    OTHER = "other"

class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class ProjectClassification(BaseModel):
    project_type: ProjectType = Field(description="Classified type of the project")
    complexity: ComplexityLevel = Field(description="Estimated complexity of the project")
    domain: str = Field(description="Identified domain of the project (e.g., e-commerce, healthcare)")
    estimated_duration_hours: int = Field(description="Estimated development duration in hours")
    team_size_recommendation: str = Field(description="Recommended team size for the project")

class ProjectClassifier:
    def __init__(self):
        pass

    def classify_project(self, requirements: str) -> ProjectClassification:
        # This is a placeholder for a more sophisticated LLM-based classification
        # For now, it uses simple keyword matching
        requirements_lower = requirements.lower()

        project_type = ProjectType.OTHER
        if "web application" in requirements_lower or "website" in requirements_lower or "frontend" in requirements_lower:
            project_type = ProjectType.WEB_APPLICATION
        elif "api" in requirements_lower or "backend" in requirements_lower or "microservice" in requirements_lower:
            project_type = ProjectType.BACKEND_API
        elif "mobile app" in requirements_lower or "ios" in requirements_lower or "android" in requirements_lower:
            project_type = ProjectType.MOBILE_APP
        elif "full stack" in requirements_lower or ("frontend" in requirements_lower and "backend" in requirements_lower):
            project_type = ProjectType.FULL_STACK
        elif "cli" in requirements_lower or "command line" in requirements_lower or "tool" in requirements_lower:
            project_type = ProjectType.CLI_TOOL

        complexity = ComplexityLevel.MEDIUM
        if "simple" in requirements_lower or "basic" in requirements_lower:
            complexity = ComplexityLevel.LOW
        elif "complex" in requirements_lower or "high performance" in requirements_lower or "scalable" in requirements_lower:
            complexity = ComplexityLevel.HIGH

        domain = "general"
        if "e-commerce" in requirements_lower or "shop" in requirements_lower or "store" in requirements_lower:
            domain = "e-commerce"
        elif "healthcare" in requirements_lower or "medical" in requirements_lower or "patient" in requirements_lower:
            domain = "healthcare"
        elif "finance" in requirements_lower or "banking" in requirements_lower or "transaction" in requirements_lower:
            domain = "finance"
        elif "game" in requirements_lower or "gaming" in requirements_lower:
            domain = "gaming"
        elif "education" in requirements_lower or "learning" in requirements_lower or "student" in requirements_lower:
            domain = "education"

        estimated_duration_hours = 40 # Default to 1 week
        team_size_recommendation = "1-2 developers"

        if complexity == ComplexityLevel.LOW:
            estimated_duration_hours = 20
            team_size_recommendation = "1 developer"
        elif complexity == ComplexityLevel.MEDIUM:
            estimated_duration_hours = 80
            team_size_recommendation = "2-3 developers"
        elif complexity == ComplexityLevel.HIGH:
            estimated_duration_hours = 240
            team_size_recommendation = "3-5 developers"
        elif complexity == ComplexityLevel.VERY_HIGH:
            estimated_duration_hours = 480
            team_size_recommendation = "5+ developers"

        return ProjectClassification(
            project_type=project_type,
            complexity=complexity,
            domain=domain,
            estimated_duration_hours=estimated_duration_hours,
            team_size_recommendation=team_size_recommendation
        )
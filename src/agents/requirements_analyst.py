"""
Requirements Analyst Agent - Analyzes and structures software requirements
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import structlog
from datetime import datetime
from zoneinfo import ZoneInfo

logger = structlog.get_logger()


class RequirementAnalysis(BaseModel):
    """Structured output for requirement analysis"""
    functional_requirements: List[str] = Field(description="List of functional requirements")
    non_functional_requirements: List[str] = Field(description="List of non-functional requirements")
    acceptance_criteria: List[str] = Field(description="Acceptance criteria in Given-When-Then format")
    assumptions: List[str] = Field(description="Assumptions that need validation")
    risks: List[str] = Field(description="Identified risks and challenges")
    questions: List[str] = Field(description="Clarifying questions for stakeholders")
    estimated_complexity: str = Field(description="Complexity level: low, medium, high, or complex")


class RequirementsAnalystAgent:
    """Agent responsible for analyzing and structuring requirements"""

    def __init__(self, api_key: str):
        self.name = "requirements_analyst"
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            temperature=0.1,
            max_tokens=4000
        )
        self.parser = JsonOutputParser(pydantic_object=RequirementAnalysis)
        self.setup_chain()
        self.tz = ZoneInfo("Asia/Kolkata")

    def setup_chain(self):
        """Setup the LangChain processing chain"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Business Analyst and Requirements Engineer with 15+ years of experience.

Your role is to analyze user requirements and convert them into structured, actionable technical specifications.

Follow these principles:
1. Extract clear, testable functional requirements
2. Identify non-functional requirements (performance, security, usability, scalability)
3. Generate comprehensive acceptance criteria using Given-When-Then format
4. Identify assumptions that need validation
5. Flag potential risks and challenges
6. Ask clarifying questions for ambiguous areas
7. Provide realistic complexity estimation

Complexity Levels:
- low: Simple CRUD operations, basic UI, standard patterns
- medium: Multiple integrations, moderate business logic, some complexity
- high: Complex business rules, multiple systems, scalability concerns
- complex: Distributed systems, high performance needs, advanced algorithms

{format_instructions}"""),
            ("human", """Analyze these requirements and provide structured analysis:

Requirements:
{requirements}

Context:
{context}

Provide a comprehensive analysis in the specified JSON format.""")
        ])

        self.chain = prompt | self.llm | self.parser

    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze requirements and return structured analysis"""

        if context is None:
            context = {}

        start_time = datetime.now(self.tz)

        try:
            logger.info("Starting requirements analysis", requirements_length=len(requirements))

            # Prepare context
            context_str = self._format_context(context)

            # Execute analysis (include format_instructions for parser)
            result = await self.chain.ainvoke({
                "requirements": requirements,
                "context": context_str,
                "format_instructions": self.parser.get_format_instructions()
            })

            # If parser returns a Pydantic model instance, convert to dict for uniform handling
            analysis_dict = result.dict() if hasattr(result, "dict") else result

            # Calculate execution time (in seconds)
            execution_time = (datetime.now(self.tz) - start_time).total_seconds()

            # Generate insights
            insights = self._generate_insights(analysis_dict)

            # Generate specification document
            spec_document = self._generate_specification(analysis_dict)

            logger.info("Requirements analysis completed", execution_time_seconds=execution_time)

            return {
                "success": True,
                "analysis": analysis_dict,
                "insights": insights,
                "specification_document": spec_document,
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now(self.tz).isoformat()
            }

        except Exception as e:
            logger.error("Requirements analysis failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(self.tz).isoformat()
            }

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information"""
        if not context:
            return "No additional context provided"

        parts = []
        # Keep context fields that are relevant to requirements; avoid embedding team-size specifics
        if "project_type" in context:
            parts.append(f"Project Type: {context['project_type']}")
        if "technology_preferences" in context:
            parts.append(f"Technology Preferences: {context['technology_preferences']}")
        if "constraints" in context:
            parts.append(f"Constraints: {context['constraints']}")
        if "target_users" in context:
            parts.append(f"Target Users: {context['target_users']}")

        return "\n".join(parts) if parts else "No specific context"

    def _generate_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about the requirements"""

        total_requirements = (
                len(analysis.get("functional_requirements", [])) +
                len(analysis.get("non_functional_requirements", []))
        )

        complexity_score = self._calculate_complexity_score(analysis)

        return {
            "requirements_coverage": {
                "functional": len(analysis.get("functional_requirements", [])),
                "non_functional": len(analysis.get("non_functional_requirements", [])),
                "total": total_requirements
            },
            "quality_indicators": {
                "has_acceptance_criteria": len(analysis.get("acceptance_criteria", [])) > 0,
                "risks_identified": len(analysis.get("risks", [])) > 0,
                "assumptions_documented": len(analysis.get("assumptions", [])) > 0,
                "questions_for_clarification": len(analysis.get("questions", [])) > 0
            },
            "complexity_score": complexity_score,
            "recommended_next_steps": self._get_next_steps(analysis)
        }

    def _calculate_complexity_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate numerical complexity score (0-10)"""

        score = 0.0

        # Base from requirements count
        total_reqs = (
                len(analysis.get("functional_requirements", [])) +
                len(analysis.get("non_functional_requirements", []))
        )
        score += min(total_reqs * 0.1, 3.0)

        # Complexity level
        complexity_weights = {"low": 1.0, "medium": 2.5, "high": 4.0, "complex": 5.0}
        score += complexity_weights.get(analysis.get("estimated_complexity", "medium"), 2.5)

        # Risk factor
        score += len(analysis.get("risks", [])) * 0.2

        # Questions factor
        score += len(analysis.get("questions", [])) * 0.1

        return min(score, 10.0)

    def _get_next_steps(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommended next steps"""

        steps = ["Proceed to system architecture design"]

        if analysis.get("questions"):
            steps.insert(0, "Clarify outstanding questions with stakeholders")

        if analysis.get("risks"):
            steps.append("Develop risk mitigation strategies")

        if analysis.get("estimated_complexity") in ["high", "complex"]:
            steps.append("Consider breaking down into smaller phases and delivering in increments")

        return steps

    def _generate_specification(self, analysis: Dict[str, Any]) -> str:
        """Generate requirements specification document"""

        now_ist = datetime.now(self.tz).isoformat()

        doc = f"""# Requirements Specification

## Functional Requirements
{self._format_list(analysis.get('functional_requirements', []))}

## Non-Functional Requirements
{self._format_list(analysis.get('non_functional_requirements', []))}

## Acceptance Criteria
{self._format_list(analysis.get('acceptance_criteria', []))}

## Assumptions
{self._format_list(analysis.get('assumptions', []))}

## Identified Risks
{self._format_list(analysis.get('risks', []))}

## Questions for Clarification
{self._format_list(analysis.get('questions', []))}

## Complexity Assessment
**Estimated Complexity**: {analysis.get('estimated_complexity', 'Unknown')}

---
*Generated by AISDAP Requirements Analyst Agent*
*Timestamp (IST): {now_ist}*
"""
        return doc

    def _format_list(self, items: List[str]) -> str:
        """Format list items for markdown"""
        if not items:
            return "- None identified"
        return "\n".join(f"- {item}" for item in items)


# Example usage
async def main():
    """Example usage of Requirements Analyst Agent"""

    agent = RequirementsAnalystAgent(api_key="your-anthropic-api-key")

    requirements = """
    Build a task management application that allows users to:
    - Create, update, and delete tasks
    - Assign tasks to team members
    - Set due dates and priorities
    - Track task progress
    - Receive notifications when tasks are due
    - Generate reports on team productivity

    The system should be accessible via web and mobile.
    It needs to support 1000+ concurrent users.
    """

    context = {
        "project_type": "Web Application",
        "technology_preferences": "Python backend, React frontend",
        "constraints": "6 month timeline, team of 5 developers",
        "target_users": "Small to medium businesses (50-500 employees)"
    }

    result = await agent.analyze(requirements, context)

    if result["success"]:
        print("Analysis successful!")
        print(f"\nComplexity: {result['analysis']['estimated_complexity']}")
        print(f"\nFunctional Requirements: {len(result['analysis']['functional_requirements'])}")
        print(f"\nSpecification Document:\n{result['specification_document']}")
    else:
        print(f"Analysis failed: {result['error']}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

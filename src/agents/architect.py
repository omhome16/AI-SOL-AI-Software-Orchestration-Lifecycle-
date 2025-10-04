"""
System Architect Agent - Designs system architecture and technology stack
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


class SystemArchitecture(BaseModel):
    """Structured output for system architecture"""
    architecture_pattern: str = Field(
        description="Architecture pattern: microservices, modular_monolith, serverless, or layered")
    components: List[Dict[str, str]] = Field(description="System components with name, responsibility, and technology")
    data_flow: List[Dict[str, str]] = Field(description="Data flow between components")
    technology_stack: Dict[str, List[str]] = Field(
        description="Technology stack for backend, frontend, database, infrastructure")
    database_design: Dict[str, Any] = Field(description="Database design details")
    api_design: Dict[str, Any] = Field(description="API design details")
    security_considerations: List[str] = Field(description="Security measures and considerations")
    scalability_strategy: List[str] = Field(description="Scalability approaches")
    deployment_strategy: str = Field(description="Deployment approach and strategy")


class ArchitectAgent:
    """Agent responsible for system architecture design"""

    def __init__(self, api_key: str):
        self.name = "architect"
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            temperature=0.1,
            max_tokens=4000
        )
        self.parser = JsonOutputParser(pydantic_object=SystemArchitecture)
        self.setup_chain()
        self.tz = ZoneInfo("Asia/Kolkata")

    def setup_chain(self):
        """Setup the LangChain processing chain"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior Software Architect with 15+ years of experience in:
- Distributed systems and microservices architecture
- Cloud-native architecture patterns
- Database design and optimization
- Security and scalability best practices
- Technology stack selection

Design comprehensive system architectures considering:
1. System complexity and scale requirements
2. Team size and expertise
3. Performance and scalability needs
4. Security and compliance requirements
5. Maintainability and extensibility
6. Cost optimization

Architecture Patterns:
- microservices: For large teams, complex domains, high scalability needs
- modular_monolith: For small-medium teams, well-defined domains, rapid development
- serverless: For event-driven workloads, variable traffic, cost optimization
- layered: For traditional applications, simple requirements

{format_instructions}"""),
            ("human", """Design a system architecture for these requirements:

Functional Requirements:
{functional_requirements}

Non-Functional Requirements:
{non_functional_requirements}

Complexity: {complexity}
Team Size: {team_size}

Context:
{context}

Provide a comprehensive architecture design in the specified JSON format.""")
        ])

        self.chain = prompt | self.llm | self.parser

    async def design(
            self,
            functional_requirements: List[str],
            non_functional_requirements: List[str],
            complexity: str = "medium",
            context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Design system architecture"""

        if context is None:
            context = {}

        start_time = datetime.now(self.tz)

        try:
            logger.info("Starting architecture design", complexity=complexity)

            # Prepare inputs
            team_size = context.get("team_size", "5-10 developers")
            context_str = self._format_context(context)

            # Execute design
            result = await self.chain.ainvoke({
                "functional_requirements": "\n".join(f"- {req}" for req in functional_requirements),
                "non_functional_requirements": "\n".join(f"- {req}" for req in non_functional_requirements),
                "complexity": complexity,
                "team_size": team_size,
                "context": context_str,
                "format_instructions": self.parser.get_format_instructions()
            })

            # Calculate execution time
            execution_time = (datetime.now(self.tz) - start_time).total_seconds()

            # Generate artifacts
            artifacts = self._generate_artifacts(result)

            # Assess implementation complexity
            implementation_assessment = self._assess_implementation(result)

            logger.info("Architecture design completed", execution_time_seconds=execution_time)

            return {
                "success": True,
                "architecture": result,
                "artifacts": artifacts,
                "implementation_assessment": implementation_assessment,
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now(self.tz).isoformat()
            }

        except Exception as e:
            logger.error("Architecture design failed", error=str(e))
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
        for key, value in context.items():
            if key != "team_size":  # Already handled separately
                parts.append(f"{key.replace('_', ' ').title()}: {value}")

        return "\n".join(parts) if parts else "No specific context"

    def _generate_artifacts(self, architecture: Dict[str, Any]) -> Dict[str, str]:
        """Generate architecture documentation artifacts"""

        return {
            "architecture_document": self._generate_architecture_doc(architecture),
            "component_diagram": self._generate_component_diagram(architecture),
            "database_schema": self._generate_database_schema(architecture),
            "api_specification": self._generate_api_spec(architecture)
        }

    def _generate_architecture_doc(self, arch: Dict[str, Any]) -> str:
        """Generate comprehensive architecture documentation"""

        doc = f"""# System Architecture Document

## Architecture Pattern
**Pattern**: {arch.get('architecture_pattern', 'Unknown')}

## System Components
"""
        for comp in arch.get('components', []):
            doc += f"""
### {comp.get('name', 'Unknown')}
- **Responsibility**: {comp.get('responsibility', 'N/A')}
- **Technology**: {comp.get('technology', 'N/A')}
"""

        doc += "\n## Technology Stack\n"
        for category, technologies in arch.get('technology_stack', {}).items():
            doc += f"- **{category.title()}**: {', '.join(technologies)}\n"

        doc += "\n## Data Flow\n"
        for flow in arch.get('data_flow', []):
            doc += f"- {flow.get('from', '?')} → {flow.get('to', '?')}: {flow.get('data', '?')} ({flow.get('method', '?')})\n"

        db_design = arch.get('database_design', {})
        doc += f"""
## Database Design
- **Type**: {db_design.get('type', 'Unknown')}
- **Primary Database**: {db_design.get('primary_database', 'Unknown')}
- **Key Entities**: {', '.join(db_design.get('key_entities', []))}

## API Design
- **Style**: {arch.get('api_design', {}).get('style', 'Unknown')}
- **Authentication**: {arch.get('api_design', {}).get('authentication', 'Unknown')}

## Security Considerations
"""
        for sec in arch.get('security_considerations', []):
            doc += f"- {sec}\n"

        doc += "\n## Scalability Strategy\n"
        for strat in arch.get('scalability_strategy', []):
            doc += f"- {strat}\n"

        doc += f"""
## Deployment Strategy
{arch.get('deployment_strategy', 'Not specified')}

---
*Generated by AI-SOL Architect Agent*
*Timestamp: {datetime.now(self.tz).isoformat()}*
"""
        return doc

    def _generate_component_diagram(self, arch: Dict[str, Any]) -> str:
        """Generate component diagram in PlantUML format"""

        diagram = "@startuml\n\n"

        # Add components
        for comp in arch.get('components', []):
            comp_name = comp.get('name', 'Unknown').replace(' ', '_')
            diagram += f"component [{comp.get('name', 'Unknown')}] as {comp_name}\n"

        diagram += "\n"

        # Add data flows
        for flow in arch.get('data_flow', []):
            from_comp = flow.get('from', 'Unknown').replace(' ', '_')
            to_comp = flow.get('to', 'Unknown').replace(' ', '_')
            diagram += f"{from_comp} --> {to_comp} : {flow.get('data', '')}\n"

        diagram += "\n@enduml"

        return diagram

    def _generate_database_schema(self, arch: Dict[str, Any]) -> str:
        """Generate basic database schema"""

        db_design = arch.get('database_design', {})
        entities = db_design.get('key_entities', [])

        schema = f"-- Database Schema for {db_design.get('primary_database', 'Unknown')}\n\n"

        for entity in entities:
            table_name = entity.lower().replace(' ', '_')
            schema += f"""CREATE TABLE {table_name} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Add specific fields based on entity
);

"""

        return schema

    def _generate_api_spec(self, arch: Dict[str, Any]) -> str:
        """Generate OpenAPI specification"""

        api_design = arch.get('api_design', {})

        spec = f"""openapi: 3.0.0
info:
  title: System API
  version: 1.0.0
  description: API specification for the system

servers:
  - url: http://localhost:8000
    description: Development server

components:
  securitySchemes:
    {api_design.get('authentication', 'Bearer')}:
      type: http
      scheme: bearer

paths:
"""

        for endpoint in api_design.get('key_endpoints', []):
            path = endpoint.get('path', '/api/resource')
            method = endpoint.get('method', 'GET').lower()

            spec += f"""  {path}:
    {method}:
      summary: {endpoint.get('purpose', 'API endpoint')}
      security:
        - {api_design.get('authentication', 'Bearer')}: []
      responses:
        '200':
          description: Successful response
        '401':
          description: Unauthorized
        '500':
          description: Internal server error

"""

        return spec

    def _assess_implementation(self, arch: Dict[str, Any]) -> Dict[str, Any]:
        """Assess implementation complexity"""

        complexity_score = 0

        # Pattern complexity
        pattern_scores = {
            "layered": 1,
            "modular_monolith": 2,
            "serverless": 3,
            "microservices": 4
        }
        complexity_score += pattern_scores.get(arch.get('architecture_pattern', 'modular_monolith'), 2)

        # Component count
        complexity_score += min(len(arch.get('components', [])) * 0.5, 3)

        # Technology diversity
        all_tech = []
        for techs in arch.get('technology_stack', {}).values():
            all_tech.extend(techs)
        complexity_score += min(len(set(all_tech)) * 0.2, 2)

        # Determine level
        if complexity_score <= 3:
            level = "low"
            time_estimate = "2-4 weeks"
            team_size = "2-3 developers"
        elif complexity_score <= 5:
            level = "medium"
            time_estimate = "4-8 weeks"
            team_size = "3-5 developers"
        elif complexity_score <= 7:
            level = "high"
            time_estimate = "8-12 weeks"
            team_size = "5-8 developers"
        else:
            level = "very high"
            time_estimate = "12+ weeks"
            team_size = "8+ developers"

        return {
            "complexity_score": round(complexity_score, 2),
            "complexity_level": level,
            "estimated_implementation_time": time_estimate,
            "recommended_team_size": team_size,
            "key_challenges": self._identify_challenges(arch)
        }

    def _identify_challenges(self, arch: Dict[str, Any]) -> List[str]:
        """Identify key implementation challenges"""

        challenges = []

        pattern = arch.get('architecture_pattern', '')
        if pattern == 'microservices':
            challenges.append("Managing distributed system complexity")
            challenges.append("Ensuring data consistency across services")
        elif pattern == 'serverless':
            challenges.append("Managing cold start latency")
            challenges.append("Debugging distributed functions")

        if len(arch.get('components', [])) > 10:
            challenges.append("Coordinating many system components")

        if 'high performance' in str(arch.get('scalability_strategy', [])).lower():
            challenges.append("Optimizing for high performance requirements")

        return challenges[:5]  # Limit to top 5


# Example usage
async def main():
    """Example usage of Architect Agent"""

    agent = ArchitectAgent(api_key="your-anthropic-api-key")

    functional_requirements = [
        "User authentication and authorization",
        "Task creation and management",
        "Team collaboration features",
        "Real-time notifications",
        "Report generation"
    ]

    non_functional_requirements = [
        "Support 1000+ concurrent users",
        "Response time under 200ms for 95% of requests",
        "99.9% uptime SLA",
        "GDPR and SOC 2 compliance",
        "Mobile responsive design"
    ]

    context = {
        "team_size": "5 developers",
        "timeline": "6 months",
        "budget": "moderate",
        "existing_infrastructure": "AWS cloud"
    }

    result = await agent.design(
        functional_requirements=functional_requirements,
        non_functional_requirements=non_functional_requirements,
        complexity="medium",
        context=context
    )

    if result["success"]:
        print("Architecture design successful!")
        print(f"\nPattern: {result['architecture']['architecture_pattern']}")
        print(f"\nImplementation Assessment:")
        print(f"- Complexity: {result['implementation_assessment']['complexity_level']}")
        print(f"- Estimated Time: {result['implementation_assessment']['estimated_implementation_time']}")
        print(f"\nArchitecture Document:\n{result['artifacts']['architecture_document'][:500]}...")
    else:
        print(f"Architecture design failed: {result['error']}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
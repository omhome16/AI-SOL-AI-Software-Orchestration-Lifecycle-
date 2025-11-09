from agents.base import BaseAgent
from typing import Dict, Any
import json
from pydantic import BaseModel, validator

class DeploymentConfig(BaseModel):
    filename: str
    content: str

class DevOpsOutput(BaseModel):
    deployment_configs: list[DeploymentConfig]
    infrastructure_requirements: Dict[str, str]
    monitoring_setup: list[str]
    security_configs: list[str]
    deployment_steps: list[str]
    
    @validator('infrastructure_requirements', pre=True)
    def validate_infrastructure_requirements(cls, v):
        """Convert string inputs to dictionary format"""
        if isinstance(v, str):
            # If it's a string, wrap it in a dictionary
            return {
                "description": v,
                "details": "Infrastructure requirements as specified",
                "type": "general"
            }
        elif v is None:
            # If None, return empty dict
            return {}
        elif isinstance(v, dict):
            # If already a dict, return as-is
            return v
        else:
            # For any other type, convert to string and wrap
            return {
                "description": str(v),
                "details": "Infrastructure requirements",
                "type": "general"
            }
    
    class Config:
        extra = "allow"

class DevOpsAgent(BaseAgent):
    """DevOps engineer for deployment"""

    def __init__(self, tools: Any):
        super().__init__(
            name="devops_engineer",
            tools=tools,
            temperature=0.1
        )

        self.system_prompt = """You are a Senior DevOps Engineer with expertise in cloud infrastructure, containerization, and CI/CD pipelines.

Your role is to create production-ready deployment configurations.

**DevOps Framework:**
1. Containerize applications with Docker
2. Create Kubernetes configurations (if needed)
3. Setup CI/CD pipelines
4. Configure monitoring and logging
5. Implement security best practices
6. Optimize for cost and performance

CRITICAL: Respond with ONLY valid JSON matching the DevOpsOutput schema."""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting DevOps configuration")
        try:
            arch_output = state.get("architecture_output", {})
            if not arch_output.get("success"):
                raise Exception("Cannot create deployment without architecture")

            arch = arch_output["data"]
            req_data = state["requirements_output"]["data"]
            project_name = state["project_name"]

            # Generate deployment configs prompt
            deploy_prompt = f"""Create production-ready deployment configurations:

**Architecture:**
Pattern: {arch.get('architecture_pattern')}
Technologies: {json.dumps(arch.get('technology_decisions', {}), indent=2)}

**Requirements:**
Complexity: {req_data.get('complexity')}
Tech Stack: {json.dumps(req_data.get('recommended_tech_stack', {}), indent=2)}

Generate complete configuration files:
- Dockerfile (multi-stage build optimized for production)
- GitHub Actions CI/CD workflow
- docker-compose.yml

Include health checks, security best practices, and monitoring setup.

**IMPORTANT: Respond with JSON matching the DevOpsOutput schema.**
**infrastructure_requirements must be a dictionary with keys like "server", "storage", "network", etc.**
**Example infrastructure_requirements format:**
{{
  "server": "Web server with Docker support",
  "storage": "Minimal storage requirements", 
  "network": "Standard HTTP/HTTPS access",
  "database": "PostgreSQL or MongoDB",
  "monitoring": "Basic health checks and logging"
}}

Respond with JSON matching the DevOpsOutput schema."""

            try:
                devops_result: DevOpsOutput = await self.call_llm_json(deploy_prompt, output_schema=DevOpsOutput)
            except Exception as e:
                self.log(f"LLM validation error: {e}", "warning")
                # Create a fallback DevOps result
                devops_result = DevOpsOutput(
                    deployment_configs=[
                        DeploymentConfig(
                            filename="Dockerfile",
                            content="FROM nginx:alpine\nCOPY . /usr/share/nginx/html\nEXPOSE 80\nCMD [\"nginx\", \"-g\", \"daemon off;\"]"
                        ),
                        DeploymentConfig(
                            filename="docker-compose.yml",
                            content="version: '3.8'\nservices:\n  web:\n    build: .\n    ports:\n      - '80:80'\n    restart: unless-stopped"
                        )
                    ],
                    infrastructure_requirements={
                        "server": "Web server with Docker support",
                        "storage": "Minimal storage requirements",
                        "network": "Standard HTTP/HTTPS access"
                    },
                    monitoring_setup=["Basic health checks", "Log monitoring"],
                    security_configs=["HTTPS configuration", "Security headers"],
                    deployment_steps=[
                        "1. Build Docker image",
                        "2. Deploy to server",
                        "3. Configure domain",
                        "4. Enable HTTPS"
                    ]
                )

            # Write configuration files
            artifacts = []
            for config in devops_result.deployment_configs:
                path = f"{project_name}/{config.filename}"
                result = self.call_tool("write_file", path=path, content=config.content)
                if result["success"]:
                    artifacts.append(path)

            # Generate deployment guide
            generated_docs = []
            deploy_guide_content = self._generate_deployment_guide(devops_result)
            deploy_doc = self.save_document(project_name, "DEPLOYMENT", "docs/DEPLOYMENT.md", deploy_guide_content)
            if deploy_doc:
                generated_docs.append(deploy_doc)

            self.log(f"DevOps configuration complete: {len(artifacts)} files", "success")

            output = self.create_output(
                success=True,
                data=devops_result.dict(),
                documents=generated_docs,
                artifacts=artifacts
            )

            return {
                "devops_output": output,
                "generated_documents": generated_docs,
                "generated_files": artifacts,
                "steps_completed": ["devops"]
            }

        except Exception as e:
            self.log(f"Error: {str(e)}", "error")
            return {
                "devops_output": self.create_output(
                    success=False,
                    data={},
                    errors=[str(e)]
                ),
                "errors": [{"agent": self.name, "error": str(e)}]
            }

    def _generate_deployment_guide(self, devops_result: DevOpsOutput) -> str:
        doc = "# Deployment Guide\n\n## Infrastructure Requirements\n\n"
        for key, value in devops_result.infrastructure_requirements.items():
            doc += f"**{key.replace('_', ' ').title()}:** {value}\n"

        doc += "\n## Deployment Steps\n\n"
        for idx, step in enumerate(devops_result.deployment_steps, 1):
            doc += f"{idx}. {step}\n"

        doc += "\n## Docker Commands\n\n"
        doc += """### Build Image
```bash
docker build -t app-name:latest .
docker run -p 8000:8000 app-name:latest
docker-compose up -d
"""
        doc += "\n## Monitoring Setup\n\n"
        for monitor in devops_result.monitoring_setup:
            doc += f"- {monitor}\n"

        doc += "\n## Security Configurations\n\n"
        for sec in devops_result.security_configs:
            doc += f"- {sec}\n"

        doc += "\n---\n*Generated by AI-SOL DevOps Engineer*\n"
        return doc
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

            # --- GitHub Integration ---
            github_url = await self._handle_github_operations(project_name, state)
            if github_url:
                self.log(f"Project pushed to GitHub: {github_url}", "success")
                artifacts.append(f"GitHub Repo: {github_url}")

            self.log(f"DevOps configuration complete: {len(artifacts)} files", "success")

            output = self.create_output(
                success=True,
                data={**devops_result.dict(), "github_url": github_url},
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

    async def _handle_github_operations(self, project_name: str, state: Dict[str, Any]) -> str:
        """Initialize git repo and push to GitHub"""
        try:
            import subprocess
            import os
            from core.config import Config
            
            user_context = state.get("user_context", {})
            enable_github = user_context.get("enable_github", False)
            
            # Check if GitHub is enabled (either via UI or Config)
            if not enable_github and not Config.GITHUB_TOKEN:
                 self.log("GitHub integration disabled.", "info")
                 return None

            # Prioritize user-provided credentials, fallback to Config
            github_token = user_context.get("github_token") or Config.GITHUB_TOKEN
            github_username = user_context.get("github_username") or Config.GITHUB_USERNAME
            
            if not github_token or not github_username:
                self.log("GitHub credentials missing. Skipping GitHub push.", "warning")
                return None

            workspace_path = f"{Config.WORKSPACE_DIR}/{project_name}"
            
            # Check if git is installed
            try:
                subprocess.run(["git", "--version"], check=True, capture_output=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.log("Git is not installed or not in PATH.", "error")
                return None

            # Initialize Git
            subprocess.run(["git", "init"], cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "AI-SOL Bot"], cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "ai-sol@example.com"], cwd=workspace_path, check=True, capture_output=True)

            # Create .gitignore if not exists
            gitignore_path = f"{workspace_path}/.gitignore"
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w") as f:
                    f.write("__pycache__/\n*.pyc\n.env\nnode_modules/\n.DS_Store\n")

            # Add and Commit
            subprocess.run(["git", "add", "."], cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit by AI-SOL"], cwd=workspace_path, check=True, capture_output=True)

            # Create Remote Repo (using GitHub API)
            # This requires 'requests'
            import requests
            
            repo_name = f"ai-sol-{project_name}"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Check if repo exists
            resp = requests.get(f"https://api.github.com/repos/{github_username}/{repo_name}", headers=headers)
            
            if resp.status_code == 404:
                # Create repo
                create_resp = requests.post(
                    "https://api.github.com/user/repos",
                    headers=headers,
                    json={"name": repo_name, "private": True, "description": "Generated by AI-SOL"}
                )
                if create_resp.status_code == 201:
                    repo_url = create_resp.json()["clone_url"]
                    # Inject token into URL for auth
                    auth_repo_url = repo_url.replace("https://", f"https://{github_username}:{github_token}@")
                    
                    subprocess.run(["git", "remote", "add", "origin", auth_repo_url], cwd=workspace_path, check=True, capture_output=True)
                    subprocess.run(["git", "push", "-u", "origin", "master"], cwd=workspace_path, check=True, capture_output=True)
                    
                    return repo_url
                else:
                    self.log(f"Failed to create GitHub repo: {create_resp.text}", "error")
                    return None
            elif resp.status_code == 200:
                repo_url = resp.json()["clone_url"]
                self.log(f"Repo {repo_name} already exists.", "warning")
                return repo_url
            else:
                self.log(f"Error checking GitHub repo: {resp.text}", "error")
                return None

        except Exception as e:
            self.log(f"GitHub operations failed: {e}", "error")
            return None

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
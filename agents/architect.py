from agents.base import BaseAgent
from typing import Dict, Any, List, Any as AnyType
import json
from pathlib import Path
from utils.context_manager import AgentContext, ProjectBlueprint, FileTask

# ------------------------------
# ArchitectAgent
# ------------------------------
class ArchitectAgent(BaseAgent):
    """Technology-specific system architect that designs comprehensive architectures for any project type.

    Features:
    - Context-driven design decisions
    - Project Blueprint generation
    - Folder structure materialization
    """
    
    def __init__(self, tools: AnyType):
        super().__init__(
            name="system_architect",
            tools=tools,
            temperature=0.1
        )

        self.system_prompt = """You are a Senior Software Architect with expertise across multiple technology stacks including React/Vue/Angular frontends, Node.js/Python/Java backends, microservices, serverless, and cloud-native architectures.

Your role is to design comprehensive, technology-specific system architectures that provide detailed implementation guidance.

**Technology-Specific Architecture Framework:**
1. Analyze requirements and technology stack
2. Choose appropriate architecture pattern for the tech stack
3. Design detailed system components with specific technologies
4. Define precise data flow and communication patterns
5. Create detailed database schema with specific database technologies
6. Design comprehensive API contracts with specific frameworks
7. Plan security architecture with specific security tools
8. Design for scalability using technology-specific patterns
9. Provide detailed deployment architecture

**Architecture Patterns by Technology:**
- **React/Vue/Angular**: Component-based architecture, state management patterns
- **Node.js**: Event-driven, microservices, API-first design
- **Python**: Django/FastAPI patterns, service-oriented architecture
- **Java**: Spring Boot microservices, enterprise patterns
- **Microservices**: Domain-driven design, API gateway patterns
- **Serverless**: Event-driven, function-as-a-service patterns

**Design Principles:**
- Technology-specific best practices and patterns
- Detailed implementation guidance for chosen technologies
- Security by design with specific security tools
- Scalability patterns appropriate for the technology stack
- Clear component interfaces and data contracts

CRITICAL: Respond with ONLY valid JSON. Provide detailed, implementable architecture specifications."""

    async def _generate_blueprint(self, context: AgentContext) -> ProjectBlueprint:
        """Generate complete project blueprint"""
        
        prompt = f"""Create a complete project blueprint.

**Project**: {context.project_name}
**Type**: {context.project_type.value}
**Requirements**: {len(context.functional_requirements)} requirements

Generate a JSON response with:
1. explanation: Brief architecture explanation
2. folder_structure: List of directories ["src", "tests", etc.]
3. build_plan: List of files with dependencies

For each file in build_plan:
- path: "src/models/user.py"
- purpose: "User data model with validation"
- dependencies: ["src/models/base.py"] (files this depends on)

Order files by dependencies (base files first).

Return ONLY valid JSON:"""
        
        response = await self.call_llm(prompt)

        # Normalize response: support string, dict, pydantic model, or object with .content
        import json
        raw = response
        # extract content if wrapper object
        try:
            raw = getattr(response, "content", response)
        except Exception:
            raw = response

        data = None
        # If it's already a dict or model, try to use it directly
        if isinstance(raw, dict):
            data = raw
        elif hasattr(raw, 'dict'):
            try:
                data = raw.dict()
            except Exception:
                data = None

        if data is None:
            # If it's a string, try to parse JSON
            if isinstance(raw, str):
                text = raw.strip()
                if not text:
                    raise ValueError("Empty response from LLM when generating blueprint")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    # Try to extract JSON code fence
                    import re
                    m = re.search(r"```(?:json)?\n(.+?)```", text, re.S)
                    if m:
                        try:
                            data = json.loads(m.group(1))
                        except Exception as e:
                            raise ValueError(f"Failed to parse JSON from code fence: {e}")
                    else:
                        raise ValueError("LLM did not return valid JSON for ProjectBlueprint")
            else:
                # Fallback: try to stringify and parse
                try:
                    data = json.loads(str(raw))
                except Exception:
                    raise ValueError("Unable to normalize LLM response to JSON for ProjectBlueprint")

        # Validate minimal keys
        if not data or 'build_plan' not in data or 'folder_structure' not in data:
            raise ValueError("ProjectBlueprint JSON missing required keys: build_plan or folder_structure")

        file_tasks = []
        for f in data.get("build_plan", []):
            # tolerate either dicts or pydantic-like objects
            if hasattr(f, 'dict'):
                try:
                    ff = f.dict()
                except Exception:
                    ff = dict(f)
            else:
                ff = dict(f)

            file_tasks.append(
                FileTask(
                    path=ff.get("path"),
                    purpose=ff.get("purpose", ""),
                    dependencies=ff.get("dependencies", []) or []
                )
            )

        return ProjectBlueprint(
            explanation=data.get("explanation", ""),
            folder_structure=list(data.get("folder_structure", [])),
            build_plan=file_tasks
        )

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete ProjectBlueprint (master plan) and materialize folder structure.

        This execute() replaces the previous architecture-design flow and now produces a
        ProjectBlueprint via a structured LLM call. The blueprint is saved into the
        AgentContext (context.blueprint) and the folders in blueprint.folder_structure are
        created on disk.
        """
        self.log("Starting ProjectBlueprint generation (ArchitectAgent)")
        try:
            project_id = state.get("project_name", "default_project")
            context = self.load_context(project_id)
            if not context:
                raise Exception("No project context available to architect the blueprint")

            requirements = context.requirements if hasattr(context, 'requirements') else getattr(context, 'original_requirements', '')
            stack = context.technology_stack.to_dict() if hasattr(context, 'technology_stack') else {}

            prompt = (
                "CRITICAL: You MUST respond with only JSON matching the ProjectBlueprint schema.\n"
                "Do NOT include any explanation or markdown. The JSON must contain: explanation (str), folder_structure (list of dirs), build_plan (list of {path,purpose,dependencies}).\n\n"
                "Example response structure (must match exactly):\n"
                "{\n"
                "  \"explanation\": \"Short explanation of architecture\",\n"
                "  \"folder_structure\": [\"app/models\", \"app/services\"],\n"
                "  \"build_plan\": [\n"
                "    { \"path\": \"app/models/user.py\", \"purpose\": \"Defines User model\", \"dependencies\": [] },\n"
                "    { \"path\": \"app/services/user_service.py\", \"purpose\": \"Business logic for users\", \"dependencies\": [\"app/models/user.py\"] },\n"
                "    { \"path\": \"app/main.py\", \"purpose\": \"Application entrypoint\", \"dependencies\": [\"app/services/user_service.py\"] }\n"
                "  ]\n"
                "}\n\n"
                f"Full requirements:\n{requirements}\n\n"
                f"Technology stack:\n{json.dumps(stack)}\n\n"
                "You are a 10x Solutions Architect. Generate a complete ProjectBlueprint for this project. The build_plan is the most important part. The build_plan MUST be a dependency-sorted list of all files required to build this project. Start with base files (models, base configs), then services that import models, then API routes that import services, and finally the main app file (main.py or index.js). Include README.md and the dependency file (requirements.txt or package.json) as the very last steps.\n"
            )

            # call structured LLM expecting ProjectBlueprint
            blueprint = await self._generate_blueprint(context)

            self.context_manager.update_context(project_id, {
                "blueprint": blueprint
            })

            # Create folder structure
            root = Path(getattr(context, 'project_root', '.'))
            created = []
            for folder in blueprint.folder_structure or []:
                p = root / folder
                p.mkdir(parents=True, exist_ok=True)
                created.append(str(p))

            # Save blueprint JSON to project for inspection
            try:
                bp_file = root / 'project_blueprint.json'
                bp_file.write_text(json.dumps(blueprint.dict(), indent=2), encoding='utf-8')
            except Exception:
                pass

            self.log(f"ProjectBlueprint generated with {len(blueprint.build_plan)} files", "success")

            # Create standardized agent output for compatibility with orchestrator/app
            output = self.create_output(
                success=True,
                data={"blueprint": blueprint.dict()},
                documents=[],
                artifacts=created
            )

            return {"architecture_output": output}

        except Exception as e:
            self.log(f"ArchitectAgent.execute failed: {e}", "error")
            output = self.create_output(success=False, data={}, errors=[str(e)])
            return {"architecture_output": output}


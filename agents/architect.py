from agents.base import BaseAgent
from typing import Dict, Any, List, Any as AnyType
import json
from pydantic import BaseModel, Field
from utils.context_manager import AgentContext, ComponentSpecification, TechnologyStack, ProjectBlueprint, FileTask
from utils.project_classifier import ProjectType, ComplexityLevel
import asyncio

from zoneinfo import ZoneInfo
from pathlib import Path

TZ = ZoneInfo("Asia/Kolkata")


# ------------------------------
# Pydantic models (LLM outputs)
# ------------------------------
class SystemComponent(BaseModel):
    name: str = Field(description="Name of the component")
    responsibility: str = Field(description="What it does")
    technology: str = Field(description="Specific tech used")
    interfaces: List[str] = Field(description="API endpoints or contracts")

    class Config:
        extra = "allow"


class DataFlow(BaseModel):
    from_component: str = Field(description="Component A")
    to_component: str = Field(description="Component B")
    data: str = Field(description="What data flows")
    protocol: str = Field(description="HTTP/gRPC/MessageQueue")

    class Config:
        extra = "allow"


class Entity(BaseModel):
    name: str = Field(description="Entity name")
    attributes: List[str] = Field(description="List of attributes")
    relationships: List[str] = Field(description="Relation to other entities")

    class Config:
        extra = "allow"


class DatabaseDesign(BaseModel):
    type: str = Field(description="SQL|NoSQL|Hybrid")
    primary_database: str = Field(description="PostgreSQL|MongoDB|etc")
    entities: List[Entity] = Field(description="List of entities")
    caching_strategy: str = Field(description="Redis|Memcached|None")

    class Config:
        extra = "allow"


class APIEndpoint(BaseModel):
    path: str = Field(description="/api/resource")
    method: str = Field(description="GET|POST|PUT|DELETE")
    purpose: str = Field(description="What it does")

    class Config:
        extra = "allow"


class APIDesign(BaseModel):
    style: str = Field(description="REST|GraphQL|gRPC")
    authentication: str = Field(description="JWT|OAuth2|API Keys")
    endpoints: List[APIEndpoint] = Field(description="List of endpoints")

    class Config:
        extra = "allow"


class ScalabilityStrategy(BaseModel):
    horizontal_scaling: str = Field(description="Strategy for horizontal scaling")
    vertical_scaling: str = Field(description="Strategy for vertical scaling")
    load_balancing: str = Field(description="Load balancing approach")
    caching: str = Field(description="Caching strategy")

    class Config:
        extra = "allow"


class TechnologyDecisions(BaseModel):
    backend_framework: str = Field(description="FastAPI|Django|Express|etc")
    frontend_framework: str = Field(description="React|Vue|Angular|etc")
    message_queue: str = Field(description="RabbitMQ|Kafka|None")
    monitoring: str = Field(description="Prometheus|DataDog|etc")

    class Config:
        extra = "allow"


class Architecture(BaseModel):
    architecture_pattern: str = Field(description="microservices|monolith|serverless|layered")
    architecture_style: str = Field(description="Description of chosen style and rationale")
    system_components: List[SystemComponent] = Field(description="List of system components")
    data_flow: List[DataFlow] = Field(description="List of data flows")
    database_design: DatabaseDesign = Field(description="Database design")
    api_design: APIDesign = Field(description="API design")
    security_architecture: List[str] = Field(description="List of security measures")
    scalability_strategy: ScalabilityStrategy = Field(description="Scalability strategy")
    technology_decisions: TechnologyDecisions = Field(description="Technology decisions")
    deployment_architecture: str = Field(description="Description of deployment strategy")

    class Config:
        extra = "allow"


# ------------------------------
# Helper utilities
# ------------------------------
def _normalize_model(obj: AnyType) -> AnyType:
    """
    Convert pydantic models to plain dicts, return primitives as-is.
    """
    if obj is None:
        return None
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            # fallback: try to serialize
            try:
                return json.loads(json.dumps(obj, default=str))
            except Exception:
                return str(obj)
    if isinstance(obj, (dict, list, str, int, float, bool)):
        return obj
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return str(obj)


def _safe_get(obj: AnyType, attr: str, default=None):
    """
    Retrieve attribute safely from pydantic model or dict.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    if hasattr(obj, attr):
        try:
            return getattr(obj, attr)
        except Exception:
            return default
    # last resort: attempt dict() if model-like
    if hasattr(obj, "dict"):
        try:
            d = obj.dict()
            return d.get(attr, default)
        except Exception:
            return default
    return default


def _iterable_from(obj: AnyType, attr: str):
    """
    Return an iterable (list) for the given attribute whether obj is dict or model.
    """
    val = _safe_get(obj, attr, [])
    if val is None:
        return []
    if isinstance(val, list):
        return val
    # sometimes nested objects may be pydantic models with .dict()
    if hasattr(val, "dict"):
        try:
            return val.dict()
        except Exception:
            return [val]
    return [val]


# ------------------------------
# ArchitectAgent
# ------------------------------
class ArchitectAgent(BaseAgent):
    """Technology-specific system architect that designs comprehensive architectures for any project type.

    Features:
    - Technology-specific architecture patterns
    - Context-driven design decisions
    - Industry-specific best practices
    - Comprehensive component specifications
    - Detailed implementation guidance
    - Scalability and security considerations
    """
    def get_architecture_pattern(self, architecture: Architecture) -> str:
        """Get the architecture pattern."""
        return architecture.architecture_pattern

    def get_technology_stack(self, architecture: Architecture) -> TechnologyDecisions:
        """Get the technology stack."""
        return architecture.technology_decisions

    def __init__(self, tools: AnyType):
        super().__init__(
            name="system_architect",
            tools=tools,
            temperature=0.1
        )

        # Technology-specific architecture patterns
        self.tech_patterns = self._initialize_tech_patterns()

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
    
    def _initialize_tech_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize technology-specific architecture patterns"""
        return {
            "react": {
                "architecture_pattern": "component-based",
                "state_management": ["Redux", "Context API", "Zustand"],
                "routing": ["React Router", "Next.js Router"],
                "styling": ["CSS Modules", "Styled Components", "Tailwind CSS"],
                "testing": ["Jest", "React Testing Library", "Cypress"],
                "build_tools": ["Vite", "Webpack", "Create React App"],
                "patterns": ["Container/Presenter", "Higher-Order Components", "Custom Hooks"]
            },
            "vue": {
                "architecture_pattern": "component-based",
                "state_management": ["Vuex", "Pinia", "Composition API"],
                "routing": ["Vue Router"],
                "styling": ["Scoped CSS", "CSS Modules", "Tailwind CSS"],
                "testing": ["Jest", "Vue Test Utils", "Cypress"],
                "build_tools": ["Vite", "Webpack", "Vue CLI"],
                "patterns": ["Composition API", "Mixins", "Provide/Inject"]
            },
            "angular": {
                "architecture_pattern": "modular",
                "state_management": ["NgRx", "Angular Services", "RxJS"],
                "routing": ["Angular Router"],
                "styling": ["Angular Material", "Bootstrap", "Tailwind CSS"],
                "testing": ["Jasmine", "Karma", "Protractor"],
                "build_tools": ["Angular CLI", "Webpack"],
                "patterns": ["Dependency Injection", "Observables", "Guards"]
            },
            "nodejs": {
                "architecture_pattern": "microservices",
                "frameworks": ["Express", "Fastify", "NestJS", "Koa"],
                "orm": ["Prisma", "Sequelize", "TypeORM", "Mongoose"],
                "testing": ["Jest", "Mocha", "Supertest"],
                "patterns": ["Middleware", "Controllers", "Services", "Repository"],
                "deployment": ["Docker", "PM2", "Kubernetes"]
            },
            "python": {
                "architecture_pattern": "layered",
                "frameworks": ["Django", "FastAPI", "Flask", "Pyramid"],
                "orm": ["Django ORM", "SQLAlchemy", "Tortoise ORM"],
                "testing": ["pytest", "unittest", "Django Test"],
                "patterns": ["MVC", "Repository", "Service Layer", "Dependency Injection"],
                "deployment": ["Docker", "Gunicorn", "uWSGI"]
            },
            "java": {
                "architecture_pattern": "enterprise",
                "frameworks": ["Spring Boot", "Quarkus", "Micronaut"],
                "orm": ["Hibernate", "JPA", "MyBatis"],
                "testing": ["JUnit", "Mockito", "TestContainers"],
                "patterns": ["MVC", "Service Layer", "Repository", "Dependency Injection"],
                "deployment": ["Docker", "Kubernetes", "Tomcat"]
            }
        }
    
    def _analyze_technology_stack(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze technology stack and determine architecture patterns"""
        tech_stack = context.technology_stack
        
        # Determine primary technologies
        primary_frontend = tech_stack.frontend[0] if tech_stack.frontend else "html"
        primary_backend = tech_stack.backend[0] if tech_stack.backend else "python"
        primary_database = tech_stack.database[0] if tech_stack.database else "sqlite"
        
        # Get technology patterns
        frontend_patterns = self.tech_patterns.get(primary_frontend.lower(), {})
        backend_patterns = self.tech_patterns.get(primary_backend.lower(), {})
        
        return {
            "primary_frontend": primary_frontend,
            "primary_backend": primary_backend,
            "primary_database": primary_database,
            "frontend_patterns": frontend_patterns,
            "backend_patterns": backend_patterns,
            "project_type": context.project_type.value,
            "complexity": context.complexity_level,
            "all_technologies": {
                "frontend": tech_stack.frontend,
                "backend": tech_stack.backend,
                "database": tech_stack.database,
                "devops": tech_stack.devops
            }
        }
    
    async def _conduct_tech_research(self, context: AgentContext, tech_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Conduct technology-specific research"""
        research_results = []
        
        try:
            primary_frontend = tech_analysis["primary_frontend"]
            primary_backend = tech_analysis["primary_backend"]
            project_type = tech_analysis["project_type"]
            
            search_queries = [
                f"{primary_frontend} {primary_backend} architecture best practices",
                f"{project_type} {primary_frontend} {primary_backend} patterns",
                f"{primary_backend} microservices architecture patterns"
            ]
            
            for query in search_queries:
                self.log(f"Researching: {query}", "info")
                search_result = self.call_tool("web_search", query=query, max_results=2)
                
                if search_result.get("success"):
                    results = search_result.get("results", [])
                    research_results.extend(results)
            
            self.log(f"Technology research completed: {len(research_results)} results found", "info")
            
        except Exception as e:
            self.log(f"Technology research failed: {e}", "warning")
        
        return research_results
    
    async def _design_technology_specific_architecture(self, context: AgentContext, 
                                                      tech_analysis: Dict[str, Any], 
                                                      research_results: List[Dict[str, Any]]) -> Architecture:
        """Design technology-specific architecture using LLM"""
        
        # Build comprehensive prompt with technology-specific guidance
        prompt = f"""Design a comprehensive, technology-specific system architecture:

**Project Context:**
- Project Type: {context.project_type.value}
- Complexity: {context.complexity_level}
- Domain: {getattr(context, 'domain', 'general')}

**Technology Stack:**
- Frontend: {', '.join(tech_analysis['all_technologies']['frontend'])}
- Backend: {', '.join(tech_analysis['all_technologies']['backend'])}
- Database: {', '.join(tech_analysis['all_technologies']['database'])}
- DevOps: {', '.join(tech_analysis['all_technologies']['devops'])}

**Primary Technologies:**
- Frontend Framework: {tech_analysis['primary_frontend']}
- Backend Framework: {tech_analysis['primary_backend']}
- Database: {tech_analysis['primary_database']}

**Technology-Specific Patterns:**
Frontend ({tech_analysis['primary_frontend']}):
{self._format_tech_patterns(tech_analysis['frontend_patterns'])}

Backend ({tech_analysis['primary_backend']}):
{self._format_tech_patterns(tech_analysis['backend_patterns'])}

**Functional Requirements:**
{self._format_requirements_for_prompt(context.functional_requirements)}

**Non-Functional Requirements:**
{self._format_non_functional_requirements(context.non_functional_requirements)}

**Research Findings:**
{self._format_research_results(research_results)}

**Instructions:**
1. Choose architecture pattern appropriate for {tech_analysis['primary_backend']} and {tech_analysis['primary_frontend']}
2. Design detailed system components using specific {tech_analysis['primary_backend']} and {tech_analysis['primary_frontend']} patterns
3. Define precise data flow with specific protocols and frameworks
4. Create detailed database schema using {tech_analysis['primary_database']} specific features
5. Design comprehensive API contracts using {tech_analysis['primary_backend']} framework patterns
6. Plan security architecture with specific security tools and frameworks
7. Design for scalability using technology-specific patterns
8. Provide detailed deployment architecture

**CRITICAL: Respond with ONLY valid JSON matching the Architecture schema.**

Generate technology-specific architecture:"""

        try:
            architecture = await self.call_llm_json(prompt, output_schema=Architecture)
            return architecture
        except Exception as e:
            self.log(f"LLM architecture design failed: {e}", "error")
            return self._create_fallback_architecture(context, tech_analysis)
    
    def _format_tech_patterns(self, patterns: Dict[str, Any]) -> str:
        """Format technology patterns for prompt"""
        if not patterns:
            return "No specific patterns available"
        
        formatted = ""
        for key, value in patterns.items():
            if isinstance(value, list):
                formatted += f"- {key}: {', '.join(value)}\n"
            else:
                formatted += f"- {key}: {value}\n"
        
        return formatted
    
    def _format_requirements_for_prompt(self, requirements: List) -> str:
        """Format functional requirements for prompt"""
        if not requirements:
            return "No functional requirements specified"
        
        formatted = ""
        for req in requirements:
            if hasattr(req, 'description'):
                formatted += f"- {req.description}\n"
            elif isinstance(req, dict):
                formatted += f"- {req.get('description', str(req))}\n"
            else:
                formatted += f"- {str(req)}\n"
        
        return formatted
    
    def _format_non_functional_requirements(self, requirements: List) -> str:
        """Format non-functional requirements for prompt"""
        if not requirements:
            return "No non-functional requirements specified"
        
        formatted = ""
        for req in requirements:
            if hasattr(req, 'description'):
                formatted += f"- {req.category}: {req.description}\n"
            elif isinstance(req, dict):
                formatted += f"- {req.get('category', 'general')}: {req.get('description', str(req))}\n"
            else:
                formatted += f"- {str(req)}\n"
        
        return formatted
    
    def _format_research_results(self, research_results: List[Dict[str, Any]]) -> str:
        """Format research results for prompt"""
        if not research_results:
            return "No research data available."
        
        formatted = "**Technology Research Findings:**\n"
        for idx, result in enumerate(research_results[:5], 1):
            title = result.get('title', 'Untitled')
            body = result.get('body', '')[:300]
            formatted += f"{idx}. {title}: {body}...\n"
        
        return formatted
    
    def _create_fallback_architecture(self, context: AgentContext, tech_analysis: Dict[str, Any]) -> Architecture:
        """Create fallback architecture when LLM fails"""
        
        primary_frontend = tech_analysis["primary_frontend"]
        primary_backend = tech_analysis["primary_backend"]
        primary_database = tech_analysis["primary_database"]
        
        # Create basic components based on technology stack
        components = [
            SystemComponent(
                name=f"{primary_frontend.title()} Frontend",
                responsibility="User interface and client-side logic",
                technology=primary_frontend,
                interfaces=["REST API", "WebSocket"]
            ),
            SystemComponent(
                name=f"{primary_backend.title()} Backend",
                responsibility="Business logic and API services",
                technology=primary_backend,
                interfaces=["REST API", "Database"]
            ),
            SystemComponent(
                name=f"{primary_database.title()} Database",
                responsibility="Data persistence and storage",
                technology=primary_database,
                interfaces=["SQL/NoSQL API"]
            )
        ]
        
        # Create data flows
        data_flows = [
            DataFlow(
                from_component=f"{primary_frontend.title()} Frontend",
                to_component=f"{primary_backend.title()} Backend",
                data="HTTP requests/responses",
                protocol="REST API"
            ),
            DataFlow(
                from_component=f"{primary_backend.title()} Backend",
                to_component=f"{primary_database.title()} Database",
                data="CRUD operations",
                protocol="Database API"
            )
        ]
        
        # Create database design
        database_design = DatabaseDesign(
            type="SQL" if "sql" in primary_database.lower() else "NoSQL",
            primary_database=primary_database,
            entities=[
                Entity(name="User", attributes=["id", "name", "email"], relationships=["has many Posts"]),
                Entity(name="Post", attributes=["id", "title", "content"], relationships=["belongs to User"])
            ],
            caching_strategy="Redis" if primary_database.lower() != "redis" else "None"
        )
        
        # Create API design
        api_design = APIDesign(
            style="REST",
            authentication="JWT",
            endpoints=[
                APIEndpoint(path="/api/users", method="GET", purpose="Get all users"),
                APIEndpoint(path="/api/users", method="POST", purpose="Create user"),
                APIEndpoint(path="/api/posts", method="GET", purpose="Get all posts"),
                APIEndpoint(path="/api/posts", method="POST", purpose="Create post")
            ]
        )
        
        # Create scalability strategy
        scalability_strategy = ScalabilityStrategy(
            horizontal_scaling="Load balancer with multiple instances",
            vertical_scaling="Increase server resources",
            load_balancing="Round-robin or least connections",
            caching="Redis for session and data caching"
        )
        
        # Create technology decisions
        technology_decisions = TechnologyDecisions(
            backend_framework=primary_backend,
            frontend_framework=primary_frontend,
            message_queue="None" if context.complexity_level == "low" else "Redis",
            monitoring="Basic logging" if context.complexity_level == "low" else "Prometheus + Grafana"
        )
        
        return Architecture(
            architecture_pattern="layered" if context.complexity_level == "low" else "microservices",
            architecture_style=f"Technology-specific architecture using {primary_frontend} frontend and {primary_backend} backend",
            system_components=components,
            data_flow=data_flows,
            database_design=database_design,
            api_design=api_design,
            security_architecture=["JWT Authentication", "HTTPS", "Input validation"],
            scalability_strategy=scalability_strategy,
            technology_decisions=technology_decisions,
            deployment_architecture=f"Docker containers with {primary_database} database"
        )
    
    def _update_context_with_architecture(self, context: AgentContext, architecture: Architecture):
        """Update context with architecture design results"""
        # Update architecture pattern
        context.architecture_pattern = architecture.architecture_pattern
        
        # Update component specifications
        context.component_specifications = [
            ComponentSpecification(
                name=comp.name,
                description=comp.responsibility,
                technologies=[comp.technology],
                interfaces=comp.interfaces,
                dependencies=[]
            )
            for comp in architecture.system_components
        ]
        
        # Update data models from database design
        context.data_models = [
            {
                "name": entity.name,
                "attributes": entity.attributes,
                "relationships": entity.relationships
            }
            for entity in architecture.database_design.entities
        ]
    
    async def _generate_comprehensive_docs(self, architecture: Architecture, context: AgentContext, 
                                          research_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate comprehensive architecture documentation"""
        generated_docs = []
        
        # Generate main architecture document
        arch_doc_content = self._generate_enhanced_architecture_doc(architecture, context, research_results)
        arch_doc = self.save_document(context.project_name, "ARCHITECTURE", "docs/ARCHITECTURE.md", arch_doc_content)
        if arch_doc:
            generated_docs.append(arch_doc)
        
        # Generate technology-specific documentation
        tech_doc_content = self._generate_technology_specific_doc(architecture, context)
        tech_doc = self.save_document(context.project_name, "TECHNOLOGY_GUIDE", "docs/TECHNOLOGY_GUIDE.md", tech_doc_content)
        if tech_doc:
            generated_docs.append(tech_doc)
        
        # Generate database schema
        db_schema_content = self._generate_db_schema(architecture)
        db_doc = self.save_document(context.project_name, "DB_SCHEMA", "docs/DATABASE_SCHEMA.md", db_schema_content)
        if db_doc:
            generated_docs.append(db_doc)
        
        # Generate API specification
        api_spec_content = self._generate_api_spec(architecture)
        api_doc = self.save_document(context.project_name, "API_SPEC", "docs/API_SPECIFICATION.md", api_spec_content)
        if api_doc:
            generated_docs.append(api_doc)
        
        return generated_docs
    
    def _generate_enhanced_architecture_doc(self, architecture: Architecture, context: AgentContext, 
                                           research_results: List[Dict[str, Any]]) -> str:
        """Generate enhanced architecture document with technology context"""
        doc = f"# System Architecture\n\n"
        doc += f"**Project:** {context.project_name}\n"
        doc += f"**Project Type:** {context.project_type.value}\n"
        doc += f"**Complexity:** {context.complexity_level}\n\n"
        
        doc += f"## Architecture Pattern\n"
        doc += f"**Pattern:** {architecture.architecture_pattern}\n"
        doc += f"**Rationale:** {architecture.architecture_style}\n\n"

        doc += "## System Components\n\n"
        for comp in architecture.system_components:
            doc += f"### {comp.name}\n"
            doc += f"**Responsibility:** {comp.responsibility}\n"
            doc += f"**Technology:** {comp.technology}\n"
            doc += f"**Interfaces:**\n"
            for interface in comp.interfaces:
                doc += f"- {interface}\n"
            doc += "\n"

        doc += "## Data Flow\n\n"
        for flow in architecture.data_flow:
            doc += f"- **{flow.from_component}** → **{flow.to_component}**\n"
            doc += f"  - Data: {flow.data}\n"
            doc += f"  - Protocol: {flow.protocol}\n\n"

        doc += "## Security Architecture\n\n"
        for sec in architecture.security_architecture:
            doc += f"- {sec}\n"

        doc += "\n## Scalability Strategy\n\n"
        doc += f"**Horizontal Scaling:** {architecture.scalability_strategy.horizontal_scaling}\n\n"
        doc += f"**Load Balancing:** {architecture.scalability_strategy.load_balancing}\n\n"
        doc += f"**Caching:** {architecture.scalability_strategy.caching}\n\n"

        doc += "## Technology Decisions\n\n"
        doc += f"- **Backend Framework:** {architecture.technology_decisions.backend_framework}\n"
        doc += f"- **Frontend Framework:** {architecture.technology_decisions.frontend_framework}\n"
        doc += f"- **Message Queue:** {architecture.technology_decisions.message_queue}\n"
        doc += f"**Monitoring:** {architecture.technology_decisions.monitoring}\n\n"

        doc += f"## Deployment Architecture\n\n{architecture.deployment_architecture}\n\n"

        if research_results:
            doc += f"\n## Research Insights\n"
            for idx, result in enumerate(research_results[:3], 1):
                doc += f"{idx}. **{result.get('title', '')}**: {result.get('body', '')[:200]}...\n"

            doc += f"\n---\n*Generated by AI-SOL Technology-Specific System Architect*\n"
        return doc
    
    def _generate_technology_specific_doc(self, architecture: Architecture, context: AgentContext) -> str:
        """Generate technology-specific implementation guide"""
        doc = f"# Technology Implementation Guide\n\n"
        
        doc += f"## Technology Stack Overview\n"
        doc += f"This project uses a modern technology stack optimized for {context.project_type.value} development.\n\n"
        
        doc += f"## Frontend Technology: {architecture.technology_decisions.frontend_framework}\n"
        doc += f"- **Architecture Pattern:** Component-based architecture\n"
        doc += f"- **State Management:** Recommended patterns for {architecture.technology_decisions.frontend_framework}\n"
        doc += f"- **Styling:** Modern CSS frameworks and component libraries\n"
        doc += f"**Testing:** Framework-specific testing tools\n\n"
        
        doc += f"## Backend Technology: {architecture.technology_decisions.backend_framework}\n"
        doc += f"- **Architecture Pattern:** {architecture.architecture_pattern}\n"
        doc += f"- **API Design:** {architecture.api_design.style} with {architecture.api_design.authentication}\n"
        doc += f"- **Database:** {architecture.database_design.primary_database}\n"
        doc += f"- **Caching:** {architecture.scalability_strategy.caching}\n\n"
        
        doc += f"## Implementation Guidelines\n"
        doc += f"1. Follow {architecture.technology_decisions.frontend_framework} best practices\n"
        doc += f"2. Implement {architecture.technology_decisions.backend_framework} patterns\n"
        doc += f"3. Use {architecture.database_design.primary_database} specific features\n"
        doc += f"4. Implement security measures: {', '.join(architecture.security_architecture)}\n\n"
        
        doc += f"## Development Workflow\n"
        doc += f"1. Set up development environment for {architecture.technology_decisions.frontend_framework} and {architecture.technology_decisions.backend_framework}\n"
        doc += f"2. Configure {architecture.database_design.primary_database} database\n"
        doc += f"3. Implement components following the defined architecture\n"
        doc += f"4. Test using framework-specific testing tools\n"
        doc += f"5. Deploy using {architecture.deployment_architecture}\n\n"
        
        doc += f"\n---\n*Generated by AI-SOL Technology-Specific System Architect*\n"
        return doc
    
    def _generate_architecture_doc(self, arch: AnyType, research: str) -> str:
        """Generate architecture document"""
        pattern = _safe_get(arch, "architecture_pattern", "unknown")
        style = _safe_get(arch, "architecture_style", "")
        doc = f"""# System Architecture

## Architecture Pattern
**Pattern:** {pattern}

**Rationale:** {style}

## System Components

"""
        components = _iterable_from(arch, "system_components")
        for comp in components:
            # comp may be dict or model
            name = _safe_get(comp, "name", "")
            responsibility = _safe_get(comp, "responsibility", "")
            technology = _safe_get(comp, "technology", "")
            interfaces = _safe_get(comp, "interfaces", []) or []
            doc += f"### {name}\n"
            doc += f"**Responsibility:** {responsibility}\n"
            doc += f"**Technology:** {technology}\n"
            doc += f"**Interfaces:**\n"
            for interface in interfaces:
                doc += f"- {interface}\n"
            doc += "\n"

        doc += "## Data Flow\n\n"
        flows = _iterable_from(arch, "data_flow")
        for flow in flows:
            from_c = _safe_get(flow, "from_component", "")
            to_c = _safe_get(flow, "to_component", "")
            data_field = _safe_get(flow, "data", "")
            protocol = _safe_get(flow, "protocol", "")
            doc += f"- **{from_c}** → **{to_c}**\n"
            doc += f"  - Data: {data_field}\n"
            doc += f"  - Protocol: {protocol}\n\n"

        doc += "## Security Architecture\n\n"
        security_items = _iterable_from(arch, "security_architecture")
        for sec in security_items:
            doc += f"- {sec}\n"

        doc += "\n## Scalability Strategy\n\n"
        scalability = _safe_get(arch, "scalability_strategy", {})
        doc += f"**Horizontal Scaling:** {_safe_get(scalability, 'horizontal_scaling', '')}\n\n"
        doc += f"**Load Balancing:** {_safe_get(scalability, 'load_balancing', '')}\n\n"
        doc += f"**Caching:** {_safe_get(scalability, 'caching', '')}\n\n"

        doc += "## Technology Decisions\n\n"
        tech = _safe_get(arch, "technology_decisions", {})
        if isinstance(tech, dict):
            items = tech.items()
        else:
            # try model-like
            try:
                items = tech.dict().items() if hasattr(tech, "dict") else []
            except Exception:
                items = []
        for key, value in items:
            doc += f"- **{key.replace('_', ' ').title()}:** {value}\n"

        doc += f"\n## Research Insights\n{research}\n"

        doc += f"\n---\n*Generated by AI-SOL System Architect*\n"

        return doc

    def _generate_db_schema(self, arch: AnyType) -> str:
        """Generate database schema document"""
        db = _safe_get(arch, "database_design", {})

        db_type = _safe_get(db, "type", "")
        primary = _safe_get(db, "primary_database", "")
        caching = _safe_get(db, "caching_strategy", "")

        doc = f"""# Database Schema

## Database Type
**Type:** {db_type}
**Primary Database:** {primary}
**Caching:** {caching}

## Entities

"""
        entities = _iterable_from(db, "entities")
        for entity in entities:
            name = _safe_get(entity, "name", "")
            attributes = _safe_get(entity, "attributes", []) or []
            relationships = _safe_get(entity, "relationships", []) or []

            doc += f"### {name}\n\n"
            doc += "**Attributes:**\n"
            for attr in attributes:
                doc += f"- {attr}\n"
            doc += "\n**Relationships:**\n"
            for rel in relationships:
                doc += f"- {rel}\n"
            doc += "\n"

        return doc

    def _generate_api_spec(self, arch: AnyType) -> str:
        """Generate API specification"""
        api = _safe_get(arch, "api_design", {})

        style = _safe_get(api, "style", "")
        auth = _safe_get(api, "authentication", "")

        doc = f"""# API Specification

## API Style
**Style:** {style}
**Authentication:** {auth}

## Endpoints

"""
        endpoints = _iterable_from(api, "endpoints")
        for endpoint in endpoints:
            method = _safe_get(endpoint, "method", "")
            path = _safe_get(endpoint, "path", "")
            purpose = _safe_get(endpoint, "purpose", "")
            doc += f"### {method} {path}\n\n"
            doc += f"**Purpose:** {purpose}\n\n"
            doc += "---\n\n"

        return doc

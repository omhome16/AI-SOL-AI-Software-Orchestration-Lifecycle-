from agents.base import BaseAgent
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from utils.project_classifier import ProjectClassifier, ProjectType, ComplexityLevel
from utils.context_manager import AgentContext, FunctionalRequirement, NonFunctionalRequirement, TechnologyStack
import asyncio


class FunctionalRequirement(BaseModel):
    id: str = Field(description="Unique identifier")
    description: str = Field(description="What the system should do")
    priority: str = Field(description="high|medium|low")
    acceptance_criteria: List[str] = Field(description="How to verify completion")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary"""
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "acceptance_criteria": self.acceptance_criteria
        }


class NonFunctionalRequirement(BaseModel):
    category: str = Field(description="performance|security|scalability|usability|reliability")
    description: str = Field(description="Quality attribute requirement")
    metrics: List[str] = Field(description="Measurable criteria")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary"""
        return {
            "category": self.category,
            "description": self.description,
            "metrics": self.metrics
        }


class TechnologyStack(BaseModel):
    backend: List[str] = Field(description="Backend technologies")
    frontend: List[str] = Field(description="Frontend technologies")
    database: List[str] = Field(description="Database technologies")
    devops: Optional[List[str]] = Field(default_factory=list, description="DevOps/Infrastructure tools")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary"""
        return {
            "backend": self.backend,
            "frontend": self.frontend,
            "database": self.database,
            "devops": self.devops
        }


class ProjectStructure(BaseModel):
    folders: Dict[str, List[str]] = Field(description="Folder structure with files")

    class Config:
        extra = "allow"

    @validator('folders', pre=True)
    def parse_folders(cls, v):
        if isinstance(v, str):
            # If it's a string, try to parse it or create a default structure
            return {
                "src": ["index.html", "style.css", "script.js"],
                "games": ["tic-tac-toe.js"],
                "assets": ["images/", "icons/"]
            }
        return v
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary"""
        return {"folders": self.folders}


class RequirementsAnalysis(BaseModel):
    functional_requirements: List[FunctionalRequirement] = Field(description="What the system does")
    non_functional_requirements: List[NonFunctionalRequirement] = Field(description="How well it does it")
    complexity: str = Field(description="low|medium|high")
    estimated_timeline: str = Field(description="Development time estimate")
    recommended_tech_stack: TechnologyStack = Field(description="Technology recommendations")
    project_structure: ProjectStructure = Field(description="Suggested project structure")
    risks: List[str] = Field(description="Potential risks and challenges")
    assumptions: List[str] = Field(description="Assumptions made during analysis")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary with nested models handled"""
        return {
            "functional_requirements": [fr.to_dict() for fr in self.functional_requirements],
            "non_functional_requirements": [nfr.to_dict() for nfr in self.non_functional_requirements],
            "complexity": self.complexity,
            "estimated_timeline": self.estimated_timeline,
            "recommended_tech_stack": self.recommended_tech_stack.to_dict(),
            "project_structure": self.project_structure.to_dict(),
            "risks": self.risks,
            "assumptions": self.assumptions
        }


class RequirementsAgent(BaseAgent):
    """Domain-aware requirements analyst that creates comprehensive specifications for any project type.

    Features:
    - Domain-aware analysis based on project type and industry
    - Context-driven requirements generation
    - Industry-specific best practices integration
    - Comprehensive functional and non-functional requirements
    - Technology stack recommendations based on project type
    - Risk assessment and timeline estimation
    """

    def get_functional_requirements(self, analysis: RequirementsAnalysis) -> List[FunctionalRequirement]:
        """Get the functional requirements."""
        return analysis.functional_requirements

    def get_non_functional_requirements(self, analysis: RequirementsAnalysis) -> List[NonFunctionalRequirement]:
        """Get the non-functional requirements."""
        return analysis.non_functional_requirements

    def __init__(self, tools: Any):
        super().__init__(
            name="requirements_analyst",
            tools=tools,
            temperature=0.1
        )

        # Initialize project classifier for domain awareness
        self.project_classifier = ProjectClassifier()

        # Domain-specific requirement templates
        self.domain_templates = self._initialize_domain_templates()

        self.system_prompt = """You are a Senior Requirements Analyst with expertise across multiple domains including web applications, mobile apps, backend APIs, enterprise systems, gaming, e-commerce, healthcare, finance, and more.

Your role is to analyze user requirements and create comprehensive, domain-specific technical specifications.

**Domain-Aware Analysis Framework:**
1. Classify project type and domain
2. Apply domain-specific requirements patterns
3. Research industry best practices
4. Generate comprehensive functional requirements
5. Define domain-appropriate non-functional requirements
6. Recommend technology stack based on domain needs
7. Assess complexity and estimate realistic timelines
8. Identify domain-specific risks and assumptions

**Analysis Principles:**
- Apply domain expertise to requirements analysis
- Consider industry standards and compliance requirements
- Research current best practices for the specific domain
- Provide realistic timeline estimates based on domain complexity
- Identify domain-specific risks and mitigation strategies
- Document assumptions clearly with domain context

CRITICAL: Respond with ONLY valid JSON matching the RequirementsAnalysis schema."""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Domain-aware requirements analysis with comprehensive context integration"""
        self.log("Starting domain-aware requirements analysis")

        try:
            project_id = state.get("project_name", "default_project")
            requirements_text = state.get("requirements", "")
            user_context = state.get("user_context", {})

            # Initialize checkpoint state for human interaction
            checkpoint_state = {
                "requires_review": state.get("requires_review", True),
                "review_stage": "requirements",
                "last_checkpoint": None,
                "modifications_needed": False
            }

            # Start timeline tracking
            self.update_timeline(project_id, "requirements", 0, "Initialization")

            # Step 1: Classify project and domain
            self.log("Classifying project type and domain", "info")
            self.update_timeline(project_id, "requirements", 20, "Project Classification")
            classification = self.project_classifier.classify_project(requirements_text)

            # Step 2: Create or load context
            context = self.load_context(project_id)
            if not context:
                self.log("Creating initial context from requirements", "info")
                context = self.context_manager.create_initial_context(
                    project_id=project_id,
                    project_name=project_id,
                    requirements=requirements_text,
                    project_type=classification.project_type
                )

            # Step 3: Domain-specific research
            self.log(f"Researching best practices for {classification.domain} domain", "info")
            self.update_timeline(project_id, "requirements", 40, "Domain Research")
            research_results = await self._conduct_domain_research(requirements_text, classification, user_context)

            # Step 4: Generate domain-specific requirements
            self.log("Generating domain-specific requirements", "info")
            self.update_timeline(project_id, "requirements", 60, "Requirements Generation")
            analysis = await self._generate_domain_specific_requirements(
                requirements_text, classification, research_results, context
            )

            # Human Interaction Checkpoint - Requirements Review
            if checkpoint_state["requires_review"]:
                checkpoint_state["last_checkpoint"] = "requirements_review"
                checkpoint_data = {
                    "stage": "requirements",
                    "analysis": analysis.to_dict(),  # Use the new to_dict() method
                    "requires_modification": False,
                    "modification_comments": []
                }
                
                # Store checkpoint data in state
                state["checkpoint_data"] = checkpoint_data
                state["awaiting_review"] = True
                
                # Return early if human review is needed
                if not user_context.get("skip_review", False):
                    return {
                        "status": "awaiting_review",
                        "checkpoint_data": checkpoint_data,
                        "message": "Requirements analysis complete. Awaiting human review."
                    }

            # Step 5: Update context with analysis
            self.log("Updating context with requirements analysis", "info")
            self.update_timeline(project_id, "requirements", 80, "Context Update")
            self._update_context_with_analysis(context, analysis)

            # Step 6: Generate comprehensive documentation
            self.log("Generating requirements documentation", "info")
            self.update_timeline(project_id, "requirements", 90, "Documentation")
            generated_docs = await self._generate_comprehensive_docs(analysis, requirements_text, research_results,
                                                                     classification)

            # Step 7: Complete timeline tracking
            self.update_timeline(project_id, "requirements", 100, "Complete")

            # Create output using to_dict() for proper serialization
            output = self.create_output(
                success=True,
                data=analysis.to_dict(),  # Use the new to_dict() method
                documents=generated_docs,
                artifacts=[doc["path"] for doc in generated_docs]
            )

            self.update_project_state(project_id, "requirements", output)

            # Save updated context
            self.context_manager.save_context(project_id, context)

            self.log(
                f"Domain-aware analysis complete: {len(analysis.functional_requirements)} functional, {len(analysis.non_functional_requirements)} non-functional",
                "success")

            return {
                "requirements_output": output,
                "generated_documents": generated_docs,
                "generated_files": [doc["path"] for doc in generated_docs],
                "steps_completed": ["requirements"],
                "checkpoint_state": checkpoint_state
            }

        except Exception as e:
            self.log(f"Error in domain-aware requirements analysis: {str(e)}", "error")
            error_output = self.create_output(
                success=False,
                data={},
                errors=[str(e)]
            )
            
            # Ensure the error state is properly serialized
            if hasattr(error_output, 'to_dict'):
                error_output = error_output.to_dict()
                
            return {
                "requirements_output": error_output,
                "errors": [{"agent": self.name, "error": str(e)}]
            }

    def _initialize_domain_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize domain-specific requirement templates"""
        return {
            "e-commerce": {
                "functional_patterns": [
                    "User registration and authentication",
                    "Product catalog and search",
                    "Shopping cart and checkout",
                    "Payment processing",
                    "Order management",
                    "Inventory tracking",
                    "Customer reviews and ratings",
                    "Admin dashboard"
                ],
                "non_functional_patterns": [
                    {"category": "security", "description": "PCI DSS compliance for payment processing"},
                    {"category": "performance", "description": "High availability during peak shopping periods"},
                    {"category": "scalability", "description": "Handle seasonal traffic spikes"}
                ],
                "tech_recommendations": {
                    "backend": ["Node.js", "Python", "Java"],
                    "frontend": ["React", "Vue.js", "Angular"],
                    "database": ["PostgreSQL", "MongoDB", "Redis"],
                    "infrastructure": ["AWS", "Docker", "Kubernetes"]
                }
            },
            "gaming": {
                "functional_patterns": [
                    "Game mechanics and rules",
                    "Player management",
                    "Score tracking and leaderboards",
                    "Multiplayer functionality",
                    "Game state persistence",
                    "Real-time updates",
                    "Achievement system"
                ],
                "non_functional_patterns": [
                    {"category": "performance", "description": "Low latency for real-time gameplay"},
                    {"category": "scalability", "description": "Support concurrent players"},
                    {"category": "reliability", "description": "Minimal downtime for gaming sessions"}
                ],
                "tech_recommendations": {
                    "backend": ["Node.js", "Go", "C++"],
                    "frontend": ["JavaScript", "Unity", "Unreal Engine"],
                    "database": ["Redis", "MongoDB", "PostgreSQL"],
                    "infrastructure": ["WebSocket", "Docker", "AWS"]
                }
            },
            "healthcare": {
                "functional_patterns": [
                    "Patient management system",
                    "Medical records management",
                    "Appointment scheduling",
                    "Prescription management",
                    "Billing and insurance",
                    "Compliance reporting",
                    "Telemedicine features"
                ],
                "non_functional_patterns": [
                    {"category": "security", "description": "HIPAA compliance and data encryption"},
                    {"category": "reliability", "description": "High availability for critical medical data"},
                    {"category": "compliance", "description": "Audit trails and regulatory compliance"}
                ],
                "tech_recommendations": {
                    "backend": ["Java", "C#", "Python"],
                    "frontend": ["React", "Angular", "Vue.js"],
                    "database": ["PostgreSQL", "Oracle", "SQL Server"],
                    "infrastructure": ["Azure", "AWS", "Docker"]
                }
            },
            "finance": {
                "functional_patterns": [
                    "Account management",
                    "Transaction processing",
                    "Risk assessment",
                    "Compliance monitoring",
                    "Reporting and analytics",
                    "Fraud detection",
                    "API for third-party integrations"
                ],
                "non_functional_patterns": [
                    {"category": "security", "description": "Bank-grade security and encryption"},
                    {"category": "compliance", "description": "SOX, PCI DSS, and other financial regulations"},
                    {"category": "performance", "description": "High-frequency transaction processing"}
                ],
                "tech_recommendations": {
                    "backend": ["Java", "C#", "Go"],
                    "frontend": ["React", "Angular"],
                    "database": ["Oracle", "PostgreSQL", "Redis"],
                    "infrastructure": ["AWS", "Azure", "Kubernetes"]
                }
            },
            "education": {
                "functional_patterns": [
                    "Student management",
                    "Course catalog and enrollment",
                    "Learning management system",
            "Data management and storage"
        ])

        non_functional_patterns = domain_template.get("non_functional_patterns", [
            {"category": "performance", "description": "System performance requirements"},
            {"category": "security", "description": "Security and data protection"}
        ])

        tech_recommendations = domain_template.get("tech_recommendations", {
            "backend": ["Python", "Node.js"],
            "frontend": ["React", "Vue.js"],
            "database": ["PostgreSQL", "MongoDB"],
            "infrastructure": ["Docker", "AWS"]
        })

        # Create functional requirements from patterns
        functional_reqs = []
        for i, pattern in enumerate(functional_patterns[:5], 1):
            functional_reqs.append(FunctionalRequirement(
                id=f"FR-{i:03d}",
                description=pattern,
                priority="high" if i <= 2 else "medium",
                acceptance_criteria=[f"System implements {pattern.lower()}"]
            ))

        # Create non-functional requirements from patterns
        non_functional_reqs = []
        for pattern in non_functional_patterns:
            non_functional_reqs.append(NonFunctionalRequirement(
                category=pattern["category"],
                description=pattern["description"],
                metrics=[f"Meet {pattern['category']} standards"]
            ))

        return RequirementsAnalysis(
            functional_requirements=functional_reqs,
            non_functional_requirements=non_functional_reqs,
            complexity=classification.complexity.value,
            estimated_timeline=f"{classification.estimated_duration_hours // 8} days",
            recommended_tech_stack=TechnologyStack(
                backend=tech_recommendations.get("backend", []),
                frontend=tech_recommendations.get("frontend", []),
                database=tech_recommendations.get("database", []),
                devops=tech_recommendations.get("infrastructure", [])
            ),
            project_structure=ProjectStructure(
                folders=self._get_default_project_structure(classification.project_type.value)
            ),
            risks=self._get_domain_risks(classification.domain),
            assumptions=self._get_domain_assumptions(classification.domain)
        )

    def _get_default_project_structure(self, project_type: str) -> Dict[str, List[str]]:
        """Get default project structure based on project type"""
        structures = {
            "web_application": {
                "src": ["index.html", "style.css", "script.js"],
                "assets": ["images/", "icons/"],
                "docs": ["README.md"]
            },
            "backend_api": {
                "app": ["main.py", "config.py"],
                "api": ["routes.py", "models.py"],
                "tests": ["test_api.py"],
                "docs": ["README.md", "API.md"]
            },
            "mobile_app": {
                "src": ["App.js", "index.js"],
                "components": ["Button.js", "Header.js"],
                "screens": ["Home.js", "Profile.js"],
                "assets": ["images/", "fonts/"]
            },
            "full_stack": {
                "frontend": ["src/", "public/"],
                "backend": ["app/", "api/"],
                "shared": ["types/", "utils/"],
                "docs": ["README.md"]
            }
        }

        return structures.get(project_type, structures["web_application"])

    def _get_domain_risks(self, domain: str) -> List[str]:
        """Get domain-specific risks"""
        risk_map = {
            "e-commerce": ["Payment security", "Scalability during peak times", "Data privacy compliance"],
            "healthcare": ["HIPAA compliance", "Data security", "Regulatory changes"],
            "finance": ["Security vulnerabilities", "Regulatory compliance", "Fraud prevention"],
            "gaming": ["Performance optimization", "Scalability", "User engagement"],
            "education": ["Accessibility compliance", "Data privacy", "Scalability"]
        }

        return risk_map.get(domain, ["Technical complexity", "User adoption", "Maintenance overhead"])

    def _get_domain_assumptions(self, domain: str) -> List[str]:
        """Get domain-specific assumptions"""
        assumption_map = {
            "e-commerce": ["Users have modern browsers", "Payment gateway integration available",
                           "SSL certificates available"],
            "healthcare": ["HIPAA-compliant infrastructure", "Medical staff training", "Regulatory approval"],
            "finance": ["Banking API access", "Compliance framework", "Security audit capability"],
            "gaming": ["Modern gaming devices", "Stable internet connection", "User engagement"],
            "education": ["Educational institution support", "Teacher training", "Student device access"]
        }

        return assumption_map.get(domain, ["Modern technology stack", "User training", "Infrastructure support"])

    def _update_context_with_analysis(self, context: AgentContext, analysis: RequirementsAnalysis):
        """Update context with requirements analysis results"""
        try:
            # Convert Pydantic models to plain dictionaries
            functional_reqs = [
                FunctionalRequirement(
                    id=req.id,
                    description=req.description,
                    priority=req.priority,
                    acceptance_criteria=req.acceptance_criteria
                ).to_dict()
                for req in analysis.functional_requirements
            ]

            non_functional_reqs = [
                NonFunctionalRequirement(
                    category=nfr.category,
                    description=nfr.description,
                    metrics=nfr.metrics
                ).to_dict()
                for nfr in analysis.non_functional_requirements
            ]

            tech_stack_dict = analysis.recommended_tech_stack.to_dict()

            # Update context with the serializable dictionaries
            context.functional_requirements = functional_reqs
            context.non_functional_requirements = non_functional_reqs
            context.technology_stack = TechnologyStack(**tech_stack_dict)
            context.complexity_level = analysis.complexity
            context.estimated_timeline = analysis.estimated_timeline

            # Save changes
            self.context_manager.save_context(context.project_id, context)

        except Exception as e:
            self.log(f"Error updating context: {str(e)}", "error")
            raise

    async def _generate_comprehensive_docs(self, analysis: RequirementsAnalysis, requirements: str,
                                           research_results: List[Dict[str, Any]], classification) -> List[
        Dict[str, str]]:
        """Generate comprehensive documentation"""
        generated_docs = []

        # Generate main requirements document
        req_doc_content = self._generate_enhanced_requirements_doc(analysis, requirements, research_results,
                                                                   classification)
        req_doc = self.save_document(analysis.project_name if hasattr(analysis, 'project_name') else 'project',
                                     "REQUIREMENTS", "docs/REQUIREMENTS.md", req_doc_content)
        if req_doc:
            generated_docs.append(req_doc)

        # Generate domain-specific documentation
        domain_doc_content = self._generate_domain_specific_doc(classification, analysis)
        domain_doc = self.save_document(analysis.project_name if hasattr(analysis, 'project_name') else 'project',
                                        "DOMAIN_ANALYSIS", "docs/DOMAIN_ANALYSIS.md", domain_doc_content)
        if domain_doc:
            generated_docs.append(domain_doc)

        return generated_docs

    def _generate_enhanced_requirements_doc(self, analysis: RequirementsAnalysis, original_requirements: str,
                                            research_results: List[Dict[str, Any]], classification) -> str:
        """Generate enhanced requirements document with domain context"""
        doc = f"# Requirements Analysis\n\n"
        doc += f"**Project:** {classification.project_name if hasattr(classification, 'project_name') else 'Unknown'}\n"
        doc += f"**Project Type:** {classification.project_type.value}\n"
        doc += f"**Domain:** {classification.domain}\n"
        doc += f"**Complexity:** {classification.complexity.value}\n\n"

        doc += f"## Original Requirements\n{original_requirements}\n\n"

        doc += "## Functional Requirements\n\n"
        for req in analysis.functional_requirements:
            doc += f"### {req.id} - {req.description}\n"
            doc += f"**Priority:** {req.priority}\n"
            doc += f"**Acceptance Criteria:**\n"
            for criteria in req.acceptance_criteria:
                doc += f"- {criteria}\n"
            doc += "\n"

        doc += "## Non-Functional Requirements\n\n"
        for req in analysis.non_functional_requirements:
            doc += f"### {req.category.title()}\n"
            doc += f"**Description:** {req.description}\n"
            doc += f"**Metrics:**\n"
            for metric in req.metrics:
                doc += f"- {metric}\n"
            doc += "\n"

        doc += f"## Project Assessment\n\n"
        doc += f"**Complexity:** {analysis.complexity}\n"
        doc += f"**Estimated Timeline:** {analysis.estimated_timeline}\n\n"

        doc += "## Technology Stack\n\n"
        tech = analysis.recommended_tech_stack
        doc += f"**Backend:** {', '.join(tech.backend)}\n"
        doc += f"**Frontend:** {', '.join(tech.frontend)}\n"
        doc += f"**Database:** {', '.join(tech.database)}\n"
        doc += f"**DevOps:** {', '.join(tech.devops)}\n\n"

        doc += "## Project Structure\n\n"
        for folder, files in analysis.project_structure.folders.items():
            doc += f"**{folder}/**\n"
            for file in files:
                doc += f"- {file}\n"
            doc += "\n"

        doc += "## Risks and Assumptions\n\n"
        doc += "**Risks:**\n"
        for risk in analysis.risks:
            doc += f"- {risk}\n"
        doc += "\n**Assumptions:**\n"
        for assumption in analysis.assumptions:
            doc += f"- {assumption}\n"

        if research_results:
            doc += f"\n## Research Insights\n"
            for idx, result in enumerate(research_results[:3], 1):
                doc += f"{idx}. **{result.get('title', '')}**: {result.get('body', '')[:200]}...\n"

        doc += "\n---\n*Generated by AI-SOL Domain-Aware Requirements Analyst*\n"
        return doc

    def _generate_domain_specific_doc(self, classification, analysis: RequirementsAnalysis) -> str:
        """Generate domain-specific analysis document"""
        doc = f"# Domain Analysis: {classification.domain}\n\n"

        doc += f"## Domain Overview\n"
        doc += f"This project falls under the **{classification.domain}** domain with **{classification.project_type.value}** architecture.\n\n"

        doc += f"## Domain-Specific Considerations\n"
        doc += f"- **Industry Standards:** {classification.domain} industry best practices\n"
        doc += f"- **Compliance Requirements:** Domain-specific regulatory requirements\n"
        doc += f"- **User Expectations:** {classification.domain} user experience patterns\n\n"

        doc += f"## Technology Recommendations\n"
        doc += f"Based on {classification.domain} domain expertise:\n"
        tech = analysis.recommended_tech_stack
        doc += f"- **Backend:** {', '.join(tech.backend)} (proven in {classification.domain})\n"
        doc += f"- **Frontend:** {', '.join(tech.frontend)} (suitable for {classification.domain} users)\n"
        doc += f"- **Database:** {', '.join(tech.database)} (scales for {classification.domain} data)\n\n"

        doc += f"## Domain-Specific Risks\n"
        for risk in analysis.risks:
            doc += f"- {risk}\n"

        doc += f"\n## Domain Assumptions\n"
        for assumption in analysis.assumptions:
            doc += f"- {assumption}\n"

        doc += "\n---\n*Generated by AI-SOL Domain-Aware Requirements Analyst*\n"
        return doc
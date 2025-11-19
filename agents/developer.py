from agents.base import BaseAgent
from typing import Dict, Any, List, Optional, Tuple
import re
from pydantic import BaseModel, Field
from utils.project_classifier import ProjectType
from utils.context_manager import AgentContext, TechnologyStack, FileTask, ProjectBlueprint
import asyncio
from pathlib import Path


class FileGenerationResult(BaseModel):
    """Result of file generation"""
    path: str
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    dependencies_used: List[str] = Field(default_factory=list)


class CodeValidationResult(BaseModel):
    """Result of code validation"""
    is_valid: bool
    syntax_errors: List[str] = Field(default_factory=list)
    missing_imports: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class DeveloperAgent(BaseAgent):
    """
    Cursor-style Developer Agent that generates production-ready code.
    
    Features:
    - Reads architect's blueprint and follows it exactly
    - Generates files in dependency order
    - Multi-pass generation with validation and refinement
    - Full context awareness of all generated files
    - Self-correcting code generation
    - Orchestrator can read, edit, and delete files
    """

    def __init__(self, tools: Any):
        super().__init__(
            name="developer",
            tools=tools,
            temperature=0.2
        )

        # System prompt for intelligent code generation
        self.system_prompt = (
            "You are an elite software engineer with expertise in all modern technologies. "
            "You generate complete, production-ready, working code based on architectural blueprints. "
            "You understand dependencies, imports, and how files connect together. "
            "You write clean, maintainable, and functional code that runs without errors. "
            "You NEVER use placeholders, TODOs, or incomplete implementations."
        )

        # Code parsing patterns
        self._code_fence_re = re.compile(r"```(?:[a-zA-Z0-9#+\-]*)\n(?P<code>.*?)\n```", re.DOTALL)
        self._tilde_fence_re = re.compile(r"~~~(?:[a-zA-Z0-9#+\-]*)\n(?P<code>.*?)\n~~~", re.DOTALL)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method - Cursor-style code generation"""
        self.log("Starting Cursor-style code generation", "info")

        try:
            project_id = state.get("project_name", "default_project")
            
            # Load comprehensive context
            context = self.load_context(project_id)
            if not context:
                return self._create_error_output("No context found for project")

            # Validate we have a blueprint from architect
            if not context.blueprint:
                return self._create_error_output("No blueprint found - architect must run first")

            # Start timeline tracking
            self.update_timeline(project_id, "development", 0, "Initialization")

            # Phase 1: Setup project structure
            self.log("Phase 1: Setting up project structure", "info")
            self.update_timeline(project_id, "development", 10, "Creating directories")
            await self._setup_project_structure(project_id, context.blueprint)

            # Phase 2: Generate files progressively
            self.log("Phase 2: Generating files in dependency order", "info")
            generation_results = await self._generate_files_from_blueprint(
                project_id, context
            )

            # Phase 3: Validate and refine
            self.log("Phase 3: Validating and refining code", "info")
            self.update_timeline(project_id, "development", 85, "Validating code")
            validation_results = await self._validate_and_refine_files(
                project_id, generation_results, context
            )

            # Phase 4: Final integration check
            self.log("Phase 4: Final integration check", "info")
            self.update_timeline(project_id, "development", 95, "Final checks")
            await self._perform_integration_check(project_id, context)

            # Complete
            self.update_timeline(project_id, "development", 100, "Complete")

            # Prepare output
            successful_files = [r.path for r in generation_results if r.success]
            failed_files = [r.path for r in generation_results if not r.success]

            output = self.create_output(
                success=len(failed_files) == 0,
                data={
                    "files_generated": len(successful_files),
                    "files_failed": len(failed_files),
                    "project_type": context.project_type.value,
                    "technology_stack": context.technology_stack.to_dict(),
                    "validation_summary": validation_results
                },
                artifacts=successful_files,
                errors=[f"Failed to generate {f}" for f in failed_files]
            )

            # Update project state
            self.update_project_state(project_id, "development", output)

            # Update context
            self.context_manager.update_context(project_id, {
                "generated_files": successful_files,
                "updated_at": context.updated_at
            })

            self.log(f"Code generation complete: {len(successful_files)} files created", "success")

            return {
                "developer_output": output,
                "generated_files": successful_files,
                "failed_files": failed_files,
                "steps_completed": ["developer"]
            }

        except Exception as e:
            self.log(f"Critical error in code generation: {str(e)}", "error")
            return self._create_error_output(str(e))

    async def _setup_project_structure(self, project_id: str, blueprint: ProjectBlueprint):
        """Create all directories from the blueprint"""
        workspace_path = self._get_workspace_path(project_id)
        
        for folder in blueprint.folder_structure:
            folder_path = Path(workspace_path) / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Create .gitkeep for empty directories
            gitkeep = folder_path / ".gitkeep"
            gitkeep.touch(exist_ok=True)
        
        self.log(f"Created {len(blueprint.folder_structure)} directories", "success")

    async def _generate_files_from_blueprint(
        self, 
        project_id: str, 
        context: AgentContext
    ) -> List[FileGenerationResult]:
        """Generate all files from the blueprint in dependency order"""
        
        if not context.blueprint or not context.blueprint.build_plan:
            self.log("No build plan found in blueprint", "error")
            return []

        build_plan = context.blueprint.build_plan
        total_files = len(build_plan)
        
        self.log(f"Generating {total_files} files in dependency order", "info")
        
        results: List[FileGenerationResult] = []
        code_cache: Dict[str, str] = {}  # Cache of generated file contents
        
        for idx, file_task in enumerate(build_plan):
            progress = 20 + int((idx / total_files) * 60)  # 20-80% range
            self.update_timeline(
                project_id, 
                "development", 
                progress, 
                f"Generating {file_task.path}"
            )
            
            self.log(f"[{idx+1}/{total_files}] Generating: {file_task.path}", "info")
            
            # Call public generate_file method
            result = await self.generate_file(
                file_task=file_task, 
                context=context, 
                code_cache=code_cache,
                project_id=project_id
            )
            
            results.append(result)
            
            # Add to cache if successful
            if result.success and result.content:
                code_cache[file_task.path] = result.content
        
        return results

    async def generate_file(
        self,
        file_task: FileTask,
        context: AgentContext,
        code_cache: Dict[str, str],
        project_id: str = None
    ) -> FileGenerationResult:
        """Generate a single file with full context awareness.
        
        This is the public method called by Orchestrator or internal loop.
        """
        # Fallback for project_id if called from Orchestrator
        if not project_id:
            project_id = context.project_name
            
        try:
            # Build comprehensive prompt
            prompt = self._build_file_generation_prompt(
                file_task, context, code_cache
            )
            
            # Call LLM
            raw_response = await self.call_llm(prompt)
            
            # Parse and clean code
            cleaned_code = self._parse_code_from_response(raw_response)
            
            if not cleaned_code or len(cleaned_code.strip()) < 10:
                self.log(f"LLM returned empty/invalid code for {file_task.path}", "error")
                return FileGenerationResult(
                    path=file_task.path,
                    success=False,
                    error="Empty or invalid code generated"
                )
            
            # Validate code before writing
            validation = await self._validate_code(cleaned_code, file_task, context)
            
            # If validation fails, try to fix
            if not validation.is_valid:
                self.log(f"Initial code for {file_task.path} has issues, attempting fix", "warning")
                cleaned_code = await self._fix_code_issues(
                    cleaned_code, file_task, validation, context, code_cache
                )
            
            # Write file
            file_path = self._build_file_path(project_id, file_task.path)
            write_result = self.call_tool("write_file", path=file_path, content=cleaned_code)
            
            if write_result.get("success"):
                self.log(f"✓ Successfully generated: {file_task.path}", "success")
                return FileGenerationResult(
                    path=file_path,
                    success=True,
                    content=cleaned_code,
                    dependencies_used=file_task.dependencies
                )
            else:
                error_msg = write_result.get("error", "Unknown write error")
                self.log(f"✗ Failed to write {file_task.path}: {error_msg}", "error")
                return FileGenerationResult(
                    path=file_task.path,
                    success=False,
                    error=error_msg
                )
        
        except Exception as e:
            self.log(f"Exception generating {file_task.path}: {e}", "error")
            return FileGenerationResult(
                path=file_task.path,
                success=False,
                error=str(e)
            )

    def _build_file_generation_prompt(
        self,
        file_task: FileTask,
        context: AgentContext,
        code_cache: Dict[str, str]
    ) -> str:
        """Build a comprehensive prompt for file generation"""
        
        prompt_parts = []
        
        # Header
        prompt_parts.append("# FILE GENERATION TASK")
        prompt_parts.append(f"\nYou are generating: **{file_task.path}**")
        prompt_parts.append(f"Purpose: {file_task.purpose}\n")
        
        # Project context
        prompt_parts.append("## PROJECT CONTEXT")
        prompt_parts.append(f"- Project: {context.project_name}")
        prompt_parts.append(f"- Type: {context.project_type.value}")
        prompt_parts.append(f"- Complexity: {context.complexity_level.value}")
        
        # Technology stack
        stack = context.technology_stack.to_dict()
        prompt_parts.append("\n## TECHNOLOGY STACK")
        for key, values in stack.items():
            if values:
                prompt_parts.append(f"- {key.title()}: {', '.join(values)}")
        
        # Architecture pattern
        if context.architecture_pattern:
            prompt_parts.append(f"\n## ARCHITECTURE PATTERN")
            prompt_parts.append(context.architecture_pattern)
        
        # Blueprint explanation
        if context.blueprint and context.blueprint.explanation:
            prompt_parts.append(f"\n## ARCHITECTURAL DECISION")
            prompt_parts.append(context.blueprint.explanation)
        
        # Functional requirements (relevant ones)
        if context.functional_requirements:
            prompt_parts.append("\n## FUNCTIONAL REQUIREMENTS")
            for req in context.functional_requirements[:5]:
                prompt_parts.append(f"- [{req.priority}] {req.description}")
        
        # Dependencies (show actual code)
        if file_task.dependencies:
            prompt_parts.append("\n## DEPENDENCY FILES")
            prompt_parts.append("Your file depends on these files. Study them carefully:\n")
            
            for dep_path in file_task.dependencies:
                dep_code = code_cache.get(dep_path)
                if dep_code:
                    # Show full dependency code (truncated if too long)
                    truncated = self._truncate_for_context(dep_code, 1500)
                    prompt_parts.append(f"### FILE: {dep_path}")
                    prompt_parts.append(f"```\n{truncated}\n```\n")
                else:
                    prompt_parts.append(f"### FILE: {dep_path}")
                    prompt_parts.append("(Not yet generated - you may need to handle this gracefully)\n")
        
        # Component specifications
        if context.component_specifications:
            prompt_parts.append("\n## COMPONENT SPECIFICATIONS")
            for comp in context.component_specifications[:3]:
                prompt_parts.append(f"- {comp.name}: {comp.description}")
        
        # Critical instructions
        prompt_parts.append("\n## CRITICAL INSTRUCTIONS")
        prompt_parts.append("1. Generate COMPLETE, WORKING code - NO placeholders or TODOs")
        prompt_parts.append("2. Ensure ALL imports are correct based on project structure")
        prompt_parts.append("3. Match the technology stack exactly")
        prompt_parts.append("4. Include proper error handling")
        prompt_parts.append("5. Add docstrings and helpful comments")
        prompt_parts.append("6. Make sure the code integrates with dependency files")
        prompt_parts.append("7. Follow best practices for the language/framework")
        prompt_parts.append("8. Return ONLY the raw code - no explanations, no markdown")
        
        prompt_parts.append(f"\n## YOUR TASK")
        prompt_parts.append(f"Generate the complete, production-ready code for: {file_task.path}")
        prompt_parts.append("\nReturn ONLY the code, nothing else:")
        
        return "\n".join(prompt_parts)

    def _truncate_for_context(self, code: str, max_chars: int) -> str:
        """Truncate code intelligently for context"""
        if len(code) <= max_chars:
            return code
        
        # Prioritize imports and class/function definitions
        lines = code.split('\n')
        important_lines = []
        other_lines = []
        
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith('import ') or 
                stripped.startswith('from ') or
                stripped.startswith('class ') or
                stripped.startswith('def ') or
                stripped.startswith('async def ')):
                important_lines.append(line)
            else:
                other_lines.append(line)
        
        # Combine important lines + truncated other lines
        important_code = '\n'.join(important_lines)
        remaining_space = max_chars - len(important_code)
        
        if remaining_space > 100:
            other_code = '\n'.join(other_lines[:remaining_space // 50])
            return important_code + '\n\n# ... (truncated for brevity) ...\n\n' + other_code
        
        return important_code + '\n\n# ... (truncated for brevity) ...'

    def _parse_code_from_response(self, response: str) -> str:
        """Extract code from LLM response, handling markdown fences"""
        if not response:
            return ""
        
        # Try to extract from code fences
        code_blocks = []
        
        for match in self._code_fence_re.finditer(response):
            code_blocks.append(match.group('code').strip())
        
        for match in self._tilde_fence_re.finditer(response):
            code_blocks.append(match.group('code').strip())
        
        if code_blocks:
            # Combine multiple code blocks if present
            return '\n\n'.join(code_blocks)
        
        # Fallback: clean up response
        cleaned = response.strip()
        
        # Remove common markdown artifacts
        cleaned = re.sub(r'^```[a-zA-Z0-9#+\-]*\n', '', cleaned)
        cleaned = re.sub(r'\n```$', '', cleaned)
        cleaned = re.sub(r'^~~~[a-zA-Z0-9#+\-]*\n', '', cleaned)
        cleaned = re.sub(r'\n~~~$', '', cleaned)
        
        # Remove common LLM preambles
        cleaned = re.sub(r'(?i)^(here\'s|here is|the code|generated code)[:\s]+', '', cleaned)
        
        return cleaned.strip()

    async def _validate_code(
        self,
        code: str,
        file_task: FileTask,
        context: AgentContext
    ) -> CodeValidationResult:
        """Validate generated code"""
        
        issues = []
        missing_imports = []
        suggestions = []
        
        # Basic checks
        if len(code.strip()) < 10:
            issues.append("Code is too short or empty")
        
        # Check for placeholders
        placeholder_patterns = [
            r'TODO', r'FIXME', r'placeholder', r'implement.*here',
            r'add.*code.*here', r'your.*code.*here'
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"Found placeholder pattern: {pattern}")
        
        # Language-specific validation
        file_ext = Path(file_task.path).suffix
        
        if file_ext == '.py':
            # Python validation
            try:
                compile(code, file_task.path, 'exec')
            except SyntaxError as e:
                issues.append(f"Python syntax error: {e}")
        
        elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            # JavaScript/TypeScript basic checks
            if 'function' not in code and 'const' not in code and 'class' not in code:
                suggestions.append("No functions or classes found")
        
        # Check for common imports based on tech stack
        if file_ext == '.py':
            # Case-insensitive check for Flask
            if any(t.lower() == 'flask' for t in context.technology_stack.backend):
                if 'from flask import' not in code and 'import flask' not in code:
                    if 'app' in code.lower():
                        missing_imports.append("Flask import might be missing")
            
            # Case-insensitive check for FastAPI
            if any(t.lower() == 'fastapi' for t in context.technology_stack.backend):
                if 'from fastapi import' not in code and 'import fastapi' not in code:
                    if 'app' in code.lower() or '@' in code:
                        missing_imports.append("FastAPI import might be missing")
        
        is_valid = len(issues) == 0
        
        return CodeValidationResult(
            is_valid=is_valid,
            syntax_errors=issues,
            missing_imports=missing_imports,
            suggestions=suggestions
        )

    async def _fix_code_issues(
        self,
        code: str,
        file_task: FileTask,
        validation: CodeValidationResult,
        context: AgentContext,
        code_cache: Dict[str, str]
    ) -> str:
        """Attempt to fix code issues"""
        
        self.log(f"Attempting to fix issues in {file_task.path}", "info")
        
        fix_prompt = f"""The following code has issues. Please fix them and return the corrected code.

**File**: {file_task.path}
**Purpose**: {file_task.purpose}

**Issues Found**:
"""
        
        if validation.syntax_errors:
            fix_prompt += "\nSyntax Errors:\n"
            for error in validation.syntax_errors:
                fix_prompt += f"- {error}\n"
        
        if validation.missing_imports:
            fix_prompt += "\nMissing Imports:\n"
            for imp in validation.missing_imports:
                fix_prompt += f"- {imp}\n"
        
        if validation.suggestions:
            fix_prompt += "\nSuggestions:\n"
            for sug in validation.suggestions:
                fix_prompt += f"- {sug}\n"
        
        fix_prompt += f"""

**Current Code**:
```
{code}
```

**Instructions**:
1. Fix ALL the issues listed above
2. Ensure the code is complete and functional
3. Remove any placeholders or TODOs
4. Make sure imports are correct
5. Return ONLY the fixed code, no explanations

Fixed code:"""
        
        try:
            fixed_response = await self.call_llm(fix_prompt)
            fixed_code = self._parse_code_from_response(fixed_response)
            
            if fixed_code and len(fixed_code) > len(code) * 0.5:
                self.log(f"Successfully fixed code for {file_task.path}", "success")
                return fixed_code
            else:
                self.log(f"Fix attempt didn't improve code, using original", "warning")
                return code
        
        except Exception as e:
            self.log(f"Error fixing code: {e}", "error")
            return code

    async def _validate_and_refine_files(
        self,
        project_id: str,
        generation_results: List[FileGenerationResult],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Validate all generated files and refine if needed"""
        
        validation_summary = {
            "total_files": len(generation_results),
            "successful": 0,
            "failed": 0,
            "refined": 0
        }
        
        for result in generation_results:
            if result.success:
                validation_summary["successful"] += 1
            else:
                validation_summary["failed"] += 1
        
        self.log(f"Validation complete: {validation_summary['successful']}/{validation_summary['total_files']} successful", "info")
        
        return validation_summary

    async def _perform_integration_check(
        self,
        project_id: str,
        context: AgentContext
    ):
        """Perform final integration checks"""
        
        # Generate integration report
        workspace_path = self._get_workspace_path(project_id)
        
        integration_report = f"""# Integration Report for {context.project_name}

## Project Overview
- Type: {context.project_type.value}
- Complexity: {context.complexity_level.value}
- Files Generated: {len(context.generated_files)}

## Technology Stack
"""
        
        stack = context.technology_stack.to_dict()
        for key, values in stack.items():
            if values:
                integration_report += f"- {key.title()}: {', '.join(values)}\n"
        
        integration_report += """

## Next Steps
1. Review generated files
2. Install dependencies
3. Run tests
4. Deploy application

## Notes
All files have been generated according to the architectural blueprint.
The orchestrator can now read, edit, or delete any files as needed.
"""
        
        # Save integration report
        report_path = f"{workspace_path}/INTEGRATION_REPORT.md"
        self.call_tool("write_file", path=report_path, content=integration_report)
        
        self.log("Integration check complete", "success")

    def _get_workspace_path(self, project_id: str) -> str:
        """Get workspace path for project"""
        workspace_base = getattr(self, 'workspace_dir', './workspace')
        return f"{workspace_base}/{project_id}"

    def _build_file_path(self, project_id: str, relative_path: str) -> str:
        """Build absolute file path"""
        workspace_path = self._get_workspace_path(project_id)
        return f"{workspace_path}/{relative_path}"

    def _create_error_output(self, error_message: str) -> Dict[str, Any]:
        """Create error output"""
        return {
            "developer_output": self.create_output(
                success=False,
                data={},
                errors=[error_message]
            ),
            "errors": [{"agent": self.name, "error": error_message}]
        }
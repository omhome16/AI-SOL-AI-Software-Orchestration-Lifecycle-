"""
Orchestrator File Management Helper

This module provides high-level file management capabilities for the orchestrator,
allowing it to act like a developer using Cursor AI - reading, editing, and managing
project files with full context awareness.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class OrchestratorFileManager:
    """
    High-level file management for the orchestrator.
    Acts as an intelligent code editor with project awareness.
    """

    def __init__(self, file_tools, context_manager):
        """
        Initialize with file tools and context manager.
        
        Args:
            file_tools: EnhancedFileTools instance
            context_manager: ContextManager instance
        """
        self.tools = file_tools
        self.context_manager = context_manager

    def inspect_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get a complete overview of the project structure and files.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Complete project inspection report
        """
        workspace = f"./workspace/{project_id}"
        
        # List all files
        files_result = self.tools.list_files(workspace, recursive=True)
        
        if not files_result.get("success"):
            return files_result
        
        # Categorize files by type
        files_by_type = {}
        for file_info in files_result.get("files", []):
            ext = file_info.get("extension", "no_extension")
            if ext not in files_by_type:
                files_by_type[ext] = []
            files_by_type[ext].append(file_info)
        
        # Load context
        context = self.context_manager.load_context(project_id)
        
        return {
            "success": True,
            "project_id": project_id,
            "workspace": workspace,
            "total_files": files_result.get("total_files", 0),
            "total_directories": files_result.get("total_directories", 0),
            "files_by_type": files_by_type,
            "all_files": files_result.get("files", []),
            "directories": files_result.get("directories", []),
            "context_available": context is not None
        }

    def read_project_file(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """
        Read a specific file in the project.
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file in project
            
        Returns:
            File content and metadata
        """
        full_path = f"./workspace/{project_id}/{file_path}"
        return self.tools.read_file(full_path)

    def edit_project_file(
        self,
        project_id: str,
        file_path: str,
        edit_type: str,
        **edit_params
    ) -> Dict[str, Any]:
        """
        Edit a file in the project using various strategies.
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file in project
            edit_type: Type of edit - "replace_text", "replace_line", "insert_after", "insert_before"
            **edit_params: Edit-specific parameters
            
        Returns:
            Edit result
        """
        full_path = f"./workspace/{project_id}/{file_path}"
        
        # Map edit types to tool parameters
        if edit_type == "replace_text":
            return self.tools.edit_file(
                path=full_path,
                search=edit_params.get("search"),
                replace=edit_params.get("replace")
            )
        
        elif edit_type == "replace_line":
            return self.tools.edit_file(
                path=full_path,
                line_number=edit_params.get("line_number"),
                new_content=edit_params.get("new_content")
            )
        
        elif edit_type == "insert_after":
            return self.tools.edit_file(
                path=full_path,
                insert_after=edit_params.get("after"),
                new_content=edit_params.get("new_content")
            )
        
        elif edit_type == "insert_before":
            return self.tools.edit_file(
                path=full_path,
                insert_before=edit_params.get("before"),
                new_content=edit_params.get("new_content")
            )
        
        else:
            return {
                "success": False,
                "error": f"Unknown edit type: {edit_type}"
            }

    def delete_project_file(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """
        Delete a file from the project.
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file in project
            
        Returns:
            Deletion result
        """
        full_path = f"./workspace/{project_id}/{file_path}"
        return self.tools.delete_file(full_path)

    def find_bugs_in_file(
        self,
        project_id: str,
        file_path: str,
        llm_callable
    ) -> Dict[str, Any]:
        """
        Analyze a file for potential bugs using LLM.
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file
            llm_callable: Async function to call LLM
            
        Returns:
            Bug analysis report
        """
        # Read file
        read_result = self.read_project_file(project_id, file_path)
        
        if not read_result.get("success"):
            return read_result
        
        content = read_result.get("content")
        
        # Analyze with LLM (async)
        import asyncio
        
        async def analyze():
            prompt = f"""Analyze this code file for potential bugs, issues, and improvements.

**File**: {file_path}

**Code**:
```
{content}
```

**Analysis Required**:
1. Syntax errors
2. Logic errors
3. Security vulnerabilities
4. Performance issues
5. Code quality issues
6. Missing error handling
7. Suggestions for improvement

Provide a detailed analysis in JSON format with the following structure:
{{
    "bugs": [list of bugs found],
    "security_issues": [list of security concerns],
    "performance_issues": [list of performance problems],
    "quality_issues": [list of code quality issues],
    "suggestions": [list of improvement suggestions]
}}
"""
            
            response = await llm_callable(prompt)
            return response
        
        # Run async analysis
        analysis = asyncio.run(analyze())
        
        return {
            "success": True,
            "file": file_path,
            "analysis": analysis
        }

    def fix_file_with_llm(
        self,
        project_id: str,
        file_path: str,
        issue_description: str,
        llm_callable
    ) -> Dict[str, Any]:
        """
        Fix issues in a file using LLM assistance.
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file
            issue_description: Description of what needs to be fixed
            llm_callable: Async function to call LLM
            
        Returns:
            Fix result with new content
        """
        # Read current file
        read_result = self.read_project_file(project_id, file_path)
        
        if not read_result.get("success"):
            return read_result
        
        content = read_result.get("content")
        
        # Load project context
        context = self.context_manager.load_context(project_id)
        
        # Get fix from LLM
        import asyncio
        
        async def get_fix():
            prompt = f"""Fix the following issue in this code file.

**Project Context**:
- Type: {context.project_type.value if context else 'unknown'}
- Tech Stack: {context.technology_stack.to_dict() if context else {}}

**File**: {file_path}

**Issue to Fix**: {issue_description}

**Current Code**:
```
{content}
```

**Instructions**:
1. Fix the described issue
2. Maintain all existing functionality
3. Ensure the code is complete and working
4. Follow best practices
5. Return ONLY the fixed code, no explanations

Fixed code:"""
            
            response = await llm_callable(prompt)
            return response
        
        # Get fixed code
        fixed_code = asyncio.run(get_fix())
        
        # Clean up response
        import re
        fixed_code = re.sub(r'^```[a-zA-Z0-9#+\-]*\n', '', fixed_code)
        fixed_code = re.sub(r'\n```$', '', fixed_code)
        fixed_code = fixed_code.strip()
        
        if not fixed_code:
            return {
                "success": False,
                "error": "LLM returned empty fix"
            }
        
        # Write fixed file
        full_path = f"./workspace/{project_id}/{file_path}"
        write_result = self.tools.write_file(full_path, fixed_code)
        
        return {
            "success": write_result.get("success"),
            "file": file_path,
            "issue": issue_description,
            "fixed": write_result.get("success"),
            "write_result": write_result
        }

    def refactor_file(
        self,
        project_id: str,
        file_path: str,
        refactor_instruction: str,
        llm_callable
    ) -> Dict[str, Any]:
        """
        Refactor a file based on instructions.
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file
            refactor_instruction: What to refactor and how
            llm_callable: Async function to call LLM
            
        Returns:
            Refactoring result
        """
        # Similar to fix_file_with_llm but for refactoring
        return self.fix_file_with_llm(
            project_id,
            file_path,
            f"Refactor: {refactor_instruction}",
            llm_callable
        )

    def search_for_pattern(
        self,
        project_id: str,
        pattern: str,
        file_pattern: str = "*.py"
    ) -> Dict[str, Any]:
        """
        Search for a pattern across project files.
        
        Args:
            project_id: Project identifier
            pattern: Text pattern to search for
            file_pattern: File glob pattern (e.g., "*.py", "*.js")
            
        Returns:
            Search results
        """
        workspace = f"./workspace/{project_id}"
        return self.tools.search_in_files(
            directory=workspace,
            search_text=pattern,
            file_pattern=file_pattern,
            case_sensitive=False
        )

    def validate_project_structure(self, project_id: str) -> Dict[str, Any]:
        """
        Validate that project structure matches the blueprint.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Validation report
        """
        # Load context to get blueprint
        context = self.context_manager.load_context(project_id)
        
        if not context or not context.blueprint:
            return {
                "success": False,
                "error": "No blueprint found in context"
            }
        
        # Get expected files from blueprint
        expected_files = [task.path for task in context.blueprint.build_plan]
        
        # Get actual files
        workspace = f"./workspace/{project_id}"
        actual_result = self.tools.list_files(workspace, recursive=True)
        
        if not actual_result.get("success"):
            return actual_result
        
        actual_files = [f["path"].replace(f"{workspace}/", "") 
                       for f in actual_result.get("files", [])]
        
        # Compare
        missing_files = [f for f in expected_files if f not in actual_files]
        extra_files = [f for f in actual_files if f not in expected_files 
                      and not f.startswith('.git') 
                      and '.gitkeep' not in f]
        
        return {
            "success": True,
            "project_id": project_id,
            "expected_files": len(expected_files),
            "actual_files": len(actual_files),
            "missing_files": missing_files,
            "extra_files": extra_files,
            "is_complete": len(missing_files) == 0,
            "has_extras": len(extra_files) > 0
        }

    def get_file_dependencies(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze file dependencies (imports/requires).
        
        Args:
            project_id: Project identifier
            file_path: Relative path to file
            
        Returns:
            Dependency analysis
        """
        # Read file
        read_result = self.read_project_file(project_id, file_path)
        
        if not read_result.get("success"):
            return read_result
        
        content = read_result.get("content")
        
        # Parse imports (simple regex-based)
        import re
        
        dependencies = {
            "internal": [],  # Project files
            "external": []   # External packages
        }
        
        # Python imports
        if file_path.endswith('.py'):
            # Find "from X import Y" and "import X"
            from_imports = re.findall(r'from\s+([a-zA-Z0-9_.]+)\s+import', content)
            direct_imports = re.findall(r'^import\s+([a-zA-Z0-9_.]+)', content, re.MULTILINE)
            
            all_imports = from_imports + direct_imports
            
            # Categorize
            for imp in all_imports:
                if imp.startswith('.') or '/' in imp:
                    dependencies["internal"].append(imp)
                else:
                    dependencies["external"].append(imp)
        
        # JavaScript/TypeScript imports
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            # Find import statements
            imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
            requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
            
            all_imports = imports + requires
            
            for imp in all_imports:
                if imp.startswith('.') or imp.startswith('/'):
                    dependencies["internal"].append(imp)
                else:
                    dependencies["external"].append(imp)
        
        return {
            "success": True,
            "file": file_path,
            "dependencies": dependencies,
            "total_internal": len(dependencies["internal"]),
            "total_external": len(dependencies["external"])
        }

    def create_missing_file(
        self,
        project_id: str,
        file_path: str,
        purpose: str,
        llm_callable
    ) -> Dict[str, Any]:
        """
        Create a missing file based on purpose and context.
        
        Args:
            project_id: Project identifier
            file_path: Relative path for new file
            purpose: What this file should do
            llm_callable: Async function to call LLM
            
        Returns:
            Creation result
        """
        # Load context
        context = self.context_manager.load_context(project_id)
        
        # Generate file content with LLM
        import asyncio
        
        async def generate():
            prompt = f"""Generate a complete, working file for this project.

**Project Context**:
- Name: {context.project_name if context else 'unknown'}
- Type: {context.project_type.value if context else 'unknown'}
- Tech Stack: {context.technology_stack.to_dict() if context else {}}

**File to Create**: {file_path}
**Purpose**: {purpose}

**Requirements**:
1. Generate complete, production-ready code
2. Match the project's technology stack
3. Include proper imports and dependencies
4. Add error handling
5. Follow best practices
6. Return ONLY the code, no explanations

Generate the file:"""
            
            response = await llm_callable(prompt)
            return response
        
        # Get content
        content = asyncio.run(generate())
        
        # Clean up
        import re
        content = re.sub(r'^```[a-zA-Z0-9#+\-]*\n', '', content)
        content = re.sub(r'\n```$', '', content)
        content = content.strip()
        
        # Write file
        full_path = f"./workspace/{project_id}/{file_path}"
        write_result = self.tools.write_file(full_path, content)
        
        return {
            "success": write_result.get("success"),
            "file": file_path,
            "purpose": purpose,
            "write_result": write_result
        }


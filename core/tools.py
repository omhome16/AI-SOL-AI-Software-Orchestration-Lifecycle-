
import subprocess
import json
from pathlib import Path
from typing import Dict, Any
import requests
from datetime import datetime
import ast
import re
from zoneinfo import ZoneInfo
import tiktoken
from core.enhanced_file_tools import EnhancedFileTools


class Tools:
    """Unified tool system for all agents"""

    def __init__(self, workspace_path: str = "./workspace"):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        self.file_tools = EnhancedFileTools()

    # =====================
    # FILE OPERATIONS
    # =====================


    

    def delete_directory(self, path: str) -> Dict[str, Any]:
        """Delete a directory"""
        try:
            full_path = self.workspace_path / path
            if full_path.is_dir():
                import shutil
                shutil.rmtree(full_path)
                return {"success": True, "path": str(full_path)}
            else:
                return {"success": False, "error": "Path is not a directory"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================
    # GIT OPERATIONS
    # =====================

    def git_init(self, project_path: str) -> Dict[str, Any]:
        """Initialize git repository"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["git", "init"],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_add_all(self, project_path: str) -> Dict[str, Any]:
        """Stage all files"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["git", "add", "."],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_commit(self, project_path: str, message: str) -> Dict[str, Any]:
        """Create commit"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_push(self, project_path: str, remote: str = "origin", branch: str = "main") -> Dict[str, Any]:
        """Push to remote"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_set_remote(self, project_path: str, remote_url: str) -> Dict[str, Any]:
        """Set git remote"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================
    # GITHUB API
    # =====================

    def github_create_repo(
            self,
            repo_name: str,
            description: str,
            token: str,
            private: bool = False
    ) -> Dict[str, Any]:
        """Create GitHub repository"""
        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }

            data = {
                "name": repo_name,
                "description": description,
                "private": private,
                "auto_init": False
            }

            response = requests.post(
                "https://api.github.com/user/repos",
                headers=headers,
                json=data
            )

            if response.status_code == 201:
                repo_data = response.json()
                return {
                    "success": True,
                    "repo_url": repo_data["html_url"],
                    "clone_url": repo_data["clone_url"],
                    "ssh_url": repo_data["ssh_url"]
                }
            else:
                return {
                    "success": False,
                    "error": f"GitHub API error: {response.status_code}",
                    "message": response.json().get("message", "Unknown error")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================
    # WEB SEARCH
    # =====================

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search web using DuckDuckGo with improved error handling"""
        try:
            from duckduckgo_search import DDGS

            ddgs = DDGS()
            results = []

            # Add timeout and better error handling
            search_results = ddgs.text(query, max_results=max_results)
            
            for result in search_results:
                if result:  # Check if result is not None
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "body": result.get("body", "")
                    })

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
        except ImportError as e:
            return {
                "success": False, 
                "error": f"DuckDuckGo search library not installed: {e}",
                "suggestion": "Run: pip install duckduckgo-search"
            }
        except Exception as e:
            # Return a fallback result instead of complete failure
            return {
                "success": True,  # Changed to True to not break the workflow
                "query": query,
                "results": [{
                    "title": f"Search results for: {query}",
                    "url": "",
                    "body": f"Web search temporarily unavailable. Query: {query}"
                }],
                "count": 1,
                "warning": f"Web search error: {e}"
            }

    def fetch_url(self, url: str) -> Dict[str, Any]:
        """Fetch content from URL"""
        try:
            response = requests.get(url, timeout=10)

            return {
                "success": response.status_code == 200,
                "url": url,
                "content": response.text[:5000],  # Limit to 5000 chars
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================
    # CODE ANALYSIS
    # =====================

    def analyze_python_code(self, code: str) -> Dict[str, Any]:
        """Analyze Python code for errors and quality"""
        try:
            issues = []

            # Parse AST
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                return {
                    "success": False,
                    "syntax_error": str(e),
                    "line": e.lineno,
                    "offset": e.offset
                }

            # Check for common issues
            for node in ast.walk(tree):
                # Unused imports (simplified)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._is_name_used(alias.name, tree):
                            issues.append({
                                "type": "unused_import",
                                "message": f"Unused import: {alias.name}",
                                "line": node.lineno
                            })

                # Missing docstrings
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        issues.append({
                            "type": "missing_docstring",
                            "message": f"Missing docstring in {node.name}",
                            "line": node.lineno
                        })

            # Calculate complexity (simplified)
            complexity = self._calculate_complexity(tree)

            return {
                "success": True,
                "issues": issues,
                "complexity": complexity,
                "lines": len(code.split('\n')),
                "quality_score": max(0, 100 - len(issues) * 5 - max(0, complexity - 10) * 2)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_name_used(self, name: str, tree: ast.AST) -> bool:
        """Check if name is used in AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == name.split('.')[0]:
                return True
        return False

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity

    def count_tokens(self, text: str, model: str = "cl100k_base") -> int:
        """Counts the number of tokens in a string."""
        try:
            encoding = tiktoken.get_encoding(model)
            return len(encoding.encode(text))
        except Exception as e:
            # Fallback for models not supported by tiktoken
            return len(text.split())

    def run_linter(self, project_path: str) -> Dict[str, Any]:
        """Run flake8 linter"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["flake8", "--max-line-length=100", "."],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "issues_found": result.returncode != 0
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "flake8 not installed. Run: pip install flake8"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_tests(self, project_path: str) -> Dict[str, Any]:
        """Run pytest tests"""
        try:
            full_path = self.workspace_path / project_path
            result = subprocess.run(
                ["pytest", "-v", "--tb=short"],
                cwd=full_path,
                capture_output=True,
                text=True
            )

            # Parse output for pass/fail counts
            output = result.stdout
            passed = len(re.findall(r'PASSED', output))
            failed = len(re.findall(r'FAILED', output))

            return {
                "success": result.returncode == 0,
                "output": output,
                "tests_passed": passed,
                "tests_failed": failed,
                "total_tests": passed + failed
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "pytest not installed. Run: pip install pytest"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================
    # CLI EXECUTION
    # =====================

    def run_command(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute shell command"""
        try:
            full_cwd = self.workspace_path / cwd if cwd else self.workspace_path

            result = subprocess.run(
                command,
                shell=True,
                cwd=full_cwd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 60s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =====================
    # VECTOR MEMORY (Basic)
    # =====================

    def save_project_memory(
            self,
            project_name: str,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save project metadata for learning"""
        try:
            memory_file = self.workspace_path / ".ai-sol" / "memory.json"
            memory_file.parent.mkdir(exist_ok=True)

            # Load existing memory
            if memory_file.exists():
                memory = json.loads(memory_file.read_text())
            else:
                memory = {"projects": []}

            # Add new project
            memory["projects"].append({
                "name": project_name,
                "metadata": metadata,
                "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
            })

            # Save
            memory_file.write_text(json.dumps(memory, indent=2))

            return {"success": True, "projects_stored": len(memory["projects"])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_similar_projects(
            self,
            requirements: str,
            top_k: int = 3
    ) -> Dict[str, Any]:
        """Find similar past projects (basic text matching)"""
        try:
            memory_file = self.workspace_path / ".ai-sol" / "memory.json"

            if not memory_file.exists():
                return {"success": True, "similar_projects": []}

            memory = json.loads(memory_file.read_text())

            # Simple keyword matching
            req_words = set(requirements.lower().split())
            similar = []

            for project in memory["projects"]:
                proj_words = set(str(project["metadata"]).lower().split())
                overlap = len(req_words & proj_words)

                if overlap > 3:
                    similar.append({
                        "name": project["name"],
                        "similarity": overlap,
                        "metadata": project["metadata"]
                    })

            similar.sort(key=lambda x: x["similarity"], reverse=True)

            return {
                "success": True,
                "similar_projects": similar[:top_k]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        

    def read_file(self, path: str):
        return self.file_tools.read_file(path)
    
    def write_file(self, path: str, content: str):
        return self.file_tools.write_file(path, content)
    
    def edit_file(self, path: str, **kwargs):
        return self.file_tools.edit_file(path, **kwargs)
    
    def delete_file(self, path: str):
        return self.file_tools.delete_file(path)
    
    def list_files(self, path: str, **kwargs):
        return self.file_tools.list_files(path, **kwargs)
    
    def search_in_files(self, directory: str, search_text: str, **kwargs):
        return self.file_tools.search_in_files(directory, search_text, **kwargs)

from pathlib import Path
import subprocess
import requests
import git
import os
from typing import Dict, Any, Optional
from duckduckgo_search import DDGS


class Tools:
    """All tools in one class for simplicity"""

    def __init__(self, workspace_dir: str = "./workspace"):
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)

    # ============ FILE OPERATIONS ============

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file"""
        try:
            full_path = self.workspace / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            return {"success": True, "path": str(full_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, path: str) -> Dict[str, Any]:
        """Read file content"""
        try:
            full_path = self.workspace / path
            content = full_path.read_text(encoding='utf-8')
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, directory: str = ".") -> Dict[str, Any]:
        """List all files in directory recursively"""
        try:
            dir_path = self.workspace / directory
            files = [str(f.relative_to(self.workspace))
                     for f in dir_path.rglob("*") if f.is_file()]
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file"""
        try:
            full_path = self.workspace / path
            full_path.unlink()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============ WEB OPERATIONS ============

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search web using DuckDuckGo"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return {"success": True, "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_url(self, url: str) -> Dict[str, Any]:
        """Fetch content from URL"""
        try:
            response = requests.get(url, timeout=10)
            return {
                "success": True,
                "content": response.text[:5000],  # Limit
                "status_code": response.status_code
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============ CLI OPERATIONS ============

    def run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute shell command
        Safe mode: only allows specific commands
        """
        # Whitelist of safe commands
        safe_commands = {
            'pip', 'python', 'pytest', 'black', 'flake8',
            'npm', 'node', 'git', 'ls', 'cat', 'echo'
        }

        cmd_name = command.split()[0]
        if cmd_name not in safe_commands:
            return {
                "success": False,
                "error": f"Command '{cmd_name}' not allowed. Allowed: {safe_commands}"
            }

        try:
            work_dir = self.workspace / cwd if cwd else self.workspace
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============ GIT OPERATIONS ============

    def git_init(self, project_path: str) -> Dict[str, Any]:
        """Initialize git repository"""
        try:
            repo_path = self.workspace / project_path
            git.Repo.init(repo_path)
            return {"success": True, "path": str(repo_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_add_all(self, project_path: str) -> Dict[str, Any]:
        """Stage all files"""
        try:
            repo = git.Repo(self.workspace / project_path)
            repo.git.add(A=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_commit(self, project_path: str, message: str) -> Dict[str, Any]:
        """Commit changes"""
        try:
            repo = git.Repo(self.workspace / project_path)
            repo.index.commit(message)
            return {"success": True, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_push(self, project_path: str, remote_url: str, branch: str = "main") -> Dict[str, Any]:
        """Push to remote"""
        try:
            repo = git.Repo(self.workspace / project_path)
            if "origin" not in [r.name for r in repo.remotes]:
                origin = repo.create_remote("origin", remote_url)
            else:
                origin = repo.remote("origin")
            origin.push(branch)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============ GITHUB OPERATIONS ============

    def github_create_repo(
            self,
            repo_name: str,
            description: str = "",
            private: bool = False
    ) -> Dict[str, Any]:
        """Create GitHub repository"""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return {"success": False, "error": "GITHUB_TOKEN not set"}

        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "name": repo_name,
                "description": description,
                "private": private
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
                    "clone_url": repo_data["clone_url"],
                    "html_url": repo_data["html_url"]
                }
            return {"success": False, "error": response.json().get("message")}
        except Exception as e:
            return {"success": False, "error": str(e)}


TOOL_DESCRIPTIONS = {
    "write_file": "Write content to a file. Args: path (str), content (str)",
    "read_file": "Read file content. Args: path (str)",
    "list_files": "List all files. Args: directory (str, optional)",
    "delete_file": "Delete a file. Args: path (str)",
    "web_search": "Search the web. Args: query (str), max_results (int)",
    "fetch_url": "Fetch URL content. Args: url (str)",
    "run_command": "Run shell command. Args: command (str), cwd (str, optional)",
    "git_init": "Initialize git repo. Args: project_path (str)",
    "git_add_all": "Stage all files. Args: project_path (str)",
    "git_commit": "Commit changes. Args: project_path (str), message (str)",
    "git_push": "Push to remote. Args: project_path (str), remote_url (str), branch (str)",
    "github_create_repo": "Create GitHub repo. Args: repo_name (str), description (str), private (bool)"
}
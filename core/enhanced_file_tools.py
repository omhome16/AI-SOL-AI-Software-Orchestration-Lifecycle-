from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import shutil
import json


class EnhancedFileTools:
    """
    Enhanced file management tools for the orchestrator.
    Provides full CRUD operations on project files.
    """

    def __init__(self, base_workspace: str = "./workspace"):
        self.base_workspace = Path(base_workspace)
        self.base_workspace.mkdir(parents=True, exist_ok=True)

    def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read a file and return its contents.
        
        Args:
            path: Full path to the file
            
        Returns:
            Dict with success status and content or error
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {path}"
                }
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file metadata
            stat = file_path.stat()
            
            return {
                "success": True,
                "path": str(file_path),
                "content": content,
                "size": stat.st_size,
                "lines": len(content.splitlines()),
                "extension": file_path.suffix
            }
        
        except UnicodeDecodeError:
            # Handle binary files
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                return {
                    "success": True,
                    "path": str(file_path),
                    "content": f"[Binary file: {len(content)} bytes]",
                    "size": len(content),
                    "is_binary": True
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error reading binary file: {str(e)}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file: {str(e)}"
            }

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file. Creates directories if needed.
        
        Args:
            path: Full path to the file
            content: Content to write
            
        Returns:
            Dict with success status
        """
        try:
            file_path = Path(path)
            
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(file_path),
                "message": f"File written successfully: {file_path.name}",
                "size": len(content),
                "lines": len(content.splitlines())
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error writing file: {str(e)}"
            }

    def edit_file(
        self, 
        path: str, 
        search: Optional[str] = None,
        replace: Optional[str] = None,
        line_number: Optional[int] = None,
        new_content: Optional[str] = None,
        insert_after: Optional[str] = None,
        insert_before: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit a file using various strategies.
        
        Strategies:
        1. search + replace: Replace all occurrences of search with replace
        2. line_number + new_content: Replace specific line
        3. insert_after + new_content: Insert content after matching line
        4. insert_before + new_content: Insert content before matching line
        
        Args:
            path: Full path to the file
            search: Text to search for
            replace: Text to replace with
            line_number: Line number to replace (1-indexed)
            new_content: New content to insert/replace
            insert_after: Insert new_content after this line
            insert_before: Insert new_content before this line
            
        Returns:
            Dict with success status and changes made
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            lines = content.splitlines(keepends=True)
            
            # Strategy 1: Search and replace
            if search is not None and replace is not None:
                if search in content:
                    count = content.count(search)
                    content = content.replace(search, replace)
                    
                    # Write modified content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return {
                        "success": True,
                        "path": str(file_path),
                        "message": f"Replaced {count} occurrence(s) of search text",
                        "changes": count,
                        "strategy": "search_replace"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Search text not found in file"
                    }
            
            # Strategy 2: Replace specific line
            elif line_number is not None and new_content is not None:
                if 1 <= line_number <= len(lines):
                    lines[line_number - 1] = new_content + '\n'
                    content = ''.join(lines)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return {
                        "success": True,
                        "path": str(file_path),
                        "message": f"Replaced line {line_number}",
                        "strategy": "line_replace"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Line number {line_number} out of range (1-{len(lines)})"
                    }
            
            # Strategy 3: Insert after matching line
            elif insert_after is not None and new_content is not None:
                new_lines = []
                inserted = False
                
                for line in lines:
                    new_lines.append(line)
                    if insert_after in line:
                        new_lines.append(new_content + '\n')
                        inserted = True
                
                if inserted:
                    content = ''.join(new_lines)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return {
                        "success": True,
                        "path": str(file_path),
                        "message": f"Inserted content after matching line",
                        "strategy": "insert_after"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Could not find line containing: {insert_after}"
                    }
            
            # Strategy 4: Insert before matching line
            elif insert_before is not None and new_content is not None:
                new_lines = []
                inserted = False
                
                for line in lines:
                    if insert_before in line:
                        new_lines.append(new_content + '\n')
                        inserted = True
                    new_lines.append(line)
                
                if inserted:
                    content = ''.join(new_lines)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return {
                        "success": True,
                        "path": str(file_path),
                        "message": f"Inserted content before matching line",
                        "strategy": "insert_before"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Could not find line containing: {insert_before}"
                    }
            
            else:
                return {
                    "success": False,
                    "error": "No valid edit strategy provided"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error editing file: {str(e)}"
            }

    def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            path: Full path to the file
            
        Returns:
            Dict with success status
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            if file_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is a directory, use delete_directory instead: {path}"
                }
            
            # Delete file
            file_path.unlink()
            
            return {
                "success": True,
                "path": str(file_path),
                "message": f"File deleted successfully: {file_path.name}"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error deleting file: {str(e)}"
            }

    def delete_directory(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """
        Delete a directory.
        
        Args:
            path: Full path to the directory
            recursive: If True, delete directory and all contents
            
        Returns:
            Dict with success status
        """
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {path}"
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}"
                }
            
            if recursive:
                shutil.rmtree(dir_path)
                message = f"Directory and contents deleted: {dir_path.name}"
            else:
                # Only delete if empty
                if list(dir_path.iterdir()):
                    return {
                        "success": False,
                        "error": f"Directory is not empty. Use recursive=True to delete contents."
                    }
                dir_path.rmdir()
                message = f"Empty directory deleted: {dir_path.name}"
            
            return {
                "success": True,
                "path": str(dir_path),
                "message": message
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error deleting directory: {str(e)}"
            }

    def list_files(
        self, 
        path: str, 
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List files in a directory.
        
        Args:
            path: Directory path
            recursive: If True, list files recursively
            pattern: Glob pattern to filter files (e.g., "*.py")
            
        Returns:
            Dict with success status and list of files
        """
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {path}"
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}"
                }
            
            files = []
            directories = []
            
            if recursive:
                if pattern:
                    paths = dir_path.rglob(pattern)
                else:
                    paths = dir_path.rglob("*")
            else:
                if pattern:
                    paths = dir_path.glob(pattern)
                else:
                    paths = dir_path.glob("*")
            
            for p in paths:
                if p.is_file():
                    stat = p.stat()
                    files.append({
                        "name": p.name,
                        "path": str(p),
                        "size": stat.st_size,
                        "extension": p.suffix
                    })
                elif p.is_dir():
                    directories.append({
                        "name": p.name,
                        "path": str(p)
                    })
            
            return {
                "success": True,
                "path": str(dir_path),
                "files": files,
                "directories": directories,
                "total_files": len(files),
                "total_directories": len(directories)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing files: {str(e)}"
            }

    def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Move or rename a file.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Dict with success status
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source file not found: {source}"
                }
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(source_path), str(dest_path))
            
            return {
                "success": True,
                "source": str(source_path),
                "destination": str(dest_path),
                "message": f"File moved successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error moving file: {str(e)}"
            }

    def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copy a file.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Dict with success status
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source file not found: {source}"
                }
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(str(source_path), str(dest_path))
            
            return {
                "success": True,
                "source": str(source_path),
                "destination": str(dest_path),
                "message": f"File copied successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error copying file: {str(e)}"
            }

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file.
        
        Args:
            path: File path
            
        Returns:
            Dict with file information
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            stat = file_path.stat()
            
            info = {
                "success": True,
                "path": str(file_path),
                "name": file_path.name,
                "extension": file_path.suffix,
                "size": stat.st_size,
                "size_human": self._human_readable_size(stat.st_size),
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir(),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            }
            
            # Add line count for text files
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        info["lines"] = len(content.splitlines())
                        info["characters"] = len(content)
                except:
                    info["is_binary"] = True
            
            return info
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting file info: {str(e)}"
            }

    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def search_in_files(
        self, 
        directory: str, 
        search_text: str,
        file_pattern: str = "*",
        case_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Search for text in files.
        
        Args:
            directory: Directory to search in
            search_text: Text to search for
            file_pattern: File pattern to match (e.g., "*.py")
            case_sensitive: Whether search is case sensitive
            
        Returns:
            Dict with search results
        """
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}"
                }
            
            matches = []
            
            for file_path in dir_path.rglob(file_pattern):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Search in content
                        search_content = content if case_sensitive else content.lower()
                        search_target = search_text if case_sensitive else search_text.lower()
                        
                        if search_target in search_content:
                            # Find line numbers
                            lines = content.splitlines()
                            line_matches = []
                            
                            for i, line in enumerate(lines, 1):
                                line_search = line if case_sensitive else line.lower()
                                if search_target in line_search:
                                    line_matches.append({
                                        "line_number": i,
                                        "content": line.strip()
                                    })
                            
                            matches.append({
                                "file": str(file_path),
                                "matches": len(line_matches),
                                "lines": line_matches
                            })
                    
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue
            
            return {
                "success": True,
                "search_text": search_text,
                "directory": str(dir_path),
                "files_matched": len(matches),
                "results": matches
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching files: {str(e)}"
            }
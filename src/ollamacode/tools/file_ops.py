"""File operation tools for OllamaCode."""

import os
import pathlib
from typing import Optional, List
from rich.console import Console

from ..permissions import PermissionManager, OperationType
from ..diff_utils import DiffPreview
from ..error_handler import show_helpful_error

console = Console()


class FileOperations:
    """Handle file read/write operations."""
    
    def __init__(self, permission_manager: PermissionManager = None):
        self.permissions = permission_manager or PermissionManager()
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Read content from a file."""
        if not self.permissions.check_permission(OperationType.READ_FILE, f"read {file_path}"):
            return None
            
        try:
            path = pathlib.Path(file_path)
            if not path.exists():
                show_helpful_error("file reading", f"File not found: {file_path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            show_helpful_error("file reading", str(e))
            return None
    
    def write_file(self, file_path: str, content: str, show_diff: bool = True) -> bool:
        """Write content to a file with optional diff preview."""
        if not self.permissions.check_permission(OperationType.WRITE_FILE, f"write to {file_path}"):
            return False
            
        try:
            path = pathlib.Path(file_path)
            
            # Show diff preview if file exists and show_diff is enabled
            if show_diff and path.exists():
                original_content = self.read_file(file_path)
                if original_content is not None:
                    if not DiffPreview.show_diff_preview(original_content, content, file_path):
                        console.print("[yellow]Write operation cancelled by user.[/yellow]")
                        return False
            
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            console.print(f"[green]✓ Successfully wrote to {file_path}[/green]")
            return True
        except Exception as e:
            show_helpful_error("file writing", str(e))
            return False
    
    @staticmethod
    def list_files(directory: str = ".", pattern: str = "*") -> List[str]:
        """List files in a directory matching a pattern."""
        try:
            path = pathlib.Path(directory)
            if not path.exists():
                show_helpful_error("file listing", f"Directory not found: {directory}")
                return []
            
            files = list(path.glob(pattern))
            return [str(f) for f in files if f.is_file()]
        except Exception as e:
            show_helpful_error("file listing", str(e))
            return []
    
    @staticmethod
    def get_file_info(file_path: str) -> Optional[dict]:
        """Get file information."""
        try:
            path = pathlib.Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            return {
                "path": str(path.absolute()),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_file": path.is_file(),
                "is_dir": path.is_dir()
            }
        except Exception as e:
            console.print(f"[red]Error getting file info: {e}[/red]")
            return None
"""Search and grep operation tools for OllamaCode."""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

console = Console()


class SearchOperations:
    """Handle search and grep operations."""
    
    @staticmethod
    def grep_files(pattern: str, directory: str = ".", 
                   file_pattern: str = "*", ignore_case: bool = False,
                   recursive: bool = True, max_results: int = 100) -> List[Dict[str, Any]]:
        """Search for pattern in files using grep-like functionality."""
        results = []
        flags = re.IGNORECASE if ignore_case else 0
        
        try:
            compiled_pattern = re.compile(pattern, flags)
        except re.error as e:
            console.print(f"[red]Invalid regex pattern: {e}[/red]")
            return []
        
        search_path = Path(directory)
        if not search_path.exists():
            console.print(f"[red]Directory not found: {directory}[/red]")
            return []
        
        # Get files to search
        if recursive:
            files = search_path.rglob(file_pattern)
        else:
            files = search_path.glob(file_pattern)
        
        for file_path in files:
            if not file_path.is_file():
                continue
                
            # Skip binary files and common non-text files
            if SearchOperations._is_binary_file(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if compiled_pattern.search(line):
                            results.append({
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.rstrip(),
                                "match": compiled_pattern.search(line).group()
                            })
                            
                            if len(results) >= max_results:
                                return results
                                
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return results
    
    @staticmethod
    def find_files(name_pattern: str, directory: str = ".", 
                   recursive: bool = True) -> List[str]:
        """Find files by name pattern."""
        search_path = Path(directory)
        if not search_path.exists():
            console.print(f"[red]Directory not found: {directory}[/red]")
            return []
        
        files = []
        try:
            if recursive:
                matches = search_path.rglob(name_pattern)
            else:
                matches = search_path.glob(name_pattern)
            
            files = [str(f) for f in matches if f.is_file()]
        except Exception as e:
            console.print(f"[red]Error finding files: {e}[/red]")
            
        return files
    
    @staticmethod
    def _is_binary_file(file_path: Path) -> bool:
        """Check if file is likely binary."""
        # Common binary extensions
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso',
            '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.pyc', '.pyo', '.pyd', '.class', '.jar'
        }
        
        if file_path.suffix.lower() in binary_extensions:
            return True
        
        # Check first few bytes for null bytes (common in binary files)
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\0' in chunk:
                    return True
        except (PermissionError, OSError):
            return True
            
        return False
    
    @staticmethod
    def ripgrep_search(pattern: str, directory: str = ".", 
                      file_types: Optional[List[str]] = None,
                      ignore_case: bool = False) -> Optional[str]:
        """Use ripgrep if available for faster searching."""
        try:
            cmd = ["rg", pattern, directory]
            
            if ignore_case:
                cmd.append("-i")
            
            if file_types:
                for file_type in file_types:
                    cmd.extend(["-t", file_type])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else None
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
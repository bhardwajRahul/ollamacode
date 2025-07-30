"""Git operation tools for OllamaCode."""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from git import Repo, InvalidGitRepositoryError
from git.exc import GitCommandError

console = Console()


class GitOperations:
    """Handle git operations."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self._repo = None
        
    @property
    def repo(self) -> Optional[Repo]:
        """Get the git repository object."""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError:
                return None
        return self._repo
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        return self.repo is not None
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get git status information."""
        if not self.is_git_repo():
            console.print("[red]Not a git repository[/red]")
            return None
        
        try:
            repo = self.repo
            return {
                "branch": repo.active_branch.name,
                "commit": repo.head.commit.hexsha[:8],
                "modified": [item.a_path for item in repo.index.diff(None)],
                "staged": [item.a_path for item in repo.index.diff("HEAD")],
                "untracked": repo.untracked_files,
                "is_dirty": repo.is_dirty(),
            }
        except Exception as e:
            console.print(f"[red]Error getting git status: {e}[/red]")
            return None
    
    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> Optional[str]:
        """Get git diff output."""
        if not self.is_git_repo():
            console.print("[red]Not a git repository[/red]")
            return None
        
        try:
            repo = self.repo
            if staged:
                if file_path:
                    diff = repo.index.diff("HEAD", paths=file_path, create_patch=True)
                else:
                    diff = repo.index.diff("HEAD", create_patch=True)
            else:
                if file_path:
                    diff = repo.index.diff(None, paths=file_path, create_patch=True)
                else:
                    diff = repo.index.diff(None, create_patch=True)
            
            return "\n".join([item.diff.decode('utf-8') for item in diff])
        except Exception as e:
            console.print(f"[red]Error getting git diff: {e}[/red]")
            return None
    
    def add_files(self, files: List[str]) -> bool:
        """Add files to git staging area."""
        if not self.is_git_repo():
            console.print("[red]Not a git repository[/red]")
            return False
        
        try:
            repo = self.repo
            repo.index.add(files)
            return True
        except Exception as e:
            console.print(f"[red]Error adding files: {e}[/red]")
            return False
    
    def commit(self, message: str, author: Optional[str] = None) -> bool:
        """Create a commit."""
        if not self.is_git_repo():
            console.print("[red]Not a git repository[/red]")
            return False
        
        try:
            repo = self.repo
            if author:
                repo.index.commit(message, author=author)
            else:
                repo.index.commit(message)
            return True
        except Exception as e:
            console.print(f"[red]Error creating commit: {e}[/red]")
            return False
    
    def get_log(self, max_count: int = 10, file_path: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get git log entries."""
        if not self.is_git_repo():
            console.print("[red]Not a git repository[/red]")
            return None
        
        try:
            repo = self.repo
            if file_path:
                commits = list(repo.iter_commits(paths=file_path, max_count=max_count))
            else:
                commits = list(repo.iter_commits(max_count=max_count))
            
            return [
                {
                    "hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for commit in commits
            ]
        except Exception as e:
            console.print(f"[red]Error getting git log: {e}[/red]")
            return None
"""Context management for OllamaCode conversations."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rich.console import Console

console = Console()


class ContextManager:
    """Manage conversation context and project awareness."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).absolute()
        self.context_dir = self.project_root / ".ollamacode"
        self.context_file = self.context_dir / "context.json"
        self.conversations_dir = self.context_dir / "conversations"
        
        # Ensure directories exist
        self.context_dir.mkdir(exist_ok=True)
        self.conversations_dir.mkdir(exist_ok=True)
        
        self._context = self._load_context()
    
    def _load_context(self) -> Dict[str, Any]:
        """Load project context from file."""
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Default context
        return {
            "project_name": self.project_root.name,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "file_patterns": ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.c", "*.h"],
            "ignore_patterns": ["*.pyc", "node_modules/", "__pycache__/", ".git/", "*.egg-info/"],
            "important_files": [],
            "project_type": "unknown",
            "dependencies": [],
            "notes": []
        }
    
    def _save_context(self):
        """Save context to file."""
        self._context["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.context_file, 'w') as f:
                json.dump(self._context, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving context: {e}[/red]")
    
    def get_project_summary(self) -> str:
        """Generate a project summary for AI context."""
        summary_parts = [
            f"Project: {self._context['project_name']}",
            f"Type: {self._context['project_type']}",
            f"Root: {self.project_root}"
        ]
        
        if self._context['dependencies']:
            summary_parts.append(f"Dependencies: {', '.join(self._context['dependencies'])}")
        
        if self._context['important_files']:
            summary_parts.append(f"Key files: {', '.join(self._context['important_files'])}")
        
        if self._context['notes']:
            note_texts = [note['text'] if isinstance(note, dict) else str(note) for note in self._context['notes']]
            summary_parts.append(f"Notes: {'; '.join(note_texts)}")
        
        return "\n".join(summary_parts)
    
    def detect_project_type(self) -> str:
        """Auto-detect project type based on files."""
        project_indicators = {
            "python": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
            "javascript": ["package.json", "yarn.lock", "npm-shrinkwrap.json"],
            "typescript": ["tsconfig.json", "package.json"],
            "java": ["pom.xml", "build.gradle", "gradle.properties"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "go": ["go.mod", "go.sum"],
            "cpp": ["CMakeLists.txt", "Makefile", "configure.ac"],
            "web": ["index.html", "webpack.config.js", "vite.config.js"]
        }
        
        for project_type, indicators in project_indicators.items():
            for indicator in indicators:
                if (self.project_root / indicator).exists():
                    self._context["project_type"] = project_type
                    self._save_context()
                    return project_type
        
        return "unknown"
    
    def scan_important_files(self) -> List[str]:
        """Scan for important project files."""
        important_patterns = [
            "README*", "readme*", "LICENSE*", "CHANGELOG*",
            "setup.py", "pyproject.toml", "package.json", "Cargo.toml",
            "main.py", "index.js", "main.cpp", "main.c",
            "Dockerfile", "docker-compose.yml",
            ".gitignore", "requirements.txt"
        ]
        
        important_files = []
        for pattern in important_patterns:
            files = list(self.project_root.glob(pattern))
            important_files.extend([str(f.relative_to(self.project_root)) for f in files])
        
        self._context["important_files"] = important_files[:10]  # Limit to 10
        self._save_context()
        return important_files
    
    def save_conversation(self, conversation_id: str, messages: List[Dict[str, str]]):
        """Save conversation history."""
        conversation_file = self.conversations_dir / f"{conversation_id}.json"
        conversation_data = {
            "id": conversation_id,
            "created_at": datetime.now().isoformat(),
            "messages": messages,
            "project_context": self.get_project_summary()
        }
        
        try:
            with open(conversation_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving conversation: {e}[/red]")
    
    def load_conversation(self, conversation_id: str) -> Optional[List[Dict[str, str]]]:
        """Load conversation history."""
        conversation_file = self.conversations_dir / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            return None
        
        try:
            with open(conversation_file, 'r') as f:
                data = json.load(f)
                return data.get("messages", [])
        except Exception as e:
            console.print(f"[red]Error loading conversation: {e}[/red]")
            return None
    
    def list_conversations(self) -> List[Dict[str, str]]:
        """List all saved conversations."""
        conversations = []
        
        for conv_file in self.conversations_dir.glob("*.json"):
            try:
                with open(conv_file, 'r') as f:
                    data = json.load(f)
                    conversations.append({
                        "id": data.get("id", conv_file.stem),
                        "created_at": data.get("created_at", "unknown"),
                        "message_count": len(data.get("messages", []))
                    })
            except Exception:
                continue
        
        return sorted(conversations, key=lambda x: x["created_at"], reverse=True)
    
    def get_last_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent conversation session."""
        conversations = self.list_conversations()
        
        if not conversations:
            return None
        
        # Get the most recent conversation
        last_conv = conversations[0]
        conversation_file = self.conversations_dir / f"{last_conv['id']}.json"
        
        try:
            with open(conversation_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading last session: {e}[/red]")
            return None
    
    def add_note(self, note: str):
        """Add a project note."""
        self._context["notes"].append({
            "text": note,
            "timestamp": datetime.now().isoformat()
        })
        self._save_context()
    
    def get_file_context(self, file_path: str) -> str:
        """Get relevant context for a file."""
        file_path = Path(file_path)
        
        # Check if file is in important files
        is_important = str(file_path) in self._context.get("important_files", [])
        
        # Get file info
        context_parts = [f"File: {file_path}"]
        
        if is_important:
            context_parts.append("(Important project file)")
        
        # Add project context
        context_parts.append(self.get_project_summary())
        
        return "\n".join(context_parts)
"""Configuration management for OllamaCode."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console

console = Console()


class Config:
    """Manage OllamaCode configuration."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".ollamacode"
        self.config_file = self.config_dir / "config.json"
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                console.print("[yellow]Warning: Invalid config file, using defaults[/yellow]")
        
        # Default configuration
        return {
            "ollama_url": "http://localhost:11434",
            "default_model": "gemma3",
            "timeout": 120,
            "max_tokens": 4096,
            "temperature": 0.7,
            "editor": os.environ.get("EDITOR", "nano"),
            "auto_save_conversations": True,
            "show_context_hints": True,
            "safe_mode": True,
            "allowed_commands": [
                "ls", "cat", "grep", "find", "head", "tail", "wc", "sort", "uniq",
                "pwd", "whoami", "date", "echo", "which", "type",
                "git", "npm", "pip", "python", "python3", "node", "cargo", "go",
                "pytest", "jest", "mocha", "make", "cmake",
                "tree", "file", "stat", "du", "df"
            ],
            "feedback": {
                "endpoint_url": "http://100.76.97.90:8080/api/feedback",
                "api_key": "",
                "include_session_data": True,
                "enabled": True
            }
        }
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self._config[key] = value
        self.save_config()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values."""
        self._config.update(updates)
        self.save_config()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self._config = self._load_config.__func__(self)  # Call without loading from file
        self.save_config()
    
    def show_config(self) -> str:
        """Return formatted configuration."""
        return json.dumps(self._config, indent=2)
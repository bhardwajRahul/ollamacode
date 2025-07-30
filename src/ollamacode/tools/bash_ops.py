"""Bash operation tools for OllamaCode."""

import subprocess
import shlex
from typing import Optional, Dict, Any
from rich.console import Console

console = Console()


class BashOperations:
    """Handle bash command execution."""
    
    @staticmethod
    def run_command(command: str, cwd: Optional[str] = None, 
                   timeout: int = 30, capture_output: bool = True) -> Dict[str, Any]:
        """Execute a bash command safely."""
        
        # Security: only allow safe commands
        safe_commands = {
            'ls', 'cat', 'grep', 'find', 'head', 'tail', 'wc', 'sort', 'uniq',
            'pwd', 'whoami', 'date', 'echo', 'which', 'type',
            'git', 'npm', 'pip', 'python', 'python3', 'node', 'cargo', 'go',
            'pytest', 'jest', 'mocha', 'make', 'cmake',
            'tree', 'file', 'stat', 'du', 'df'
        }
        
        # Parse command to check if it's safe
        try:
            args = shlex.split(command)
            if not args:
                return {"success": False, "error": "Empty command"}
            
            base_command = args[0]
            
            # Check if base command is in safe list
            if base_command not in safe_commands:
                return {
                    "success": False, 
                    "error": f"Command '{base_command}' not allowed for security reasons"
                }
            
        except ValueError as e:
            return {"success": False, "error": f"Invalid command syntax: {e}"}
        
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": command
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Command not found: {base_command}",
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "command": command
            }
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """Get basic system information."""
        info = {}
        
        commands = {
            "os": "uname -s",
            "architecture": "uname -m", 
            "kernel": "uname -r",
            "user": "whoami",
            "pwd": "pwd",
            "shell": "echo $SHELL"
        }
        
        for key, cmd in commands.items():
            result = BashOperations.run_command(cmd, timeout=5)
            if result["success"]:
                info[key] = result["stdout"].strip()
            else:
                info[key] = "unknown"
        
        return info
    
    @staticmethod
    def check_tool_availability(tools: list) -> Dict[str, bool]:
        """Check if command-line tools are available."""
        availability = {}
        
        for tool in tools:
            result = BashOperations.run_command(f"which {tool}", timeout=5)
            availability[tool] = result["success"]
        
        return availability
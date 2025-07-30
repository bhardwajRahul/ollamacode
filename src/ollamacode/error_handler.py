"""Error handling utilities for OllamaCode."""

import sys
import traceback
from functools import wraps
from typing import Callable, Any
from rich.console import Console
from rich.panel import Panel

console = Console()


class OllamaCodeError(Exception):
    """Base exception for OllamaCode."""
    pass


class ModelNotAvailableError(OllamaCodeError):
    """Raised when the requested model is not available."""
    pass


class ServiceUnavailableError(OllamaCodeError):
    """Raised when Ollama service is not running."""
    pass


class FileOperationError(OllamaCodeError):
    """Raised when file operations fail."""
    pass


class GitOperationError(OllamaCodeError):
    """Raised when git operations fail."""
    pass


def handle_errors(func: Callable) -> Callable:
    """Decorator to handle common errors gracefully."""
    
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)
        except ServiceUnavailableError as e:
            console.print(f"[red]Ollama service error:[/red] {e}")
            console.print("[blue]💡 Try: [bold]ollama serve[/bold][/blue]")
            sys.exit(1)
        except ModelNotAvailableError as e:
            console.print(f"[red]Model error:[/red] {e}")
            console.print("[blue]💡 Try: [bold]ollama pull gemma3[/bold][/blue]")
            sys.exit(1)
        except FileOperationError as e:
            console.print(f"[red]File error:[/red] {e}")
            sys.exit(1)
        except GitOperationError as e:
            console.print(f"[red]Git error:[/red] {e}")
            console.print("[blue]💡 Make sure you're in a git repository[/blue]")
            sys.exit(1)
        except Exception as e:
            if sys.stdout.isatty():  # Only show detailed error in terminal
                console.print(Panel.fit(
                    f"[red]Unexpected error:[/red]\n{str(e)}\n\n"
                    f"[blue]Please report this at:[/blue]\n"
                    f"https://github.com/anthropics/claude-code/issues",
                    title="Error",
                    border_style="red"
                ))
                
                # Show traceback in debug mode
                if "--debug" in sys.argv:
                    console.print("\n[dim]Traceback:[/dim]")
                    console.print(traceback.format_exc())
            else:
                # Simple error for scripts/automation
                print(f"Error: {e}")
            
            sys.exit(1)
    
    return wrapper


def validate_model_availability(client) -> None:
    """Validate that the Ollama service and model are available."""
    if not client.is_available():
        raise ServiceUnavailableError(
            "Ollama service is not running. Start it with: ollama serve"
        )


def validate_git_repo(git_ops) -> None:
    """Validate that we're in a git repository."""
    if not git_ops.is_git_repo():
        raise GitOperationError(
            "Not in a git repository. Initialize with: git init"
        )


def show_helpful_error(command: str, error: str, suggestion: str = None):
    """Show a helpful error message with suggestions."""
    console.print(f"[red]Error in {command}:[/red] {error}")
    
    if suggestion:
        console.print(f"[blue]💡 Suggestion:[/blue] {suggestion}")
    
    # Generate contextual suggestions based on error patterns
    suggestions = _generate_error_suggestions(error, command)
    for sug in suggestions:
        console.print(f"[blue]💡 {sug}[/blue]")


def _generate_error_suggestions(error: str, command: str = "") -> list[str]:
    """Generate contextual error suggestions based on error content."""
    suggestions = []
    error_lower = error.lower()
    command_lower = command.lower()
    
    # Permission-related errors
    if any(term in error_lower for term in ["permission", "denied", "access"]):
        suggestions.extend([
            "Try running with appropriate permissions",
            "Use `/permissions approve-all` to approve all operations for this session",
            "Check if the file/directory is write-protected"
        ])
    
    # File/Path related errors
    elif any(term in error_lower for term in ["not found", "no such file", "does not exist"]):
        if "file" in command_lower:
            suggestions.extend([
                "Check if the file path is correct",
                "Use tab completion or `/complete @filename` to find files",
                "Try using absolute paths instead of relative paths"
            ])
        else:
            suggestions.extend([
                "Verify the file or directory exists",
                "Check for typos in the path",
                "Use `ls` to list available files"
            ])
    
    # Connection/Network errors
    elif any(term in error_lower for term in ["connection", "refused", "timeout", "unreachable"]):
        suggestions.extend([
            "Check if Ollama is running: `ollama serve`",
            "Verify the Ollama URL in config: `/config`",
            "Try switching to a different model: `/model gemma3`"
        ])
    
    # Model-related errors
    elif any(term in error_lower for term in ["model", "not available", "pull"]):
        suggestions.extend([
            "Pull the model: `ollama pull gemma3`",
            "List available models: `ollama list`",
            "Switch to a different model: `/model`"
        ])
    
    # Git-related errors
    elif any(term in error_lower for term in ["git", "repository", "not a git"]):
        suggestions.extend([
            "Initialize git repository: `git init`",
            "Check if you're in the correct directory",
            "Verify git is installed: `git --version`"
        ])
    
    # Memory/Resource errors
    elif any(term in error_lower for term in ["memory", "out of", "resource", "space"]):
        suggestions.extend([
            "Try a smaller model: `/model gemma3`",
            "Clear the cache: `/cache clear`",
            "Free up disk space or memory"
        ])
    
    # Import/Module errors
    elif any(term in error_lower for term in ["import", "module", "package"]):
        suggestions.extend([
            "Install missing dependencies: `pip install package_name`",
            "Check your Python environment",
            "Verify the package name is correct"
        ])
    
    # Syntax/Code errors
    elif any(term in error_lower for term in ["syntax", "invalid", "unexpected"]):
        suggestions.extend([
            "Check for syntax errors in your code",
            "Use syntax highlighting to identify issues",
            "Try simplifying the request"
        ])
    
    # Generic suggestions for common scenarios
    if not suggestions:
        if "file" in command_lower or "write" in command_lower:
            suggestions.extend([
                "Check file permissions and paths",
                "Ensure the directory exists",
                "Try using `/permissions status` to check current permissions"
            ])
        elif "git" in command_lower:
            suggestions.extend([
                "Ensure you're in a git repository",
                "Check git configuration",
                "Try `git status` to verify repository state"
            ])
        elif "model" in command_lower or "chat" in command_lower:
            suggestions.extend([
                "Verify Ollama is running: `ollama serve`",
                "Check available models: `ollama list`",
                "Try a different model if current one fails"
            ])
        else:
            suggestions.extend([
                "Try the operation again",
                "Check the command syntax",
                "Use `/help` for available commands"
            ])
    
    return suggestions


def create_detailed_error_message(error: Exception, context: str = "", user_action: str = "") -> str:
    """Create a detailed error message with context and suggestions."""
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Create a comprehensive error report
    parts = [
        f"[red bold]❌ {error_type}[/red bold]",
        f"[red]{error_msg}[/red]"
    ]
    
    if context:
        parts.append(f"[yellow]📍 Context:[/yellow] {context}")
    
    if user_action:
        parts.append(f"[cyan]🎯 User Action:[/cyan] {user_action}")
    
    # Add suggestions
    suggestions = _generate_error_suggestions(error_msg, context)
    if suggestions:
        parts.append("[blue bold]💡 Suggestions:[/blue bold]")
        for suggestion in suggestions[:3]:  # Limit to top 3 suggestions
            parts.append(f"  [blue]• {suggestion}[/blue]")
    
    # Add help resources
    parts.extend([
        "",
        "[dim]For more help:[/dim]",
        "[dim]• Type `/help` for available commands[/dim]",
        "[dim]• Visit: https://docs.anthropic.com/en/docs/claude-code[/dim]"
    ])
    
    return "\n".join(parts)
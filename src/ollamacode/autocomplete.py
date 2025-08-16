"""Auto-completion system for Ollamacode CLI commands and inputs."""

import re
from typing import List, Dict, Tuple, Optional
from rich.console import Console

console = Console()


class AutoCompleter:
    """Intelligent auto-completion for slash commands and inputs."""
    
    # Available slash commands with their arguments
    SLASH_COMMANDS = {
        'help': {
            'description': 'Show help information',
            'args': [],
            'examples': ['/help']
        },
        'clear': {
            'description': 'Clear conversation history',
            'args': [],
            'examples': ['/clear']
        },
        'exit': {
            'description': 'Exit Ollamacode CLI',
            'args': [],
            'examples': ['/exit', '/quit']
        },
        'quit': {
            'description': 'Exit Ollamacode CLI',
            'args': [],
            'examples': ['/quit', '/exit']
        },
        'model': {
            'description': 'Change or show current model',
            'args': ['[model_name]'],
            'examples': ['/model', '/model gemma3', '/model codellama'],
            'completions': ['gemma3', 'codellama', 'llama2', 'mistral', 'orca-mini']
        },
        'config': {
            'description': 'Show current configuration',
            'args': [],
            'examples': ['/config']
        },
        'status': {
            'description': 'Show session and project status',
            'args': [],
            'examples': ['/status']
        },
        'sessions': {
            'description': 'List saved sessions',
            'args': [],
            'examples': ['/sessions']
        },
        'permissions': {
            'description': 'Manage operation permissions',
            'args': ['status|reset|approve-all'],
            'examples': ['/permissions status', '/permissions reset', '/permissions approve-all'],
            'completions': ['status', 'reset', 'approve-all']
        },
        'cache': {
            'description': 'Manage response cache',
            'args': ['status|clear|stats'],
            'examples': ['/cache status', '/cache clear', '/cache stats'],
            'completions': ['status', 'clear', 'stats']
        }
    }
    
    # Common file extensions for @filename completion
    CODE_EXTENSIONS = [
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
        '.rs', '.go', '.rb', '.php', '.swift', '.kt', '.scala', '.cs', '.vb',
        '.r', '.m', '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1',
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.md', '.rst', '.txt', '.log'
    ]
    
    @classmethod
    def get_slash_completions(cls, partial_input: str) -> List[Tuple[str, str]]:
        """Get completions for slash commands.
        
        Returns list of (completion, description) tuples.
        """
        if not partial_input.startswith('/'):
            return []
        
        # Remove the leading slash
        input_without_slash = partial_input[1:]
        parts = input_without_slash.split(' ')
        command = parts[0]
        
        completions = []
        
        if len(parts) == 1:
            # Completing command name
            for cmd_name, cmd_info in cls.SLASH_COMMANDS.items():
                if cmd_name.startswith(command):
                    full_cmd = f"/{cmd_name}"
                    description = cmd_info['description']
                    completions.append((full_cmd, description))
        
        elif len(parts) == 2 and command in cls.SLASH_COMMANDS:
            # Completing command arguments
            cmd_info = cls.SLASH_COMMANDS[command]
            if 'completions' in cmd_info:
                arg = parts[1]
                for completion in cmd_info['completions']:
                    if completion.startswith(arg):
                        full_cmd = f"/{command} {completion}"
                        description = f"{cmd_info['description']} - {completion}"
                        completions.append((full_cmd, description))
        
        return completions
    
    @classmethod
    def get_file_completions(cls, partial_path: str, current_dir: str = ".") -> List[str]:
        """Get file completions for @filename references."""
        import os
        import glob
        
        try:
            # Handle @filename pattern
            if partial_path.startswith('@'):
                partial_path = partial_path[1:]
            
            # If no path separator, look in current directory
            if '/' not in partial_path and '\\' not in partial_path:
                pattern = f"{current_dir}/{partial_path}*"
            else:
                pattern = f"{partial_path}*"
            
            matches = glob.glob(pattern)
            
            # Filter and format results
            completions = []
            for match in matches:
                # Prefer files with code extensions
                if any(match.endswith(ext) for ext in cls.CODE_EXTENSIONS):
                    completions.append(f"@{match}")
                elif os.path.isfile(match):
                    completions.append(f"@{match}")
            
            return sorted(completions[:10])  # Limit to 10 results
        
        except Exception:
            return []
    
    @classmethod
    def get_context_completions(cls, partial_input: str, context: Dict) -> List[Tuple[str, str]]:
        """Get context-aware completions based on project and session state."""
        completions = []
        input_lower = partial_input.lower()
        
        # Common coding-related completions
        if any(word in input_lower for word in ['help', 'how', 'explain', 'show']):
            suggestions = [
                ("explain this code", "Get explanation of code"),
                ("help me debug", "Get debugging assistance"),
                ("show me examples", "See code examples"),
                ("how do I", "Get how-to guidance")
            ]
            completions.extend(suggestions)
        
        # File operation completions
        if any(word in input_lower for word in ['edit', 'modify', 'change', 'update']):
            suggestions = [
                ("edit the file", "Modify an existing file"),
                ("update the code", "Make changes to code"),
                ("modify the function", "Change a specific function")
            ]
            completions.extend(suggestions)
        
        # Git operation completions
        if any(word in input_lower for word in ['git', 'commit', 'branch', 'merge']):
            suggestions = [
                ("git status", "Check repository status"),
                ("show git log", "View commit history"),
                ("git diff", "See changes in files")
            ]
            completions.extend(suggestions)
        
        return completions
    
    @classmethod
    def suggest_completions(cls, partial_input: str, context: Optional[Dict] = None) -> Dict[str, List]:
        """Get all available completions for the given input."""
        suggestions = {
            'slash_commands': [],
            'file_references': [],
            'context_suggestions': []
        }
        
        if not partial_input:
            return suggestions
        
        # Slash command completions
        if partial_input.startswith('/'):
            suggestions['slash_commands'] = cls.get_slash_completions(partial_input)
        
        # File reference completions
        at_match = re.search(r'@([^\s]*)$', partial_input)
        if at_match:
            file_partial = at_match.group(1)
            suggestions['file_references'] = cls.get_file_completions(f"@{file_partial}")
        
        # Context-aware suggestions
        if context:
            suggestions['context_suggestions'] = cls.get_context_completions(partial_input, context)
        
        return suggestions
    
    @classmethod
    def format_completion_display(cls, suggestions: Dict[str, List]) -> str:
        """Format completion suggestions for display."""
        output = []
        
        if suggestions['slash_commands']:
            output.append("[bold blue]Slash Commands:[/bold blue]")
            for cmd, desc in suggestions['slash_commands'][:5]:  # Show top 5
                output.append(f"  [cyan]{cmd}[/cyan] - {desc}")
        
        if suggestions['file_references']:
            output.append("\n[bold green]File References:[/bold green]")
            for file_ref in suggestions['file_references'][:5]:  # Show top 5
                output.append(f"  [green]{file_ref}[/green]")
        
        if suggestions['context_suggestions']:
            output.append("\n[bold yellow]Suggestions:[/bold yellow]")
            for suggestion, desc in suggestions['context_suggestions'][:3]:  # Show top 3
                output.append(f"  [yellow]{suggestion}[/yellow] - {desc}")
        
        return "\n".join(output) if output else ""
    
    @classmethod
    def get_command_help(cls, command: str) -> str:
        """Get detailed help for a specific command."""
        if not command.startswith('/'):
            command = f"/{command}"
        
        command_name = command[1:]  # Remove leading slash
        
        if command_name not in cls.SLASH_COMMANDS:
            return f"[red]Unknown command: {command}[/red]"
        
        cmd_info = cls.SLASH_COMMANDS[command_name]
        
        help_parts = [
            f"[bold blue]{command}[/bold blue] - {cmd_info['description']}"
        ]
        
        if cmd_info['args']:
            args_str = ' '.join(cmd_info['args'])
            help_parts.append(f"Usage: [cyan]{command} {args_str}[/cyan]")
        
        if cmd_info['examples']:
            help_parts.append("Examples:")
            for example in cmd_info['examples']:
                help_parts.append(f"  [dim]{example}[/dim]")
        
        return "\n".join(help_parts)
    
    @classmethod
    def is_complete_command(cls, input_text: str) -> bool:
        """Check if the input is a complete, valid command."""
        if not input_text.startswith('/'):
            return False
        
        parts = input_text[1:].split(' ')
        command = parts[0]
        
        if command not in cls.SLASH_COMMANDS:
            return False
        
        # Check if command has required arguments
        cmd_info = cls.SLASH_COMMANDS[command]
        if 'completions' in cmd_info and len(parts) == 1:
            # Command requires an argument but none provided
            return False
        
        return True
    
    @classmethod
    def get_all_commands(cls) -> List[str]:
        """Get list of all available slash commands."""
        return [f"/{cmd}" for cmd in cls.SLASH_COMMANDS.keys()]
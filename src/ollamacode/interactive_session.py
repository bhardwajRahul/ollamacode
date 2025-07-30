"""Interactive session management for OllamaCode."""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown

from .ollama_client import OllamaClient
from .tools import FileOperations, GitOperations, SearchOperations, BashOperations
from .context import ContextManager
from .config import Config
from .permissions import PermissionManager
from .syntax_highlighter import CodeHighlighter
from .autocomplete import AutoCompleter
from .error_handler import create_detailed_error_message, show_helpful_error

console = Console()


class InteractiveSession:
    """Manage an interactive OllamaCode session."""
    
    def __init__(self, model: str = None, url: str = None):
        self.config = Config()
        self.client = OllamaClient(
            base_url=url or self.config.get('ollama_url'),
            model=model or self.config.get('default_model')
        )
        
        # Initialize permission manager and tools
        self.permissions = PermissionManager()
        self.file_ops = FileOperations(self.permissions)
        self.git_ops = GitOperations()
        self.search_ops = SearchOperations()
        self.bash_ops = BashOperations()
        self.context_mgr = ContextManager()
        
        # Session state
        self.conversation_id = f"session_{int(datetime.now().timestamp())}"
        self.messages = []
        self.project_context_loaded = False
        
    def start(self, initial_prompt: str = None):
        """Start interactive session."""
        if not self.client.is_available():
            console.print("[red]Error: Ollama service is not available[/red]")
            console.print("Make sure Ollama is running: [bold]ollama serve[/bold]")
            sys.exit(1)
        
        # Auto-load project context if we're in a project
        self._auto_load_project_context()
        
        console.print(Panel.fit(
            f"🦙 OllamaCode Interactive Session\n"
            f"Model: [bold]{self.client.model}[/bold] | "
            f"Project: [bold]{self.context_mgr._context['project_name']}[/bold]",
            style="bold green"
        ))
        
        if self.project_context_loaded:
            console.print("[blue]🔍 Project context automatically loaded[/blue]")
        
        console.print("\n[dim]Type your request naturally. I can help with:\n"
                      "• File editing and code generation\n"  
                      "• Git operations and project analysis\n"
                      "• Running commands and searching code\n"
                      "• Project-aware assistance\n"
                      "Type 'exit' to quit, or try slash commands like /help[/dim]\n")
        
        # Process initial prompt if provided
        if initial_prompt:
            console.print(f"\n[bold blue]You[/bold blue]: {initial_prompt}")
            response = self._process_user_input(initial_prompt)
            # Only print Assistant label if response doesn't already include it
            if response and not response.startswith("\n[bold green]Assistant[/bold green]"):
                console.print(f"\n[bold green]Assistant[/bold green]:")
            
            # Use enhanced response printing
            if response:
                self._print_enhanced_response(response)
        
        self._main_loop()
    
    def run_headless(self, prompt: str, piped_input: str = None):
        """Run in headless mode with a single prompt."""
        if not self.client.is_available():
            console.print("[red]Error: Ollama service is not available[/red]")
            sys.exit(1)
        
        # Auto-load project context
        self._auto_load_project_context()
        
        # Combine prompt with piped input if available
        full_prompt = prompt
        if piped_input:
            full_prompt = f"{prompt}\n\nInput data:\n```\n{piped_input}\n```"
        
        try:
            response = self._process_user_input(full_prompt)
            console.print(response)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
    
    def continue_session(self):
        """Continue the last saved session."""
        if not self.client.is_available():
            console.print("[red]Error: Ollama service is not available[/red]")
            sys.exit(1)
        
        # Try to load last session
        last_session = self.context_mgr.get_last_session()
        if last_session:
            self.conversation_id = last_session['id']
            self.messages = last_session['messages']
            console.print(f"[green]Continuing session {self.conversation_id}[/green]")
            
            # Show last few messages for context
            if len(self.messages) > 1:
                console.print("\n[dim]Recent conversation:[/dim]")
                for msg in self.messages[-4:]:  # Show last 4 messages
                    if msg['role'] == 'user':
                        console.print(f"[blue]You[/blue]: {msg['content'][:100]}...")
                    elif msg['role'] == 'assistant':
                        console.print(f"[green]Assistant[/green]: {msg['content'][:100]}...")
        else:
            console.print("[yellow]No previous session found. Starting new session.[/yellow]")
        
        self.start()
    
    def _auto_load_project_context(self):
        """Automatically load project context if we're in a project."""
        project_type = self.context_mgr.detect_project_type()
        
        if project_type != "unknown":
            self.context_mgr.scan_important_files()
            project_summary = self.context_mgr.get_project_summary()
            
            context_message = f"""You are an AI coding assistant helping with a {project_type} project. Here's the project context:

{project_summary}

You have access to these tools:
- File operations (read, write, edit files)
- Git operations (status, diff, log, etc.)
- Code search and grep functionality  
- Safe command execution
- Project analysis and context awareness

When users ask for help, consider the project context and suggest relevant actions. Be proactive about offering to use tools when appropriate."""
            
            self.messages.append({"role": "system", "content": context_message})
            self.project_context_loaded = True
    
    def _main_loop(self):
        """Main interactive loop."""
        while True:
            try:
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self._save_and_exit()
                    break
                
                # Check for completion hints before processing
                self._maybe_show_completion_hints(user_input)
                
                # Process the user input
                response = self._process_user_input(user_input)
                
                # Only print Assistant label if response doesn't already include it
                if response and not response.startswith("\n[bold green]Assistant[/bold green]"):
                    console.print(f"\n[bold green]Assistant[/bold green]:")
                
                # Use enhanced response printing
                if response:
                    self._print_enhanced_response(response)
                
            except KeyboardInterrupt:
                self._save_and_exit()
                break
    
    def _process_user_input(self, user_input: str) -> str:
        """Process user input and determine appropriate response."""
        user_input = user_input.strip()
        
        # Handle slash commands
        if user_input.startswith('/'):
            return self._handle_slash_command(user_input)
        
        # Handle file references (@filename)
        user_input = self._process_file_references(user_input)
        
        self.messages.append({"role": "user", "content": user_input})
        
        # Check if this looks like a tool request
        if self._should_use_tools(user_input):
            return self._handle_tool_request(user_input)
        else:
            # Regular conversation
            return self._get_ai_response()
    
    def _should_use_tools(self, user_input: str) -> bool:
        """Determine if user input requires tool usage."""
        tool_keywords = [
            # File operations
            "edit", "modify", "change", "update", "create file", "write file",
            "read file", "show file", "open file", "content of", "show me",
            "write a file", "create a file", "make a file", "save to file",
            
            # Git operations  
            "git status", "git diff", "commit", "branch", "repo status",
            "changes", "modified files", "staging",
            
            # Search operations
            "find", "search", "grep", "look for", "locate",
            
            # Command execution
            "run", "execute", "command", "npm", "pip", "python", "test"
        ]
        
        lower_input = user_input.lower()
        return any(keyword in lower_input for keyword in tool_keywords)
    
    def _is_file_creation_request(self, user_input: str) -> bool:
        """Check if user input is requesting file creation."""
        creation_patterns = [
            "write a file", "create a file", "make a file", "save to file",
            "create file", "write file", "make file", "generate file",
            "write a script", "create a script", "make a script"
        ]
        
        lower_input = user_input.lower()
        return any(pattern in lower_input for pattern in creation_patterns)
    
    def _handle_file_creation_request(self, user_input: str) -> str:
        """Handle file creation requests by actually creating the file."""
        import re
        
        # Extract programming language from request
        # Order matters - more specific patterns should come first
        language_keywords = {
            'bash': ['bash script', 'shell script', '.sh', 'bash', 'shell'],
            'python': [' in python', '.py', 'python script', 'python file', 'python'],
            'typescript': ['.ts', 'typescript', ' ts '],
            'javascript': ['.js', 'javascript', ' js '],
            'html': ['.html', 'html'],
            'css': ['.css', 'css'],
            'java': ['.java', ' java '],
            'cpp': ['.cpp', '.c++', 'c++', 'cpp'],
            'c': ['.c', ' c '],
            'go': ['.go', 'golang', ' go '],
            'rust': ['.rs', 'rust'],
            'php': ['.php', 'php']
        }
        
        detected_language = None
        lower_input = user_input.lower()
        
        for lang, keywords in language_keywords.items():
            if any(keyword in lower_input for keyword in keywords):
                detected_language = lang
                break
        
        if not detected_language:
            detected_language = 'python'  # Default to Python
        
        # Generate appropriate file extension
        extensions = {
            'python': '.py',
            'javascript': '.js', 
            'typescript': '.ts',
            'html': '.html',
            'css': '.css',
            'bash': '.sh',
            'java': '.java',
            'cpp': '.cpp',
            'c': '.c',
            'go': '.go',
            'rust': '.rs',
            'php': '.php'
        }
        
        extension = extensions.get(detected_language, '.py')
        
        # Determine filename from request or use default
        filename_match = re.search(r'(?:file\s+(?:called|named)\s+)([a-zA-Z0-9_\-\.]+)', user_input, re.IGNORECASE)
        if filename_match:
            filename = filename_match.group(1)
            if not filename.endswith(extension):
                filename += extension
        else:
            # Generate a default filename based on content
            if "hello world" in lower_input:
                filename = f"hello_world{extension}"
            else:
                filename = f"script{extension}"
        
        # Generate appropriate code content based on the request
        content = self._generate_code_content(user_input, detected_language)
        
        # Try to write the file
        try:
            if self.file_ops.write_file(filename, content):
                return f"""✅ Successfully created {filename}

📄 **File Contents:**
```{detected_language}
{content}
```

The file has been created in the current directory and is ready to run!"""
            else:
                return f"❌ Failed to create {filename}. Check permissions and try again."
        except Exception as e:
            error_msg = create_detailed_error_message(e, "file creation", user_input)
            console.print(error_msg)
            return f"❌ Error creating file: {e}"
    
    def _generate_code_content(self, user_input: str, language: str) -> str:
        """Generate appropriate code content based on user request and language."""
        # Use AI to generate the actual code content
        code_prompt = f"""Generate {language} code based on this request: "{user_input}"

Requirements:
- Write functional, executable {language} code
- Include appropriate imports and error handling
- Add helpful comments
- Make it production-ready
- Only return the code, no explanations

The code should directly implement what the user asked for."""

        try:
            # Get AI-generated code content
            code_content = self.client.generate(code_prompt)
            
            # Clean up the response - remove markdown code blocks if present
            lines = code_content.strip().split('\n')
            # Remove ```language and ``` markers if present
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1] == '```':
                lines = lines[:-1]
            
            return '\n'.join(lines)
            
        except Exception as e:
            # Fallback to basic templates if AI generation fails
            show_helpful_error("code generation", str(e), "Falling back to basic template")
            return self._get_fallback_template(language, user_input)
    
    def _get_fallback_template(self, language: str, user_input: str) -> str:
        """Get fallback templates when AI generation fails."""
        # Basic templates as fallback
        basic_templates = {
            'python': '''#!/usr/bin/env python3
"""Simple Hello World script."""

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
''',
            'javascript': '''#!/usr/bin/env node
// Simple Hello World script

function main() {
    console.log("Hello, World!");
}

main();
''',
            'typescript': '''#!/usr/bin/env ts-node
// Simple Hello World script

function main(): void {
    console.log("Hello, World!");
}

main();
''',
            'bash': '''#!/bin/bash
# Simple Hello World script

echo "Hello, World!"
''',
            'java': '''public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
''',
            'cpp': '''#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
''',
            'c': '''#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
''',
            'go': '''package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
''',
            'rust': '''fn main() {
    println!("Hello, World!");
}
''',
            'html': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World</title>
</head>
<body>
    <h1>Hello, World!</h1>
</body>
</html>
''',
            'css': '''/* Simple CSS styles */
body {
    font-family: Arial, sans-serif;
    text-align: center;
    margin-top: 50px;
}

h1 {
    color: #333;
}
''',
            'php': '''<?php
// Simple Hello World script

function main() {
    echo "Hello, World!\\n";
}

main();
?>
'''
        }
        
        return basic_templates.get(language, basic_templates['python'])

    def _handle_tool_request(self, user_input: str) -> str:
        """Handle requests that need tool usage."""
        # Check if this is a file creation request
        if self._is_file_creation_request(user_input):
            return self._handle_file_creation_request(user_input)
        
        # First, execute tools and gather real data
        tool_results = self._execute_tools_first(user_input)
        
        if tool_results:
            # If we have tool results, let AI interpret the real data
            tool_guidance = f"""The user requested: "{user_input}"

Here are the REAL results from executing the appropriate tools:

{tool_results}

Based on these ACTUAL results, provide a helpful interpretation and response to the user. 
DO NOT make up or hallucinate any command outputs - only use the real data provided above."""
            
            temp_messages = self.messages + [{"role": "system", "content": tool_guidance}]
            
            try:
                response = self.client.chat(temp_messages, stream=False)
                self.messages.append({"role": "assistant", "content": response})
                return response
            except Exception as e:
                error_msg = create_detailed_error_message(e, "AI response generation", user_input)
                console.print(error_msg)
                return f"Sorry, I encountered an error: {e}"
        else:
            # No tools needed, regular AI response
            return self._get_ai_response()
    
    def _execute_tools_first(self, user_input: str) -> str:
        """Execute tools BEFORE AI response to get real data."""
        results = []
        lower_input = user_input.lower()
        
        # Git operations - check for git-related requests
        if any(word in lower_input for word in ["git status", "repo status", "changes", "status", "git", "repository"]):
            if self.git_ops.is_git_repo():
                status = self.git_ops.get_status()
                if status:
                    git_info = [
                        f"Git Repository Status:",
                        f"Branch: {status['branch']}",
                        f"Current commit: {status['commit']}",
                        f"Is clean: {not status['is_dirty']}"
                    ]
                    if status['modified']:
                        git_info.append(f"Modified files: {', '.join(status['modified'])}")
                    if status['staged']:
                        git_info.append(f"Staged files: {', '.join(status['staged'])}")
                    if status['untracked']:
                        git_info.append(f"Untracked files: {', '.join(status['untracked'][:5])}")
                    results.append("\n".join(git_info))
            else:
                results.append("Not in a git repository")
        
        # Git log - check for log requests
        if any(word in lower_input for word in ["git log", "log", "commits", "recent commits", "commit history"]):
            if self.git_ops.is_git_repo():
                log_entries = self.git_ops.get_log(max_count=5)
                if log_entries:
                    log_info = ["Recent commits:"]
                    for entry in log_entries:
                        log_info.append(f"  {entry['hash']} - {entry['message']} ({entry['date']})")
                    results.append("\n".join(log_info))
        
        # Direct command execution - check for "run" commands
        if any(word in lower_input for word in ["run", "execute"]) and any(cmd in lower_input for cmd in ["git", "npm", "pip", "python"]):
            # Extract the command to run
            import re
            command_match = re.search(r'(?:run|execute)\s+(.+)', user_input, re.IGNORECASE)
            if command_match:
                command = command_match.group(1).strip()
                if command.startswith('"') and command.endswith('"'):
                    command = command[1:-1]
                
                # Execute the command using bash operations
                result = self.bash_ops.run_command(command)
                if result['success']:
                    cmd_output = [
                        f"Command executed: {command}",
                        f"Output:",
                        result['stdout'] if result['stdout'] else "(no output)"
                    ]
                    if result['stderr']:
                        cmd_output.append(f"Errors: {result['stderr']}")
                    results.append("\n".join(cmd_output))
                else:
                    results.append(f"Command failed: {command}\nError: {result.get('error', 'Unknown error')}")
        
        # File operations - check for file requests
        if any(word in lower_input for word in ["read file", "show file", "cat", "content of", "show me"]):
            # Try to extract filename
            import re
            file_matches = re.findall(r'(\S+\.\w+)', user_input)
            for filename in file_matches:
                content = self.file_ops.read_file(filename)
                if content:
                    results.append(f"File: {filename}\nContent:\n{content}")
        
        # Search operations
        if any(word in lower_input for word in ["find", "search", "grep", "look for", "locate"]):
            # Extract search pattern
            pattern = None
            if "todo" in lower_input:
                pattern = "TODO"
            elif "function" in lower_input:
                pattern = "def "
            elif "import" in lower_input:
                pattern = "import"
            elif "class" in lower_input:
                pattern = "class "
            
            if pattern:
                search_results = self.search_ops.grep_files(pattern, max_results=5)
                if search_results:
                    search_info = [f"Search results for '{pattern}':"]
                    for result in search_results[:5]:
                        search_info.append(f"  {result['file']}:{result['line']} - {result['content'][:80]}...")
                    results.append("\n".join(search_info))
        
        return "\n\n".join(results) if results else ""
    
    def _execute_suggested_tools(self, ai_response: str, original_request: str) -> str:
        """Execute tools based on AI suggestions and user request."""
        response_parts = [ai_response]
        
        # Simple keyword-based tool execution
        lower_request = original_request.lower()
        
        # Git status - broader matching for natural language
        if any(word in lower_request for word in ["git status", "repo status", "changes", "status", "git", "repository"]):
            if self.git_ops.is_git_repo():
                status = self.git_ops.get_status()
                if status:
                    response_parts.append("\n[bold blue]🔍 Current Repository Status:[/bold blue]")
                    response_parts.append(f"📍 Branch: [green]{status['branch']}[/green]")
                    response_parts.append(f"✨ Clean: [{'green' if not status['is_dirty'] else 'red'}]{not status['is_dirty']}[/{'green' if not status['is_dirty'] else 'red'}]")
                    if status['modified']:
                        response_parts.append(f"📝 Modified: [yellow]{', '.join(status['modified'])}[/yellow]")
                    if status['staged']:
                        response_parts.append(f"📋 Staged: [green]{', '.join(status['staged'])}[/green]")
                    if status['untracked']:
                        response_parts.append(f"❓ Untracked: [cyan]{', '.join(status['untracked'][:5])}[/cyan]")
            else:
                response_parts.append("\n[yellow]📂 Not in a git repository[/yellow]")
        
        # File editing
        if "edit" in lower_request and any(word in lower_request for word in [".py", ".js", ".ts", "file"]):
            # Extract potential filename
            words = original_request.split()
            for word in words:
                if "." in word and not word.startswith("."):
                    if Confirm.ask(f"\nWould you like me to help edit {word}?"):
                        return self._interactive_file_edit(word, original_request)
        
        # Search operations - better pattern extraction
        if any(word in lower_request for word in ["find", "search", "grep", "look for", "locate"]):
            # Try to extract search pattern from the request
            pattern = None
            if "todo" in lower_request:
                pattern = "TODO"
            elif "function" in lower_request:
                pattern = "def "
            elif "import" in lower_request:
                pattern = "import"
            elif "class" in lower_request:
                pattern = "class "
            else:
                # Ask for pattern if we can't extract it
                try:
                    pattern = Prompt.ask("What pattern would you like to search for?")
                except:
                    pattern = "TODO"  # Default fallback
            
            if pattern:
                results = self.search_ops.grep_files(pattern, max_results=10)
                if results:
                    response_parts.append(f"\n[bold blue]🔍 Search Results for '{pattern}':[/bold blue]")
                    for result in results[:5]:  # Show top 5
                        response_parts.append(f"📄 [cyan]{result['file']}[/cyan]:[yellow]{result['line']}[/yellow] - {result['content'][:80]}...")
                else:
                    response_parts.append(f"\n[yellow]🔍 No results found for '{pattern}'[/yellow]")
        
        return "\n".join(response_parts)
    
    def _handle_slash_command(self, command: str) -> str:
        """Handle slash commands."""
        parts = command[1:].split(' ', 1)  # Remove '/' and split
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "help":
            return self._show_help()
        elif cmd == "clear":
            return self._clear_conversation()
        elif cmd == "model":
            return self._change_model(args)
        elif cmd == "status":
            return self._show_status()
        elif cmd == "sessions":
            return self._list_sessions()
        elif cmd == "config":
            return self._show_config()
        elif cmd == "permissions":
            return self._manage_permissions(args)
        elif cmd == "cache":
            return self._manage_cache(args)
        elif cmd == "complete":
            return self._handle_completion_command(args)
        elif cmd == "exit" or cmd == "quit":
            # Set a flag to exit gracefully instead of calling sys.exit() directly
            if len(self.messages) > 1:  # More than just system message
                self.context_mgr.save_conversation(self.conversation_id, self.messages)
                console.print(f"\n[yellow]Session saved as {self.conversation_id}[/yellow]")
            console.print("[yellow]Goodbye![/yellow]")
            # Raise an exception to break out of the main loop cleanly
            raise KeyboardInterrupt()
        else:
            return f"[red]Unknown command: /{cmd}[/red]\nType /help for available commands."
    
    def _show_help(self) -> str:
        """Show help information."""
        help_text = """[bold blue]OllamaCode Slash Commands[/bold blue]

[bold yellow]Session Management:[/bold yellow]
  /help                Show this help message
  /clear               Clear conversation history  
  /exit, /quit         Exit OllamaCode
  /sessions            List saved sessions
  
[bold yellow]Configuration:[/bold yellow]
  /model [name]        Change Ollama model (or show current)
  /config              Show current configuration
  /status              Show session and project status
  /permissions         Manage operation permissions
  /cache               Manage response cache
  /complete            Show completion suggestions
  
[bold yellow]File Operations:[/bold yellow]
  @filename            Reference a file in your prompt
  
[bold yellow]Examples:[/bold yellow]
  /model gemma3        Switch to gemma3 model
  /clear               Start fresh conversation
  /permissions status  Show current permissions
  @main.py explain this file to me
"""
        return help_text
    
    def _clear_conversation(self) -> str:
        """Clear conversation history."""
        # Keep system message if exists
        system_messages = [msg for msg in self.messages if msg.get('role') == 'system']
        self.messages = system_messages
        return "[green]Conversation history cleared.[/green]"
    
    def _change_model(self, model_name: str) -> str:
        """Change the Ollama model."""
        if not model_name:
            return f"Current model: [bold]{self.client.model}[/bold]"
        
        # Test if model is available
        old_model = self.client.model
        self.client.model = model_name
        
        if self.client.is_available():
            return f"[green]Switched to model: {model_name}[/green]"
        else:
            self.client.model = old_model
            return f"[red]Model '{model_name}' not available. Staying with {old_model}[/red]"
    
    def _show_status(self) -> str:
        """Show session and project status."""
        status_parts = [
            f"[bold blue]Session Status[/bold blue]",
            f"Model: [bold]{self.client.model}[/bold]",
            f"Session ID: [bold]{self.conversation_id}[/bold]",
            f"Messages: [bold]{len(self.messages)}[/bold]",
            f"Project: [bold]{self.context_mgr._context['project_name']}[/bold]",
            f"Project Type: [bold]{self.context_mgr._context['project_type']}[/bold]"
        ]
        return "\n".join(status_parts)
    
    def _list_sessions(self) -> str:
        """List saved sessions."""
        conversations = self.context_mgr.list_conversations()
        
        if not conversations:
            return "[yellow]No saved sessions found.[/yellow]"
        
        result = ["[bold blue]Saved Sessions[/bold blue]"]
        for conv in conversations[:10]:  # Show last 10
            result.append(f"• {conv['id']} - {conv['message_count']} messages - {conv['created_at'][:19]}")
        
        return "\n".join(result)
    
    def _show_config(self) -> str:
        """Show current configuration."""
        config_parts = [
            f"[bold blue]Configuration[/bold blue]",
            f"Ollama URL: [bold]{self.client.base_url}[/bold]", 
            f"Model: [bold]{self.client.model}[/bold]",
            f"Project Root: [bold]{self.context_mgr.project_root}[/bold]",
            f"Context Dir: [bold]{self.context_mgr.context_dir}[/bold]"
        ]
        return "\n".join(config_parts)
    
    def _manage_permissions(self, args: str) -> str:
        """Manage operation permissions."""
        if not args:
            return self.permissions.get_status()
        
        command = args.lower().strip()
        
        if command == "status":
            return self.permissions.get_status()
        elif command == "reset":
            self.permissions.reset_permissions()
            return "[green]✓ Permissions reset[/green]"
        elif command == "approve-all":
            self.permissions.approve_all_for_session()
            return "[yellow]⚠️  All operations approved for this session[/yellow]"
        else:
            return f"[red]Unknown permissions command: {command}[/red]\nUse: status, reset, approve-all"
    
    def _manage_cache(self, args: str) -> str:
        """Manage response cache."""
        if not self.client.cache:
            return "[yellow]Response caching is disabled[/yellow]"
        
        if not args:
            return self._show_cache_status()
        
        command = args.lower().strip()
        
        if command == "status":
            return self._show_cache_status()
        elif command == "clear":
            self.client.cache.clear()
            return "[green]✓ Cache cleared[/green]"
        elif command == "stats":
            return self._show_cache_stats()
        else:
            return f"[red]Unknown cache command: {command}[/red]\nUse: status, clear, stats"
    
    def _show_cache_status(self) -> str:
        """Show cache status."""
        if not self.client.cache:
            return "[yellow]Response caching is disabled[/yellow]"
        
        stats = self.client.cache.get_stats()
        status_parts = [
            f"[bold blue]Cache Status[/bold blue]",
            f"Entries: [bold]{stats['total_entries']}[/bold]",
            f"Total hits: [bold]{stats['total_hits']}[/bold]",
            f"Hit rate: [bold]{stats['hit_rate']}[/bold]",
            f"Cache size: [bold]{stats['cache_size_mb']} MB[/bold]"
        ]
        return "\n".join(status_parts)
    
    def _show_cache_stats(self) -> str:
        """Show detailed cache statistics."""
        if not self.client.cache:
            return "[yellow]Response caching is disabled[/yellow]"
        
        stats = self.client.cache.get_stats()
        
        if stats['total_entries'] == 0:
            return "[dim]No cache entries yet[/dim]"
        
        import datetime
        oldest_date = datetime.datetime.fromtimestamp(stats['oldest_entry']).strftime('%Y-%m-%d %H:%M:%S')
        
        stats_parts = [
            f"[bold blue]Detailed Cache Statistics[/bold blue]",
            f"📊 Total entries: [bold]{stats['total_entries']}[/bold]",
            f"🎯 Cache hits: [bold]{stats['total_hits']}[/bold]", 
            f"📈 Hit rate: [bold]{stats['hit_rate']:.2f}[/bold] hits per entry",
            f"💾 Cache size: [bold]{stats['cache_size_mb']:.2f} MB[/bold]",
            f"📅 Oldest entry: [bold]{oldest_date}[/bold]",
            f"🏆 Cache efficiency: [green]{'High' if stats['hit_rate'] > 1 else 'Medium' if stats['hit_rate'] > 0.5 else 'Low'}[/green]"
        ]
        return "\n".join(stats_parts)
    
    def _handle_completion_command(self, args: str) -> str:
        """Handle completion suggestions command."""
        if not args:
            # Show general completion help
            help_parts = [
                f"[bold blue]Auto-Completion Help[/bold blue]",
                "",
                "[bold yellow]Usage:[/bold yellow]",
                "  /complete [partial_command]  Get completions for command",
                "",
                "[bold yellow]Examples:[/bold yellow]",
                "  /complete /h                 Show commands starting with 'h'",
                "  /complete /permissions       Show permission command options",
                "  /complete @main              Show files starting with 'main'",
                "",
                "[bold yellow]Available Commands:[/bold yellow]"
            ]
            
            commands = AutoCompleter.get_all_commands()
            for i, cmd in enumerate(commands):
                if i % 3 == 0:
                    help_parts.append("")
                help_parts.append(f"  {cmd:15}" + (commands[i+1] if i+1 < len(commands) else "").ljust(15) + 
                                (commands[i+2] if i+2 < len(commands) else ""))
                if i % 3 == 2:
                    i += 2  # Skip the next two since we already added them
            
            return "\n".join(help_parts)
        
        # Show completions for the given input
        context = {
            'project_type': getattr(self.context_mgr, 'project_type', 'unknown'),
            'current_dir': str(self.context_mgr.project_root)
        }
        
        suggestions = AutoCompleter.suggest_completions(args, context)
        formatted = AutoCompleter.format_completion_display(suggestions)
        
        if formatted:
            return f"[bold cyan]💡 Completions for '{args}':[/bold cyan]\n{formatted}"
        else:
            return f"[yellow]No completions found for '{args}'[/yellow]"
    
    def _process_file_references(self, user_input: str) -> str:
        """Process @filename references in user input."""
        import re
        
        # Find all @filename patterns
        pattern = r'@([^\s]+)'
        matches = re.findall(pattern, user_input)
        
        for filename in matches:
            file_content = self.file_ops.read_file(filename)
            if file_content:
                # Replace @filename with file content
                file_reference = f"\n\nFile: {filename}\n```\n{file_content}\n```"
                user_input = user_input.replace(f"@{filename}", file_reference)
            else:
                user_input = user_input.replace(f"@{filename}", f"[File '{filename}' not found]")
        
        return user_input
    
    def _interactive_file_edit(self, file_path: str, request: str) -> str:
        """Handle interactive file editing."""
        content = self.file_ops.read_file(file_path)
        if content is None:
            return f"Could not read file: {file_path}"
        
        console.print(f"\n[bold blue]Current content of {file_path}:[/bold blue]")
        console.print(Panel(content[:500] + "..." if len(content) > 500 else content))
        
        # Get AI suggestion for edit
        edit_prompt = f"""Based on the user request: "{request}"

Here's the current file content:
```
{content}
```

Please provide an improved version of this file. Consider the project context and the user's specific request."""
        
        try:
            suggestion = self.client.generate(edit_prompt)
            
            console.print("\n[bold green]Suggested changes:[/bold green]")
            console.print(Panel(suggestion[:500] + "..." if len(suggestion) > 500 else suggestion))
            
            if Confirm.ask("Apply these changes?"):
                if self.file_ops.write_file(file_path, suggestion):
                    return f"✅ Successfully updated {file_path}"
                else:
                    return f"❌ Failed to update {file_path}"
            else:
                return "Changes not applied"
                
        except Exception as e:
            error_msg = create_detailed_error_message(e, "file editing", f"edit {file_path}")
            console.print(error_msg)
            return f"Error generating edit suggestion: {e}"
    
    def _get_ai_response(self) -> str:
        """Get AI response for regular conversation."""
        try:
            response = self.client.chat(self.messages, stream=True)
            self.messages.append({"role": "assistant", "content": response})
            return ""  # Response already streamed
        except Exception as e:
            error_msg = create_detailed_error_message(e, "AI conversation", "chat request")
            console.print(error_msg)
            return f"Sorry, I encountered an error: {e}"
    
    def _print_enhanced_response(self, text: str):
        """Print response with enhanced formatting and syntax highlighting."""
        if not text:
            return
        
        # Check if response contains code
        if CodeHighlighter.is_code_heavy(text):
            # Use enhanced code highlighting
            CodeHighlighter.print_highlighted_response(text)
        else:
            # Check for any code blocks
            code_blocks = CodeHighlighter.extract_code_blocks(text)
            if code_blocks:
                # Has some code, use highlighting
                CodeHighlighter.print_highlighted_response(text)
            else:
                # Plain text, use markdown
                try:
                    console.print(Markdown(text))
                except Exception:
                    console.print(text)
    
    def _maybe_show_completion_hints(self, user_input: str):
        """Show completion hints for partial inputs."""
        if not user_input or len(user_input) < 2:
            return
        
        # Show hints for incomplete slash commands
        if user_input.startswith('/') and not AutoCompleter.is_complete_command(user_input):
            suggestions = AutoCompleter.suggest_completions(user_input)
            
            if suggestions['slash_commands']:
                formatted = AutoCompleter.format_completion_display(suggestions)
                if formatted:
                    console.print(f"\n[dim]{formatted}[/dim]")
    
    def _show_completion_suggestions(self, user_input: str):
        """Show comprehensive completion suggestions."""
        if not user_input:
            return
        
        context = {
            'project_type': getattr(self.context_mgr, 'project_type', 'unknown'),
            'current_dir': str(self.context_mgr.project_root)
        }
        
        suggestions = AutoCompleter.suggest_completions(user_input, context)
        formatted = AutoCompleter.format_completion_display(suggestions)
        
        if formatted:
            console.print(f"\n[bold cyan]💡 Completion Suggestions:[/bold cyan]")
            console.print(formatted)
    
    def _save_and_exit(self):
        """Save conversation and exit."""
        if len(self.messages) > 1:  # More than just system message
            self.context_mgr.save_conversation(self.conversation_id, self.messages)
            console.print(f"\n[yellow]Session saved as {self.conversation_id}[/yellow]")
        console.print("[yellow]Goodbye![/yellow]")
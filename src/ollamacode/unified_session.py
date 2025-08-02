"""Unified Interactive Session - Streamlined with unified execution system."""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown

from .ollama_client import OllamaClient
from .execution import ToolExecutor, IntentAnalyzer, ToolType
from .context import ContextManager
from .config import Config
from .permissions import PermissionManager
from .syntax_highlighter import CodeHighlighter
from .autocomplete import AutoCompleter
from .error_handler import create_detailed_error_message, show_helpful_error
from .tool_executor import ToolCallExecutor

console = Console()


class UnifiedSession:
    """Unified Interactive Session with streamlined tool execution."""
    
    def __init__(self, model: str = None, url: str = None, timeout: int = None):
        self.config = Config()
        self.client = OllamaClient(
            base_url=url or self.config.get('ollama_url'),
            model=model or self.config.get('default_model'),
            timeout=timeout or self.config.get('timeout', 120)
        )
        
        # Unified execution components
        self.permissions = PermissionManager()
        self.tool_executor = ToolExecutor(self.permissions)
        
        # New tool calling executor
        self.tool_call_executor = ToolCallExecutor(self.permissions)
        
        # Context and session management
        self.context_mgr = ContextManager()
        self.autocompleter = AutoCompleter()
        
        # Session state
        self.messages = []
        self.conversation_id = None
        
        # Auto-load project context
        self._auto_load_project_context()
    
    def start(self):
        """Start interactive session."""
        if not self.client.is_available():
            console.print("[red]Error: Ollama service is not available[/red]")
            console.print("Please make sure Ollama is running: [cyan]ollama serve[/cyan]")
            sys.exit(1)
        
        # Welcome message
        console.print(Panel.fit(
            "[bold blue]🦙 OllamaCode Phase 5[/bold blue]\n"
            "AI-powered coding assistant with unified tool execution\n"
            f"Model: [green]{self.client.model}[/green] | Server: [cyan]{self.client.base_url}[/cyan]\n"
            "Type /help for commands or start coding!",
            title="Welcome",
            border_style="blue"
        ))
        
        try:
            while True:
                try:
                    user_input = Prompt.ask("\n[bold blue]You[/bold blue]", default="")
                    
                    if not user_input.strip():
                        continue
                    
                    if user_input.lower() in ['exit', 'quit', 'bye']:
                        console.print("[yellow]Goodbye! 👋[/yellow]")
                        break
                    
                    # Process the input using Phase 5 system
                    response = self._process_user_input(user_input)
                    if response.strip():
                        console.print(f"\n[bold green]🦙 OllamaCode[/bold green]:")
                        self._print_enhanced_response(response)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
                    continue
                except EOFError:
                    break
                    
        except Exception as e:
            console.print(f"[red]Fatal error: {e}[/red]")
        finally:
            # Save session
            if self.messages:
                self._save_session()
    
    def _process_user_input(self, user_input: str) -> str:
        """Process user input using Ollama tool calling (reliable approach)."""
        user_input = user_input.strip()
        
        # Handle slash commands
        if user_input.startswith('/'):
            return self._handle_slash_command(user_input)
        
        # Handle file references (@filename)
        user_input = self._process_file_references(user_input)
        
        self.messages.append({"role": "user", "content": user_input})
        
        try:
            # Use tool calling approach - let LLM decide what tools to use
            response = self.client.chat_with_tools(self.messages, stream=False)
            
            if response["type"] == "tool_calls":
                # LLM wants to use tools
                return self._handle_tool_calls_response(response)
            elif response["type"] == "text":
                # Regular text response
                content = response["content"]
                self.messages.append({"role": "assistant", "content": content})
                return content
            else:
                # Error response
                return response["content"]
                
        except Exception as e:
            error_msg = create_detailed_error_message(e, "AI response generation", user_input)
            console.print(error_msg)
            return f"Sorry, I encountered an error: {e}"
    
    def _handle_tool_calls_response(self, response: dict) -> str:
        """Handle response when LLM wants to call tools."""
        tool_calls = response["tool_calls"]
        assistant_content = response["content"]
        
        # Add assistant message with tool calls
        self.messages.append({
            "role": "assistant", 
            "content": assistant_content,
            "tool_calls": tool_calls
        })
        
        # Execute the tool calls
        tool_results = self.tool_call_executor.execute_tool_calls(tool_calls)
        
        # Add tool results to conversation
        for tool_result in tool_results:
            tool_message = self.tool_call_executor.format_tool_result_for_llm(tool_result)
            self.messages.append(tool_message)
        
        # Get LLM's response after tool execution
        try:
            final_response = self.client.chat(self.messages, stream=False)
            
            if final_response["type"] == "text":
                content = final_response["content"]
                self.messages.append({"role": "assistant", "content": content})
                return content
            else:
                return "Tool execution completed, but couldn't generate final response."
                
        except Exception as e:
            error_msg = f"Tools executed successfully, but error in final response: {e}"
            console.print(f"[yellow]{error_msg}[/yellow]")
            
            # Return a summary of what was accomplished
            successful_tools = [r for r in tool_results if r["success"]]
            if successful_tools:
                summary = "✅ Successfully executed:\n"
                for tool in successful_tools:
                    summary += f"- {tool['function_name']}\n"
                return summary
            else:
                return "Tool execution attempted but encountered errors."
    
    def _get_ai_response_with_context(self, user_input: str, tool_results: List) -> str:
        """Get AI response with tool execution context."""
        # Prepare context for AI
        context_parts = []
        
        # Add tool results as context
        successful_tools = [r for r in tool_results if r.success and r.data]
        if successful_tools:
            context_parts.append("Tool execution results:")
            for result in successful_tools:
                if isinstance(result.data, dict):
                    context_parts.append(f"- {result.tool_type.value}:{result.action} -> {result.data}")
                elif isinstance(result.data, str) and len(result.data) < 500:
                    context_parts.append(f"- {result.tool_type.value}:{result.action} -> {result.data[:200]}...")
        
        # Create system context
        if context_parts:
            system_context = f"""The user requested: "{user_input}"

{chr(10).join(context_parts)}

Based on these actual tool results, provide a helpful interpretation and response. 
Be concise and focus on what the user needs to know."""
            
            temp_messages = self.messages + [{"role": "system", "content": system_context}]
        else:
            temp_messages = self.messages
        
        try:
            response = self.client.chat(temp_messages, stream=False)
            self.messages.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            return f"I executed the tools successfully, but couldn't generate an AI response: {e}"
    
    def _handle_slash_command(self, command: str) -> str:
        """Handle slash commands."""
        parts = command[1:].split()
        if not parts:
            return "Unknown command. Type /help for available commands."
        
        cmd = parts[0].lower()
        
        if cmd == "help":
            return self._show_help()
        elif cmd == "model":
            return self._handle_model_command(parts[1:])
        elif cmd == "status":
            return self._show_status()
        elif cmd == "clear":
            self.messages = []
            return "Conversation history cleared."
        elif cmd == "permissions":
            return self._handle_permissions_command(parts[1:])
        elif cmd == "config":
            return self._show_config()
        else:
            return f"Unknown command: /{cmd}. Type /help for available commands."
    
    def _show_help(self) -> str:
        """Show help information."""
        return """Available commands:
        
🔧 **Core Commands:**
/help                    - Show this help message
/status                  - Show session status
/clear                   - Clear conversation history
/config                  - Show current configuration

🤖 **Model Commands:**
/model                   - Show current model
/model <name>           - Switch to different model

🛡️ **Permission Commands:**
/permissions status     - Check current permissions
/permissions reset      - Reset all permissions
/permissions approve-all - Approve all operations for this session

📁 **File Operations:**
@filename.ext           - Reference a file in conversation
write/create/make file  - Create new files
read/show/open file     - Read existing files

🔧 **Tool Operations:**
git status/diff/log     - Git operations
find/search/grep <term> - Search through files
run/execute <command>   - Execute bash commands

Type 'exit' or 'quit' to end the session."""
    
    def _handle_model_command(self, args: List[str]) -> str:
        """Handle model switching."""
        if not args:
            return f"Current model: [green]{self.client.model}[/green]"
        
        new_model = args[0]
        try:
            # Test if model is available
            self.client.model = new_model
            return f"✅ Switched to model: [green]{new_model}[/green]"
        except Exception as e:
            return f"❌ Failed to switch to model {new_model}: {e}"
    
    def _show_status(self) -> str:
        """Show session status."""
        status_info = [
            f"Model: {self.client.model}",
            f"Server: {self.client.base_url}",
            f"Messages: {len(self.messages)}",
            f"Project: {self.context_mgr.get_project_type()}",
        ]
        
        if self.conversation_id:
            status_info.append(f"Session ID: {self.conversation_id}")
        
        return "\\n".join(status_info)
    
    def _handle_permissions_command(self, args: List[str]) -> str:
        """Handle permission commands."""
        if not args:
            return "Permission commands: status, reset, approve-all"
        
        cmd = args[0].lower()
        if cmd == "status":
            return self.permissions.get_status_message()
        elif cmd == "reset":
            self.permissions.reset_all()
            return "✅ All permissions reset"
        elif cmd == "approve-all":
            self.permissions.approve_all_for_session()
            return "✅ All operations approved for this session"
        else:
            return f"Unknown permission command: {cmd}"
    
    def _show_config(self) -> str:
        """Show current configuration."""
        return f"""Current Configuration:
        
Ollama URL: {self.client.base_url}
Model: {self.client.model}
Project Root: {os.getcwd()}
Context Dir: {self.context_mgr.context_dir}
Project Type: {self.context_mgr.get_project_type()}"""
    
    def _process_file_references(self, text: str) -> str:
        """Process @filename references in text."""
        import re
        
        def replace_file_ref(match):
            filename = match.group(1)
            content = self.tool_executor.file_ops.read_file(filename)
            if content:
                return f"[File: {filename}]\\n{content}\\n[End of {filename}]"
            else:
                return f"[File: {filename} - could not read]"
        
        return re.sub(r'@([\\w.-]+\\.[\\w]+)', replace_file_ref, text)
    
    def _auto_load_project_context(self):
        """Automatically load project context."""
        project_type = self.context_mgr.detect_project_type()
        
        if project_type != "unknown":
            self.context_mgr.scan_important_files()
            project_summary = self.context_mgr.get_project_summary()
            
            context_message = f"""You are an AI coding assistant helping with a {project_type} project. 

{project_summary}

You have access to advanced tool execution capabilities:
- File operations (read, write, edit files)
- Git operations (status, diff, log, etc.)
- Search operations (find, grep)
- Bash operations (run commands safely)

Provide concise, helpful responses focused on the user's specific needs."""
            
            self.messages.append({"role": "system", "content": context_message})
    
    def _print_enhanced_response(self, text: str):
        """Print response with enhanced formatting."""
        if not text:
            return
        
        # Check if response contains code
        if CodeHighlighter.is_code_heavy(text):
            CodeHighlighter.print_highlighted_response(text)
        else:
            # Check for any code blocks
            code_blocks = CodeHighlighter.extract_code_blocks(text)
            if code_blocks:
                CodeHighlighter.print_highlighted_response(text)
            else:
                # Plain text, use markdown
                try:
                    console.print(Markdown(text))
                except Exception:
                    console.print(text)
    
    def _save_session(self):
        """Save current session."""
        if self.messages:
            session_data = {
                'id': self.conversation_id or f"session_{int(datetime.now().timestamp())}",
                'messages': self.messages,
                'model': self.client.model,
                'timestamp': datetime.now().isoformat()
            }
            
            self.context_mgr.save_session(session_data)
            console.print(f"[dim]Session saved as {session_data['id']}[/dim]")
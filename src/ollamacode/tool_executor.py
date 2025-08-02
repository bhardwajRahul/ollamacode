"""Tool executor for handling Ollama tool calls."""

import json
from typing import Dict, Any, List, Optional
from rich.console import Console

from .tools.file_ops import FileOperations
from .tools.bash_ops import BashOperations  
from .tools.git_ops import GitOperations
from .tools.search_ops import SearchOperations
from .permissions import PermissionManager
from .tool_schemas import get_tool_function_mapping

console = Console()


class ToolCallExecutor:
    """Execute tool calls from Ollama LLM responses."""
    
    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self.permissions = permission_manager or PermissionManager()
        
        # Initialize tool instances
        self.file_ops = FileOperations(self.permissions)
        self.bash_ops = BashOperations()
        self.git_ops = GitOperations()
        self.search_ops = SearchOperations()
        
        # Function mapping
        self.function_map = self._build_function_map()
    
    def _build_function_map(self) -> Dict[str, callable]:
        """Build mapping of function names to actual callable methods."""
        return {
            # File operations
            "read_file": self.file_ops.read_file,
            "write_file": self.file_ops.write_file,
            "list_files": self.file_ops.list_files,
            
            # Bash operations
            "run_command": self.bash_ops.run_command,
            
            # Git operations
            "git_status": self.git_ops.get_status,
            "git_diff": self.git_ops.get_diff,
            "git_add": self.git_ops.add_files,
            "git_commit": self.git_ops.commit,
            "git_log": self.git_ops.get_log,
            
            # Search operations  
            "search_text": self.search_ops.grep_files,
            "find_files": self.search_ops.find_files
        }
    
    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of tool calls and return results."""
        results = []
        
        for tool_call in tool_calls:
            result = self.execute_single_tool_call(tool_call)
            results.append(result)
        
        return results
    
    def execute_single_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call and return the result."""
        try:
            function_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]
            
            # Parse arguments if they're a string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    return {
                        "tool_call_id": tool_call.get("id", "unknown"),
                        "success": False,
                        "error": f"Failed to parse arguments: {arguments}",
                        "result": None
                    }
            
            # Get the function to call
            if function_name not in self.function_map:
                return {
                    "tool_call_id": tool_call.get("id", "unknown"),
                    "success": False,
                    "error": f"Unknown function: {function_name}",
                    "result": None
                }
            
            func = self.function_map[function_name]
            
            # Execute the function
            console.print(f"[dim]🔧 Executing: {function_name}({', '.join(f'{k}={v}' for k, v in arguments.items())})[/dim]")
            
            result = func(**arguments)
            
            # Format the result
            return {
                "tool_call_id": tool_call.get("id", "unknown"),
                "success": True,
                "error": None,
                "result": result,
                "function_name": function_name,
                "arguments": arguments
            }
            
        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            console.print(f"[red]❌ {error_msg}[/red]")
            
            return {
                "tool_call_id": tool_call.get("id", "unknown"),
                "success": False,
                "error": error_msg,
                "result": None
            }
    
    def format_tool_result_for_llm(self, tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format tool execution result for sending back to LLM."""
        if tool_result["success"]:
            # Format successful result
            result_content = self._format_result_content(
                tool_result["function_name"], 
                tool_result["result"]
            )
            
            return {
                "role": "tool",
                "tool_call_id": tool_result["tool_call_id"],
                "content": result_content
            }
        else:
            # Format error result
            return {
                "role": "tool", 
                "tool_call_id": tool_result["tool_call_id"],
                "content": f"Error: {tool_result['error']}"
            }
    
    def _format_result_content(self, function_name: str, result: Any) -> str:
        """Format the result content based on the function type."""
        if result is None:
            return "Operation completed (no output)"
        
        if function_name == "read_file":
            return f"File content:\n```\n{result}\n```"
        
        elif function_name == "write_file":
            return "File written successfully" if result else "Failed to write file"
        
        elif function_name == "list_files":
            if isinstance(result, list):
                return f"Found {len(result)} files:\n" + "\n".join(f"- {file}" for file in result)
            return str(result)
        
        elif function_name == "run_command":
            if isinstance(result, dict):
                output = result.get("stdout", "")
                error = result.get("stderr", "")
                exit_code = result.get("returncode", 0)
                
                content = f"Command executed (exit code: {exit_code})"
                if output:
                    content += f"\nOutput:\n```\n{output}\n```"
                if error:
                    content += f"\nError:\n```\n{error}\n```"
                return content
            return str(result)
        
        elif function_name.startswith("git_"):
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            elif isinstance(result, list):
                return json.dumps(result, indent=2)
            return str(result)
        
        elif function_name in ["search_text", "find_files"]:
            if isinstance(result, list):
                return f"Found {len(result)} matches:\n" + "\n".join(f"- {item}" for item in result)
            return str(result)
        
        else:
            # Default formatting
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
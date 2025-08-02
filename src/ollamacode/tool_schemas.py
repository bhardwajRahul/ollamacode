"""Tool schemas for Ollama tool calling API integration."""

from typing import List, Dict, Any

def get_ollamacode_tools() -> List[Dict[str, Any]]:
    """Get all OllamaCode tool schemas for Ollama tool calling."""
    
    return [
        # File Operations
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file from the filesystem",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "write_file",
                "description": "Write content to a file, creating it if it doesn't exist. Shows diff preview if file exists.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path where to write the file"
                        },
                        "content": {
                            "type": "string", 
                            "description": "The content to write to the file"
                        },
                        "show_diff": {
                            "type": "boolean",
                            "description": "Whether to show a diff preview before writing (default: true)",
                            "default": True
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files", 
                "description": "List files in a directory, optionally filtering by pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory to list files from (default: current directory)",
                            "default": "."
                        },
                        "pattern": {
                            "type": "string", 
                            "description": "Glob pattern to filter files (e.g., '*.py', '*.js', '*')",
                            "default": "*"
                        }
                    },
                    "required": []
                }
            }
        },
        
        # Bash Operations
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a bash command safely. Only allows whitelisted safe commands like ls, git, npm, python, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute (e.g., 'ls -la', 'python script.py', 'npm test')"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory to run the command in (default: current directory)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                            "default": 30
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        
        # Git Operations
        {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Get the current git repository status showing modified, staged, and untracked files",
                "parameters": {
                    "type": "object", 
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": "Get git diff showing changes in files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Specific file to show diff for (optional, shows all changes if not specified)"
                        },
                        "staged": {
                            "type": "boolean", 
                            "description": "Show staged changes instead of working directory changes",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_add",
                "description": "Stage files for commit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file paths to stage for commit"
                        }
                    },
                    "required": ["files"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_commit",
                "description": "Create a git commit with staged changes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message"
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name and email (optional)"
                        }
                    },
                    "required": ["message"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_log",
                "description": "Get git commit history",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_count": {
                            "type": "integer",
                            "description": "Maximum number of commits to show (default: 10)",
                            "default": 10
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Show history for specific file (optional)"
                        }
                    },
                    "required": []
                }
            }
        },
        
        # Search Operations
        {
            "type": "function",
            "function": {
                "name": "search_text",
                "description": "Search for text patterns in files using grep",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Text pattern or regex to search for"
                        },
                        "directory": {
                            "type": "string",
                            "description": "Directory to search in (default: current directory)",
                            "default": "."
                        },
                        "file_extension": {
                            "type": "string",
                            "description": "File extension to filter by (e.g., 'py', 'js', 'md')"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether search is case sensitive (default: false)",
                            "default": False
                        }
                    },
                    "required": ["pattern"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_files",
                "description": "Find files by name pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {
                            "type": "string", 
                            "description": "File name pattern to search for (supports wildcards like '*.py', 'test_*')"
                        },
                        "directory": {
                            "type": "string",
                            "description": "Directory to search in (default: current directory)",
                            "default": "."
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum directory depth to search (optional)"
                        }
                    },
                    "required": ["name_pattern"]
                }
            }
        }
    ]


def get_tool_function_mapping() -> Dict[str, str]:
    """Map tool function names to their implementation methods."""
    return {
        # File operations
        "read_file": "file_ops.read_file",
        "write_file": "file_ops.write_file", 
        "list_files": "file_ops.list_files",
        
        # Bash operations
        "run_command": "bash_ops.run_command",
        
        # Git operations  
        "git_status": "git_ops.get_status",
        "git_diff": "git_ops.get_diff",
        "git_add": "git_ops.add_files", 
        "git_commit": "git_ops.commit",
        "git_log": "git_ops.get_log",
        
        # Search operations
        "search_text": "search_ops.grep_files",
        "find_files": "search_ops.find_files"
    }
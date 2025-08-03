"""Tests for Ollama tool calling functionality."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.ollamacode.interactive_session import InteractiveSession
from src.ollamacode.tool_executor import ToolCallExecutor
from src.ollamacode.tool_schemas import get_ollamacode_tools
from src.ollamacode.permissions import PermissionManager


class TestToolCalling:
    """Test the new tool calling functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_tool_schemas_generation(self):
        """Test that tool schemas are generated correctly."""
        tools = get_ollamacode_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check that we have expected tools
        tool_names = [tool["function"]["name"] for tool in tools]
        
        # File operations
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "list_files" in tool_names
        
        # Bash operations
        assert "run_command" in tool_names
        
        # Git operations
        assert "git_status" in tool_names
        assert "git_diff" in tool_names
        
        # Search operations
        assert "search_text" in tool_names
        assert "find_files" in tool_names
        
        # Verify schema structure
        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
    
    def test_tool_executor_initialization(self):
        """Test that ToolCallExecutor initializes correctly."""
        perm_manager = PermissionManager()
        perm_manager.approve_all_for_session()
        
        executor = ToolCallExecutor(perm_manager)
        
        assert executor.permissions is not None
        assert executor.file_ops is not None
        assert executor.bash_ops is not None
        assert executor.git_ops is not None
        assert executor.search_ops is not None
        assert len(executor.function_map) > 0
    
    def test_tool_call_execution(self):
        """Test executing a simple tool call."""
        perm_manager = PermissionManager()
        perm_manager.approve_all_for_session()
        
        executor = ToolCallExecutor(perm_manager)
        
        # Test list_files tool call
        tool_call = {
            "id": "test_call_1",
            "function": {
                "name": "list_files",
                "arguments": {
                    "directory": self.temp_dir,
                    "pattern": "*"
                }
            }
        }
        
        result = executor.execute_single_tool_call(tool_call)
        
        assert result["success"] is True
        assert result["tool_call_id"] == "test_call_1"
        assert result["function_name"] == "list_files"
        assert isinstance(result["result"], list)
    
    def test_file_creation_tool_call(self):
        """Test creating a file via tool call."""
        perm_manager = PermissionManager()
        perm_manager.approve_all_for_session()
        
        executor = ToolCallExecutor(perm_manager)
        
        test_file = os.path.join(self.temp_dir, "test_file.py")
        test_content = "print('Hello from tool calling!')"
        
        # Test write_file tool call
        tool_call = {
            "id": "test_write",
            "function": {
                "name": "write_file", 
                "arguments": {
                    "file_path": test_file,
                    "content": test_content,
                    "show_diff": False
                }
            }
        }
        
        result = executor.execute_single_tool_call(tool_call)
        
        assert result["success"] is True
        assert os.path.exists(test_file)
        
        # Verify file content
        with open(test_file, 'r') as f:
            content = f.read()
        assert content == test_content
    
    @patch('src.ollamacode.interactive_session.ContextManager')
    def test_interactive_session_with_tool_calling(self, mock_context_class):
        """Test the interactive session with tool calling enabled."""
        # Mock context manager to avoid directory creation issues
        mock_context = Mock()
        mock_context_class.return_value = mock_context
        
        # Mock Ollama client responses
        with patch('src.ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "llama3.1"
            
            # Mock tool calling response
            mock_client.chat_with_tools.return_value = {
                "type": "tool_calls",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": "write_file",
                        "arguments": {
                            "file_path": os.path.join(self.temp_dir, "hello.py"),
                            "content": "print('Hello World!')",
                            "show_diff": False
                        }
                    }
                }],
                "content": "I'll create a Python file for you."
            }
            
            # Mock final response after tool execution
            mock_client.chat.return_value = {
                "type": "text", 
                "content": "I've successfully created the hello.py file with your requested content!"
            }
            
            mock_client_class.return_value = mock_client
            
            # Create session and test tool calling
            session = InteractiveSession()
            
            # Test the tool calling method (now the default)
            response = session._process_user_input("create a file called hello.py that prints hello world")
            
            # Verify the response
            assert "successfully created" in response.lower()
            assert mock_client.chat_with_tools.called
            assert mock_client.chat.called
    
    def test_tool_result_formatting(self):
        """Test that tool results are formatted correctly for LLM."""
        perm_manager = PermissionManager()
        perm_manager.approve_all_for_session()
        
        executor = ToolCallExecutor(perm_manager)
        
        # Test successful result
        tool_result = {
            "tool_call_id": "test_1",
            "success": True,
            "function_name": "write_file",
            "result": True
        }
        
        formatted = executor.format_tool_result_for_llm(tool_result)
        
        assert formatted["role"] == "tool"
        assert formatted["tool_call_id"] == "test_1"
        assert "successfully" in formatted["content"].lower()
        
        # Test error result
        error_result = {
            "tool_call_id": "test_2",
            "success": False,
            "error": "File not found"
        }
        
        formatted_error = executor.format_tool_result_for_llm(error_result)
        
        assert formatted_error["role"] == "tool"
        assert formatted_error["tool_call_id"] == "test_2"
        assert "Error:" in formatted_error["content"]
    
    def test_multiple_tool_calls(self):
        """Test executing multiple tool calls in sequence."""
        perm_manager = PermissionManager()
        perm_manager.approve_all_for_session()
        
        executor = ToolCallExecutor(perm_manager)
        
        # Create a test file first
        test_file = os.path.join(self.temp_dir, "multi_test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "list_files",
                    "arguments": {"directory": self.temp_dir}
                }
            },
            {
                "id": "call_2", 
                "function": {
                    "name": "read_file",
                    "arguments": {"file_path": test_file}
                }
            }
        ]
        
        results = executor.execute_tool_calls(tool_calls)
        
        assert len(results) == 2
        assert all(result["success"] for result in results)
        assert results[0]["function_name"] == "list_files"
        assert results[1]["function_name"] == "read_file"
        assert "Test content" in str(results[1]["result"])
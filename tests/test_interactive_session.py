"""Tests for the interactive session functionality."""

import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ollamacode.interactive_session import InteractiveSession


class TestInteractiveSession:
    
    @patch('ollamacode.interactive_session.OllamaClient')
    def test_session_initialization(self, mock_client_class):
        """Test session initializes correctly."""
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client_class.return_value = mock_client
        
        session = InteractiveSession()
        
        assert session.client == mock_client
        assert session.file_ops is not None
        assert session.git_ops is not None
        assert session.search_ops is not None
        assert session.bash_ops is not None
        assert session.context_mgr is not None
    
    def test_should_use_tools_detection(self):
        """Test tool usage detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('ollamacode.interactive_session.OllamaClient'):
                session = InteractiveSession()
                
                # Should detect tool usage
                assert session._should_use_tools("edit my file.py") is True
                assert session._should_use_tools("show git status") is True
                assert session._should_use_tools("find all functions") is True
                assert session._should_use_tools("run the tests") is True
                
                # Should not detect tool usage (adjusted for more specific detection)
                assert session._should_use_tools("what is recursion?") is False
                assert session._should_use_tools("explain algorithms") is False
    
    @patch('ollamacode.interactive_session.OllamaClient')
    def test_auto_load_project_context(self, mock_client_class):
        """Test automatic project context loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a Python project indicator
            (Path(temp_dir) / "pyproject.toml").touch()
            
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client_class.return_value = mock_client
            
            with patch('ollamacode.interactive_session.ContextManager') as mock_context_class:
                mock_context = Mock()
                mock_context.detect_project_type.return_value = "python"
                mock_context.scan_important_files.return_value = ["pyproject.toml"]
                mock_context.get_project_summary.return_value = "Test project"
                mock_context._context = {"project_name": "test"}
                mock_context_class.return_value = mock_context
                
                session = InteractiveSession()
                session._auto_load_project_context()
                
                assert session.project_context_loaded is True
                assert len(session.messages) > 0
                assert "python project" in session.messages[0]["content"]


class TestSessionWithMocks:
    """Test interactive session with mocked dependencies."""
    
    def setup_method(self):
        """Setup mocks for each test."""
        self.mock_client = Mock()
        self.mock_client.is_available.return_value = True
        self.mock_client.model = "gemma3"
        
        self.mock_context = Mock()
        self.mock_context._context = {"project_name": "test_project"}
        self.mock_context.detect_project_type.return_value = "python"
        self.mock_context.scan_important_files.return_value = ["test.py"]
        self.mock_context.get_project_summary.return_value = "Test project summary"
        
        # Patch all the classes
        self.client_patcher = patch('ollamacode.interactive_session.OllamaClient')
        self.context_patcher = patch('ollamacode.interactive_session.ContextManager')
        self.config_patcher = patch('ollamacode.interactive_session.Config')
        
        self.mock_client_class = self.client_patcher.start()
        self.mock_context_class = self.context_patcher.start()
        self.mock_config_class = self.config_patcher.start()
        
        self.mock_client_class.return_value = self.mock_client
        self.mock_context_class.return_value = self.mock_context
        self.mock_config_class.return_value = Mock()
    
    def teardown_method(self):
        """Clean up patches."""
        self.client_patcher.stop()
        self.context_patcher.stop()
        self.config_patcher.stop()
    
    def test_process_regular_conversation(self):
        """Test processing regular conversation."""
        session = InteractiveSession()
        
        # Mock a regular conversation response using new tool calling API
        self.mock_client.chat_with_tools.return_value = {
            "type": "text",
            "content": "Hello! How can I help you?"
        }
        
        response = session._process_user_input("Hello")
        
        assert len(session.messages) == 2  # User message + assistant response
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "Hello"
        assert session.messages[1]["role"] == "assistant"
    
    def test_process_tool_request(self):
        """Test processing requests that need tools."""
        session = InteractiveSession()
        
        # Mock tool calling response
        self.mock_client.chat_with_tools.return_value = {
            "type": "tool_calls",
            "tool_calls": [{
                "id": "call_1",
                "function": {
                    "name": "write_file",
                    "arguments": {"file_path": "test.py", "content": "print('hello')"}
                }
            }],
            "content": "I'll create that file for you."
        }
        
        # Mock final response after tool execution
        self.mock_client.chat.return_value = {
            "type": "text",
            "content": "File created successfully!"
        }
        
        with patch.object(session.tool_executor, 'execute_tool_calls') as mock_execute, \
             patch.object(session.tool_executor, 'format_tool_result_for_llm') as mock_format:
            
            mock_execute.return_value = [{"success": True, "tool_call_id": "call_1"}]
            mock_format.return_value = {"role": "tool", "tool_call_id": "call_1", "content": "Success"}
            
            response = session._process_user_input("edit my file.py")
            
            # Should have: user message, assistant with tool calls, tool result, final assistant
            assert len(session.messages) >= 3
            mock_execute.assert_called_once()
    
    def test_file_edit_workflow(self):
        """Test the file editing workflow."""
        session = InteractiveSession()
        
        # Mock file operations - make sure they're properly set
        with patch.object(session.file_ops, 'read_file', return_value="def hello():\n    pass"):
            with patch.object(session.file_ops, 'write_file', return_value=True) as mock_write:
                # Mock AI response
                self.mock_client.generate.return_value = "def hello():\n    print('Hello, World!')"
                
                with patch('ollamacode.interactive_session.console'):
                    with patch('ollamacode.interactive_session.Confirm.ask', return_value=True):
                        result = session._interactive_file_edit("test.py", "add print statement")
                        
                        assert "Successfully updated" in result
                        mock_write.assert_called_once()


def test_session_unavailable_service():
    """Test session handles unavailable Ollama service."""
    with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
        with patch('ollamacode.interactive_session.sys.exit') as mock_exit:
            mock_client = Mock()
            mock_client.is_available.return_value = False
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Mock the main loop to prevent it from running
            with patch.object(session, '_main_loop'):
                with patch('ollamacode.interactive_session.console'):
                    session.start()
                    
            mock_exit.assert_called_once_with(1)
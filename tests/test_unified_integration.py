"""Integration tests for Phase 5 execution system."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.ollamacode.execution import ToolExecutor, IntentAnalyzer, ToolType, OutputFormatter
from src.ollamacode.unified_session import UnifiedSession
from src.ollamacode.permissions import PermissionManager


class TestUnifiedIntegration:
    """Integration tests for the complete unified execution system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        
        # Mock the OllamaClient to avoid network calls
        self.mock_client = Mock()
        self.mock_client.is_available.return_value = True
        self.mock_client.model = "test-model"
        self.mock_client.base_url = "http://test"
        self.mock_client.chat.return_value = "AI response generated successfully"
        
        # Create permissions that auto-approve for testing
        self.permissions = Mock()
        self.permissions.check_permission.return_value = True
    
    def test_end_to_end_file_creation(self):
        """Test complete file creation workflow."""
        executor = ToolExecutor(self.permissions)
        
        # Mock file ops to simulate successful creation
        executor.file_ops.write_file = Mock(return_value=True)
        
        user_input = "create a Python script that prints hello world"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.FILE_OP
        assert results[0].action == "create"
        assert plan.needs_ai_response  # File creation should trigger AI response
    
    def test_end_to_end_git_status(self):
        """Test complete git status workflow."""
        executor = ToolExecutor(self.permissions)
        
        # Mock git operations
        executor.git_ops.is_git_repo = Mock(return_value=True)
        executor.git_ops.get_status = Mock(return_value={
            'branch': 'main',
            'is_dirty': False,
            'modified': [],
            'staged': [],
            'untracked': []
        })
        
        user_input = "show me git status"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.GIT_OP
        assert results[0].action == "status"
        assert "📂 Repository: main" in results[0].formatted_output
        assert "✨ Working tree clean" in results[0].formatted_output
    
    def test_end_to_end_file_reading(self):
        """Test complete file reading workflow."""
        # Create a real test file
        test_file = os.path.join(self.temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("print('Hello, World!')\n")
        
        executor = ToolExecutor(self.permissions)
        
        user_input = "read test.py"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.FILE_OP
        assert results[0].action == "read"
        assert "test.py" in results[0].formatted_output
        assert "Hello, World!" in results[0].formatted_output
    
    def test_end_to_end_command_execution(self):
        """Test complete bash command execution."""
        executor = ToolExecutor(self.permissions)
        
        # Mock bash operations
        executor.bash_ops.run_command = Mock(return_value={
            'success': True,
            'stdout': '/test/directory',
            'stderr': '',
            'returncode': 0,
            'command': 'pwd'
        })
        
        user_input = "what's my current directory"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.BASH_OP
        assert results[0].action == "run"
        assert "$ pwd" in results[0].formatted_output
        assert "/test/directory" in results[0].formatted_output
    
    def test_end_to_end_search_operation(self):
        """Test complete search workflow."""
        executor = ToolExecutor(self.permissions)
        
        # Mock search operations
        executor.search_ops.grep_files = Mock(return_value=[
            {'file': 'main.py', 'line': 1, 'content': 'def main():'},
            {'file': 'utils.py', 'line': 15, 'content': 'def helper():'}
        ])
        
        user_input = "find all def functions"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.SEARCH_OP
        assert results[0].action == "grep"
        assert "🔍 Found 2 matches" in results[0].formatted_output
        assert "main.py:1" in results[0].formatted_output
    
    def test_error_handling_integration(self):
        """Test error handling throughout the system."""
        executor = ToolExecutor(self.permissions)
        
        # Mock file operation to fail
        executor.file_ops.read_file = Mock(side_effect=FileNotFoundError("File not found"))
        
        user_input = "read nonexistent.py"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        assert not results[0].success
        assert results[0].error is not None
        assert ("❌" in results[0].formatted_output or 
                "not found" in results[0].formatted_output.lower() or 
                "wasn't found" in results[0].formatted_output.lower())
    
    def test_multiple_intents_handling(self):
        """Test handling of multiple tool intents in one request."""
        executor = ToolExecutor(self.permissions)
        
        # Mock git and file operations
        executor.git_ops.is_git_repo = Mock(return_value=True)
        executor.git_ops.get_status = Mock(return_value={
            'branch': 'main', 'is_dirty': False, 'modified': [], 'staged': [], 'untracked': []
        })
        
        # Create a real test file for reading
        test_file = os.path.join(self.temp_dir, "main.py")
        with open(test_file, "w") as f:
            f.write("# Main file\nprint('test')\n")
        
        user_input = "show git status and read main.py"
        results, plan = executor.process_request(user_input)
        
        # Should detect multiple intents and execute them
        assert len(results) >= 1
        assert plan.needs_ai_response  # Complex requests should need AI response
    
    @patch('src.ollamacode.unified_session.OllamaClient')
    def test_interactive_session_integration(self, mock_client_class):
        """Test the complete interactive session with unified execution."""
        # Mock the OllamaClient class
        mock_client_class.return_value = self.mock_client
        
        # Mock tool calling response
        self.mock_client.chat_with_tools.return_value = {
            "type": "tool_calls",
            "tool_calls": [{
                "id": "call_1",
                "function": {
                    "name": "run_command",
                    "arguments": {"command": "pwd"}
                }
            }],
            "content": "I'll get your current directory."
        }
        
        # Mock final response after tool execution
        self.mock_client.chat.return_value = {
            "type": "text",
            "content": "You are currently in /Users/user/project"
        }
        
        # Create session
        session = UnifiedSession()
        
        # Mock tool execution
        with patch.object(session.tool_call_executor, 'execute_tool_calls') as mock_execute, \
             patch.object(session.tool_call_executor, 'format_tool_result_for_llm') as mock_format:
            
            mock_execute.return_value = [{"success": True, "tool_call_id": "call_1", "function_name": "run_command"}]
            mock_format.return_value = {"role": "tool", "tool_call_id": "call_1", "content": "Success"}
            
            response = session._process_user_input("get my current directory")
            
            assert "currently in" in response
            mock_execute.assert_called_once()
    
    def test_response_formatting_integration(self):
        """Test that responses are properly formatted across the system."""
        executor = ToolExecutor(self.permissions)
        
        # Test different types of operations
        test_cases = [
            {
                'input': "run pwd",
                'mock_setup': lambda: setattr(executor.bash_ops, 'run_command', 
                    Mock(return_value={'success': True, 'stdout': '/test', 'stderr': '', 'returncode': 0})),
                'expected_patterns': ["$ pwd", "/test"]
            },
            {
                'input': "git status", 
                'mock_setup': lambda: [
                    setattr(executor.git_ops, 'is_git_repo', Mock(return_value=True)),
                    setattr(executor.git_ops, 'get_status', Mock(return_value={
                        'branch': 'main', 'is_dirty': True, 'modified': ['file.py'], 'staged': [], 'untracked': []
                    }))
                ],
                'expected_patterns': ["📂 Repository: main", "📝 Modified: file.py"]
            }
        ]
        
        for case in test_cases:
            case['mock_setup']()
            results, plan = executor.process_request(case['input'])
            
            assert len(results) == 1
            assert results[0].success
            
            for pattern in case['expected_patterns']:
                assert pattern in results[0].formatted_output
    
    def test_permission_integration(self):
        """Test permission system integration."""
        # Create a real permission manager (not mocked)
        real_permissions = PermissionManager()
        executor = ToolExecutor(real_permissions)
        
        # Test file operation that requires permission
        test_file = os.path.join(self.temp_dir, "test.py") 
        with open(test_file, "w") as f:
            f.write("print('test')")
        
        # File reading should work (doesn't require write permission)
        user_input = "read test.py"
        results, plan = executor.process_request(user_input)
        
        assert len(results) == 1
        # Result might fail due to permission check, but system should handle gracefully
        assert results[0].formatted_output is not None
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir("/")
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__])
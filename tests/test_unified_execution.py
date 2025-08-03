"""Unit tests for Phase 5 execution system."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ollamacode.execution import (
    IntentAnalyzer, ToolIntent, ToolType, 
    OutputFormatter, ErrorRecovery, ToolExecutor
)
from src.ollamacode.execution.error_recovery import ErrorType


class TestIntentAnalyzer:
    """Test intent detection system."""
    
    def test_file_creation_intent(self):
        """Test detection of file creation requests."""
        test_cases = [
            "write a file called test.py",
            "create a file that prints hello world",
            "make a script for data processing",
            "generate a Python file"
        ]
        
        for test_input in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            assert len(intents) >= 1
            file_intent = next((i for i in intents if i.type == ToolType.FILE_OP), None)
            assert file_intent is not None
            assert file_intent.action == "create"
    
    def test_file_read_intent(self):
        """Test detection of file reading requests."""
        test_cases = [
            "read the file main.py",
            "show me @test.js",
            "what's in config.json",
            "display the content of readme.md"
        ]
        
        for test_input in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            file_intent = next((i for i in intents if i.type == ToolType.FILE_OP), None)
            assert file_intent is not None
            assert file_intent.action == "read"
    
    def test_git_status_intent(self):
        """Test detection of git status requests."""
        test_cases = [
            "git status",
            "what files have changed",
            "show me the repo status",
            "current git status"
        ]
        
        for test_input in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            git_intent = next((i for i in intents if i.type == ToolType.GIT_OP), None)
            assert git_intent is not None
            assert git_intent.action == "status"
    
    def test_search_intent(self):
        """Test detection of search requests."""
        test_cases = [
            "find all TODO comments",
            "search for 'function main'",
            "grep for import statements",
            "look for error handling"
        ]
        
        for test_input in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            search_intent = next((i for i in intents if i.type == ToolType.SEARCH_OP), None)
            assert search_intent is not None
            assert search_intent.action == "grep"
    
    def test_bash_command_intent(self):
        """Test detection of bash command requests."""
        test_cases = [
            "run npm test",
            "execute python main.py",
            "get my current directory",
            "what's my pwd"
        ]
        
        for test_input in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            bash_intent = next((i for i in intents if i.type == ToolType.BASH_OP), None)
            assert bash_intent is not None
            assert bash_intent.action == "run"
    
    def test_filename_extraction(self):
        """Test filename extraction from user input."""
        test_cases = [
            ("read @main.py", "main.py"),
            ("edit the file test.js", "test.js"),
            ("show me config.json please", "config.json"),
        ]
        
        for test_input, expected_filename in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            file_intent = next((i for i in intents if i.type == ToolType.FILE_OP), None)
            assert file_intent is not None
            assert file_intent.target == expected_filename
    
    def test_no_intent_detected(self):
        """Test when no specific tool intent is detected."""
        test_cases = [
            "hello there",
            "how are you doing",
            "explain how sorting works",
            "what is the weather like"
        ]
        
        for test_input in test_cases:
            intents = IntentAnalyzer.analyze_intent(test_input)
            assert len(intents) == 1
            assert intents[0].type == ToolType.NONE


class TestOutputFormatter:
    """Test output formatting system."""
    
    def test_command_result_formatting(self):
        """Test command result formatting."""
        # Successful command
        result = OutputFormatter.format_command_result("ls -la", "total 8\n-rw-r--r-- 1 user user 100 test.txt")
        assert "$ ls -la" in result
        assert "total 8" in result
        
        # Command with error
        result = OutputFormatter.format_command_result("invalid_cmd", "", "command not found")
        assert "❌ Error:" in result
        assert "command not found" in result
        
        # Command with no output
        result = OutputFormatter.format_command_result("touch test.txt", "")
        assert "(no output)" in result
    
    def test_file_content_formatting(self):
        """Test file content formatting."""
        content = "def hello():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello()"
        result = OutputFormatter.format_file_content("test.py", content)
        
        assert "📄 test.py:" in result
        assert "def hello():" in result
    
    def test_git_status_formatting(self):
        """Test git status formatting."""
        status = {
            'branch': 'main',
            'is_dirty': True,
            'modified': ['file1.py', 'file2.js'],
            'staged': ['file3.py'],
            'untracked': ['new_file.txt']
        }
        
        result = OutputFormatter.format_git_status(status)
        assert "📂 Repository: main" in result
        assert "📝 Modified: file1.py, file2.js" in result
        assert "✅ Staged: file3.py" in result
        assert "❓ Untracked: new_file.txt" in result
    
    def test_search_results_formatting(self):
        """Test search results formatting."""
        results = [
            {'file': 'main.py', 'line': 10, 'content': 'def main():'},
            {'file': 'utils.py', 'line': 25, 'content': 'def helper_function():'}
        ]
        
        result = OutputFormatter.format_search_results("def", results)
        assert "🔍 Found 2 matches for 'def':" in result
        assert "main.py:10" in result
        assert "utils.py:25" in result
    
    def test_error_formatting(self):
        """Test error message formatting."""
        suggestions = ["Check file permissions", "Try using absolute path"]
        result = OutputFormatter.format_error("file reading", "Permission denied", suggestions)
        
        assert "❌ File reading failed: Permission denied" in result
        assert "💡 Suggestions:" in result
        assert "• Check file permissions" in result
        assert "• Try using absolute path" in result


class TestErrorRecovery:
    """Test error recovery system."""
    
    def test_error_classification(self):
        """Test error type classification."""
        test_cases = [
            ("No such file or directory", ErrorType.FILE_NOT_FOUND),
            ("Permission denied", ErrorType.PERMISSION_DENIED),
            ("Command not found", ErrorType.COMMAND_FAILED),
            ("Operation timed out", ErrorType.TIMEOUT),
            ("Random error message", ErrorType.UNKNOWN)
        ]
        
        for error_msg, expected_type in test_cases:
            error_type = ErrorRecovery.classify_error(error_msg)
            assert error_type == expected_type
    
    def test_error_context_creation(self):
        """Test error context creation."""
        error = FileNotFoundError("No such file: test.py")
        context = ErrorRecovery.create_error_context(error, "read test.py", "file reading")
        
        assert context.error_type == ErrorType.FILE_NOT_FOUND
        assert context.user_input == "read test.py"
        assert context.attempted_action == "file reading"
        assert len(context.suggestions) > 0
        assert context.fallback_response is not None
    
    def test_tool_error_handling(self):
        """Test tool error handling."""
        error = FileNotFoundError("test.py not found")
        result = ErrorRecovery.handle_tool_error(error, "file_operations", "read test.py")
        
        assert "❌" in result or "couldn't find" in result.lower()


class TestToolExecutor:
    """Test unified tool execution system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_permissions = Mock()
        self.mock_permissions.check_permission.return_value = True
        
        self.executor = ToolExecutor(self.mock_permissions)
        
        # Mock the tool instances
        self.executor.file_ops = Mock()
        self.executor.git_ops = Mock()
        self.executor.search_ops = Mock()
        self.executor.bash_ops = Mock()
    
    def test_file_read_execution(self):
        """Test file reading execution."""
        self.setUp()
        
        # Mock successful file read
        self.executor.file_ops.read_file.return_value = "print('Hello, World!')"
        
        results, plan = self.executor.process_request("read test.py")
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.FILE_OP
        assert results[0].action == "read"
        assert "test.py" in results[0].formatted_output
    
    def test_git_status_execution(self):
        """Test git status execution."""
        self.setUp()
        
        # Mock git repository check and status
        self.executor.git_ops.is_git_repo.return_value = True
        self.executor.git_ops.get_status.return_value = {
            'branch': 'main',
            'is_dirty': False
        }
        
        results, plan = self.executor.process_request("git status")
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.GIT_OP
        assert results[0].action == "status"
    
    def test_bash_command_execution(self):
        """Test bash command execution."""
        self.setUp()
        
        # Mock successful command execution
        self.executor.bash_ops.run_command.return_value = {
            'success': True,
            'stdout': '/Users/test/project',
            'stderr': '',
            'returncode': 0
        }
        
        results, plan = self.executor.process_request("run pwd")
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.BASH_OP
        assert results[0].action == "run"
        assert "pwd" in results[0].formatted_output
    
    def test_search_execution(self):
        """Test search execution."""
        self.setUp()
        
        # Mock search results
        self.executor.search_ops.grep_files.return_value = [
            {'file': 'main.py', 'line': 1, 'content': 'def main():'},
            {'file': 'utils.py', 'line': 10, 'content': 'def helper():'}
        ]
        
        results, plan = self.executor.process_request("find all def functions")
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].tool_type == ToolType.SEARCH_OP
        assert results[0].action == "grep"
    
    def test_error_handling_in_execution(self):
        """Test error handling during tool execution."""
        self.setUp()
        
        # Mock file operation failure
        self.executor.file_ops.read_file.side_effect = FileNotFoundError("File not found")
        
        results, plan = self.executor.process_request("read nonexistent.py")
        
        assert len(results) == 1
        assert not results[0].success
        assert results[0].error is not None
        assert results[0].formatted_output is not None
    
    def test_multiple_intents(self):
        """Test handling multiple intents in one request."""
        self.setUp()
        
        # Mock git operations
        self.executor.git_ops.is_git_repo.return_value = True
        self.executor.git_ops.get_status.return_value = {'branch': 'main', 'is_dirty': False}
        
        # Mock file operations
        self.executor.file_ops.read_file.return_value = "print('test')"
        
        results, plan = self.executor.process_request("show git status and read main.py")
        
        # Should detect multiple intents
        assert len(results) >= 1
        assert plan.needs_ai_response  # Complex requests should need AI response
    
    def test_response_combination(self):
        """Test combining tool results with AI response."""
        self.setUp()
        
        # Create mock results
        results = [
            Mock(success=True, formatted_output="✅ File created successfully"),
            Mock(success=True, formatted_output="📂 Repository: main branch")
        ]
        
        plan = Mock(needs_ai_response=True)
        ai_response = "I've completed both operations for you."
        
        combined = self.executor.format_combined_response(results, plan, ai_response)
        
        assert "✅ File created successfully" in combined
        assert "📂 Repository: main branch" in combined
        assert "I've completed both operations for you." in combined


if __name__ == "__main__":
    pytest.main([__file__])
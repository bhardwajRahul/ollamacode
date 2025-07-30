#!/usr/bin/env python3
"""Tests for enhanced error handling and suggestions."""

import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.error_handler import (
    _generate_error_suggestions, 
    create_detailed_error_message,
    show_helpful_error
)
from ollamacode.interactive_session import InteractiveSession


class TestErrorHandling:
    """Test enhanced error handling functionality."""
    
    def __init__(self):
        self.test_results = []
    
    def run_all_tests(self):
        """Run all error handling tests."""
        print("🚨 Running Enhanced Error Handling Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_permission_error_suggestions,
            self.test_file_not_found_suggestions,
            self.test_connection_error_suggestions,
            self.test_model_error_suggestions,
            self.test_git_error_suggestions,
            self.test_detailed_error_message_creation,
            self.test_contextual_suggestions,
            self.test_integration_with_file_operations
        ]
        
        for test in tests:
            try:
                print(f"\n📋 Running {test.__name__}...")
                result = test()
                self.test_results.append((test.__name__, "PASS" if result else "FAIL"))
                print(f"✅ {test.__name__}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                self.test_results.append((test.__name__, f"ERROR: {e}"))
                print(f"❌ {test.__name__}: ERROR - {e}")
        
        self.print_summary()
    
    def test_permission_error_suggestions(self) -> bool:
        """Test suggestions for permission-related errors."""
        error = "Permission denied"
        suggestions = _generate_error_suggestions(error, "file write")
        
        # Should contain permission-related suggestions
        suggestion_text = " ".join(suggestions).lower()
        
        expected_terms = ["permission", "approve-all", "write-protected"]
        return all(term in suggestion_text for term in expected_terms)
    
    def test_file_not_found_suggestions(self) -> bool:
        """Test suggestions for file not found errors."""
        error = "No such file or directory"
        suggestions = _generate_error_suggestions(error, "file")
        
        suggestion_text = " ".join(suggestions).lower()
        
        expected_terms = ["file path", "tab completion", "absolute paths"]
        return all(term in suggestion_text for term in expected_terms)
    
    def test_connection_error_suggestions(self) -> bool:
        """Test suggestions for connection errors."""
        error = "Connection refused"
        suggestions = _generate_error_suggestions(error, "chat")
        
        suggestion_text = " ".join(suggestions).lower()
        
        expected_terms = ["ollama serve", "config", "model"]
        return all(term in suggestion_text for term in expected_terms)
    
    def test_model_error_suggestions(self) -> bool:
        """Test suggestions for model-related errors."""
        error = "Model not available"
        suggestions = _generate_error_suggestions(error, "model")
        
        suggestion_text = " ".join(suggestions).lower()
        
        expected_terms = ["ollama pull", "ollama list", "switch"]
        return all(term in suggestion_text for term in expected_terms)
    
    def test_git_error_suggestions(self) -> bool:
        """Test suggestions for git-related errors."""
        error = "Not a git repository"
        suggestions = _generate_error_suggestions(error, "git")
        
        suggestion_text = " ".join(suggestions).lower()
        
        expected_terms = ["git init", "directory", "git --version"]
        return all(term in suggestion_text for term in expected_terms)
    
    def test_detailed_error_message_creation(self) -> bool:
        """Test creation of detailed error messages."""
        error = ValueError("Invalid input")
        context = "file creation"
        user_action = "write python file"
        
        message = create_detailed_error_message(error, context, user_action)
        
        # Should contain all components
        required_parts = [
            "ValueError",
            "Invalid input",
            "file creation",
            "write python file",
            "Suggestions:",
            "/help"
        ]
        
        return all(part in message for part in required_parts)
    
    def test_contextual_suggestions(self) -> bool:
        """Test that suggestions are contextual based on command type."""
        # File operation context
        file_suggestions = _generate_error_suggestions("error", "file write")
        file_text = " ".join(file_suggestions).lower()
        
        # Git operation context  
        git_suggestions = _generate_error_suggestions("error", "git status")
        git_text = " ".join(git_suggestions).lower()
        
        # Model operation context
        model_suggestions = _generate_error_suggestions("error", "model chat")
        model_text = " ".join(model_suggestions).lower()
        
        # Check that each context gets appropriate suggestions
        return (
            "permission" in file_text and
            "git" in git_text and
            "ollama" in model_text
        )
    
    def test_integration_with_file_operations(self) -> bool:
        """Test error handling integration with file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            session = InteractiveSession()
            session.permissions.approve_all_for_session()
            
            # Test reading a non-existent file
            with patch('ollamacode.error_handler.console') as mock_console:
                result = session.file_ops.read_file("nonexistent.txt")
                
                # Should return None and show helpful error
                if result is not None:
                    return False
                
                # Should have called show_helpful_error
                if not mock_console.print.called:
                    return False
            
            return True
    
    def test_error_message_formatting(self) -> bool:
        """Test that error messages are properly formatted."""
        # Test with console mocking to capture output
        with patch('ollamacode.error_handler.console') as mock_console:
            show_helpful_error("test command", "test error", "test suggestion")
            
            # Should have printed error message
            if not mock_console.print.called:
                return False
            
            # Check call arguments contain expected formatting
            calls = [str(call) for call in mock_console.print.call_args_list]
            call_text = " ".join(calls)
            
            return "test command" in call_text and "test error" in call_text
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 Enhanced Error Handling Test Results Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} error handling tests passed")
        
        if passed == total:
            print("🎉 All error handling tests passed!")
            print("✨ Enhanced error messages with suggestions are working correctly.")
            print("\n🔧 Error handling improvements:")
            print("  • Contextual suggestions based on error type")
            print("  • Detailed error messages with context")
            print("  • Integration with file operations") 
            print("  • Permission, file, git, and model error guidance")
        else:
            print(f"⚠️  {total - passed} tests failed. Review error handling implementation.")


def main():
    """Run the error handling test suite."""
    tester = TestErrorHandling()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
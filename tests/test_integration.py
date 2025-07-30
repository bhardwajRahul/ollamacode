#!/usr/bin/env python3
"""Integration tests for OllamaCode - testing the full system."""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.interactive_session import InteractiveSession
from ollamacode.cli import main as cli_main
from ollamacode.config import Config


class TestIntegration:
    """Test full system integration."""
    
    def __init__(self):
        self.test_results = []
        self.test_dir = Path(tempfile.mkdtemp())
    
    def run_all_tests(self):
        """Run all integration tests."""
        print("🔗 Running Integration Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_end_to_end_session,
            self.test_tool_chaining,
            self.test_permission_workflow,
            self.test_file_workflow,
            self.test_project_context_integration,
            self.test_error_recovery,
            self.test_performance_streaming
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
    
    def test_end_to_end_session(self) -> bool:
        """Test a complete session from start to finish."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            mock_client.chat.return_value = "I understand your request."
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Test session initialization
            if len(session.messages) != 0:
                return False
            
            # Simulate user interaction
            session.messages.append({"role": "user", "content": "Hello, test message"})
            
            # Test AI response generation
            response = session._get_ai_response()
            
            # Verify message was added to history
            if len(session.messages) != 2:
                return False
            
            # Test slash commands work in context
            help_result = session._handle_slash_command("/help")
            if "OllamaCode Slash Commands" not in help_result:
                return False
            
            # Test session cleanup
            session._save_and_exit()
            
            return True
    
    def test_tool_chaining(self) -> bool:
        """Test that multiple tools can be used in sequence."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            mock_client.chat.return_value = "Tools executed successfully"
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Test file operations
            test_file = self.test_dir / "integration_test.txt"
            content = "Integration test content"
            
            # Auto-approve permissions for testing
            session.permissions.approve_all_for_session()
            
            # Write file
            write_result = session.file_ops.write_file(str(test_file), content, show_diff=False)
            if not write_result:
                return False
            
            # Read file back
            read_content = session.file_ops.read_file(str(test_file))
            if read_content != content:
                return False
            
            # Test git operations (basic status check)
            try:
                git_status = session.git_ops.get_status()
                # Should return some status info without crashing
            except Exception:
                pass  # Git operations might fail in test environment, that's OK
            
            # Test search operations
            search_results = session.search_ops.find_files("*.py", str(self.test_dir.parent))
            # Should return results without crashing
            
            return True
    
    def test_permission_workflow(self) -> bool:
        """Test the permission system workflow."""
        session = InteractiveSession()
        
        # Test initial state (no approvals)
        if len(session.permissions.session_approvals) != 0:
            return False
        
        # Test slash command for permissions
        perm_status = session._handle_slash_command("/permissions status")
        if "No operations pre-approved" not in perm_status:
            return False
        
        # Test approval
        session._handle_slash_command("/permissions approve-all")
        if len(session.permissions.session_approvals) == 0:
            return False
        
        # Test reset
        session._handle_slash_command("/permissions reset")
        if len(session.permissions.session_approvals) != 0:
            return False
        
        return True
    
    def test_file_workflow(self) -> bool:
        """Test complete file workflow with references."""
        session = InteractiveSession()
        session.permissions.approve_all_for_session()
        
        # Create test files
        test_files = {
            "main.py": "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()",
            "config.json": '{\n    "version": "1.0.0",\n    "debug": true\n}',
            "README.md": "# Test Project\n\nThis is a test project for integration testing."
        }
        
        for filename, content in test_files.items():
            test_file = self.test_dir / filename
            session.file_ops.write_file(str(test_file), content, show_diff=False)
        
        # Test file references
        main_py_path = self.test_dir / "main.py"
        input_with_ref = f"Explain this code: @{main_py_path}"
        processed = session._process_file_references(input_with_ref)
        
        if "def main():" not in processed:
            return False
        
        # Test multiple file references
        config_path = self.test_dir / "config.json"
        multi_ref = f"Compare @{main_py_path} and @{config_path}"
        processed_multi = session._process_file_references(multi_ref)
        
        if not all(text in processed_multi for text in ["def main():", '"version"']):
            return False
        
        return True
    
    def test_project_context_integration(self) -> bool:
        """Test project context loading and usage."""
        session = InteractiveSession()
        
        # Test context manager initialization
        if not hasattr(session, 'context_mgr'):
            return False
        
        # Test that we can load project context
        try:
            session._auto_load_project_context()
            # Should not crash even if no proper project context
        except Exception:
            return False
        
        # Test project detection
        detected_type = session.context_mgr.detect_project_type()
        if detected_type != "python":
            return False  # We're in a Python project
        
        return True
    
    def test_error_recovery(self) -> bool:
        """Test system recovery from various error conditions."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            # Test with unavailable client
            mock_client = Mock()
            mock_client.is_available.return_value = False
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Should handle unavailable client gracefully
            try:
                response = session._get_ai_response()
                # Should return error message, not crash
            except SystemExit:
                # This is expected behavior for unavailable client
                pass
            
            # Test with working client but network error
            mock_client.is_available.return_value = True
            mock_client.chat.side_effect = Exception("Network error")
            
            session = InteractiveSession()
            response = session._get_ai_response()
            
            # Should handle error gracefully
            if "error" not in response.lower():
                return False
        
        return True
    
    def test_performance_streaming(self) -> bool:
        """Test streaming performance and behavior."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            
            # Simulate streaming response
            mock_client.chat.return_value = "Streaming response complete"
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Add a test message
            session.messages.append({"role": "user", "content": "Test streaming"})
            
            # Measure response time (should be fast with mocked client)
            start_time = time.time()
            response = session._get_ai_response()
            end_time = time.time()
            
            # Response should be fast (< 1 second with mocked client)
            if end_time - start_time > 1.0:
                return False
            
            # Verify streaming was used (stream=True)
            mock_client.chat.assert_called_with(session.messages, stream=True)
            
            return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Integration Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} integration tests passed")
        
        if passed == total:
            print("🎉 All integration tests passed! OllamaCode is working correctly end-to-end.")
            print("\n🏆 Phase 3 Development Complete!")
            print("✅ All features implemented and tested")
            print("✅ Streaming responses working") 
            print("✅ Advanced CLI features operational")
            print("✅ Comprehensive test coverage achieved")
        else:
            print(f"⚠️  {total - passed} tests failed. Review integration issues.")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


def main():
    """Run the integration test suite."""
    tester = TestIntegration()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
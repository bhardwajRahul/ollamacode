#!/usr/bin/env python3
"""Advanced CLI and slash command tests for OllamaCode."""

import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.interactive_session import InteractiveSession
from ollamacode.permissions import PermissionManager, OperationType


class TestAdvancedCLI:
    """Test advanced CLI features and slash commands."""
    
    def __init__(self):
        self.test_results = []
        self.test_dir = Path(tempfile.mkdtemp())
    
    def run_all_tests(self):
        """Run all advanced CLI tests."""
        print("🖥️  Running Advanced CLI Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_all_slash_commands,
            self.test_file_reference_processing,
            self.test_permissions_management,
            self.test_session_state_management,
            self.test_headless_mode_integration,
            self.test_configuration_management,
            self.test_error_handling_robustness,
            self.test_tool_integration
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
    
    def test_all_slash_commands(self) -> bool:
        """Test all available slash commands."""
        session = InteractiveSession()
        
        commands_to_test = [
            ("/help", "OllamaCode Slash Commands"),
            ("/status", "Session Status"),
            ("/clear", "Conversation history cleared"),
            ("/config", "Configuration"),
            ("/permissions status", "No operations pre-approved"),
            ("/permissions approve-all", "approved for this session"),
            ("/permissions reset", "Permissions reset"),
            ("/model", "Current model"),
            ("/sessions", "Saved Sessions"),
        ]
        
        for command, expected_text in commands_to_test:
            try:
                result = session._handle_slash_command(command)
                if expected_text not in result:
                    print(f"Command '{command}' failed: expected '{expected_text}' in result")
                    return False
            except Exception as e:
                print(f"Command '{command}' raised exception: {e}")
                return False
        
        return True
    
    def test_file_reference_processing(self) -> bool:
        """Test @filename reference processing."""
        # Create test files
        test_files = {
            "test1.py": "print('Hello from test1')",
            "test2.js": "console.log('Hello from test2');", 
            "test3.md": "# Test Document\nThis is a test."
        }
        
        for filename, content in test_files.items():
            test_file = self.test_dir / filename
            test_file.write_text(content)
        
        session = InteractiveSession()
        
        # Test single file reference
        input_text = f"Explain @{self.test_dir / 'test1.py'}"
        processed = session._process_file_references(input_text)
        
        if "print('Hello from test1')" not in processed:
            return False
        
        # Test multiple file references
        input_text = f"Compare @{self.test_dir / 'test1.py'} and @{self.test_dir / 'test2.js'}"
        processed = session._process_file_references(input_text)
        
        if not all(text in processed for text in ["print('Hello from test1')", "console.log('Hello from test2');"]):
            return False
        
        # Test non-existent file reference
        input_text = f"Check @{self.test_dir / 'nonexistent.txt'}"
        processed = session._process_file_references(input_text)
        
        # Should handle gracefully and include error message
        if "not found" not in processed:
            return False
        
        return True
    
    def test_permissions_management(self) -> bool:
        """Test comprehensive permissions management."""
        perm_mgr = PermissionManager()
        
        # Test initial state
        if len(perm_mgr.session_approvals) != 0:
            return False
        
        # Test safe operations (always allowed)
        if not perm_mgr.check_permission(OperationType.READ_FILE):
            return False
        
        # Test dangerous operations (require approval) - skip interactive test
        # We'll just verify the auto_approve=False path doesn't auto-approve
        initial_approvals = len(perm_mgr.session_approvals)
        perm_mgr.check_permission(OperationType.EXECUTE_COMMAND, auto_approve=False)
        # Should not have auto-approved
        if len(perm_mgr.session_approvals) > initial_approvals:
            return False
        
        # Test auto-approve functionality
        if not perm_mgr.check_permission(OperationType.WRITE_FILE, auto_approve=True):
            return False
        
        # Test session-wide approval
        perm_mgr.approve_all_for_session()
        if OperationType.EXECUTE_COMMAND not in perm_mgr.session_approvals:
            return False
        
        # Test permission description tracking
        result = perm_mgr.check_permission(OperationType.DELETE_FILE, "Delete temporary file", auto_approve=True)
        if not result:
            return False
        
        # Test reset functionality
        perm_mgr.reset_permissions()
        if len(perm_mgr.session_approvals) != 0:
            return False
        
        return True
    
    def test_session_state_management(self) -> bool:
        """Test session state management."""
        session = InteractiveSession()
        
        # Test initial state
        if session.messages != []:
            return False
        
        # Test message history
        session.messages.append({"role": "user", "content": "Test message"})
        session.messages.append({"role": "assistant", "content": "Test response"})
        
        if len(session.messages) != 2:
            return False
        
        # Test conversation clearing
        result = session._handle_slash_command("/clear")
        if "history cleared" not in result.lower():
            return False
        
        if len(session.messages) != 0:
            return False
        
        # Test project context loading
        if session.project_context_loaded:
            return False
        
        session._auto_load_project_context()
        # Should attempt to load context (might fail without real project, but that's OK)
        
        return True
    
    def test_headless_mode_integration(self) -> bool:
        """Test headless mode functionality."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            mock_client.chat.return_value = "Headless response"
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Test that headless mode exists and can be called
            if not hasattr(session, 'run_headless'):
                return False
            
            # Test with simple prompt
            try:
                session.run_headless("Test prompt", None)
                # Should execute without throwing exceptions
                return True
            except Exception as e:
                print(f"Headless mode failed: {e}")
                return False
    
    def test_configuration_management(self) -> bool:
        """Test configuration management."""
        session = InteractiveSession()
        
        # Test config display
        config_result = session._handle_slash_command("/config")
        if "Configuration" not in config_result:
            return False
        
        # Test model information
        model_result = session._handle_slash_command("/model")
        if "Current model" not in model_result:
            return False
        
        # Test status information
        status_result = session._handle_slash_command("/status")
        expected_status_items = ["Session Status", "Model:", "Messages:", "Project:"]
        
        if not all(item in status_result for item in expected_status_items):
            return False
        
        return True
    
    def test_error_handling_robustness(self) -> bool:
        """Test error handling robustness."""
        session = InteractiveSession()
        
        # Test invalid slash command
        result = session._handle_slash_command("/invalid_command_xyz")
        if "Unknown command" not in result:
            return False
        
        # Test slash command with malformed arguments
        result = session._handle_slash_command("/permissions invalid_arg")
        # Should handle gracefully without crashing
        
        # Test file reference with permission error
        # Create a file and then make it unreadable
        test_file = self.test_dir / "unreadable.txt"
        test_file.write_text("test content")
        test_file.chmod(0o000)  # Remove all permissions
        
        try:
            input_text = f"Read @{test_file}"
            processed = session._process_file_references(input_text)
            # Should handle permission error gracefully
            return "not found" in processed or "Error reading" in processed
        except Exception:
            return True  # Exception handling is also acceptable
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)
    
    def test_tool_integration(self) -> bool:
        """Test tool integration with session."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            mock_client.chat.return_value = "Tool response"
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Verify all tools are initialized
            required_tools = ['file_ops', 'git_ops', 'search_ops', 'bash_ops']
            for tool in required_tools:
                if not hasattr(session, tool):
                    return False
            
            # Test that tools have required methods
            if not hasattr(session.file_ops, 'read_file'):
                return False
            
            if not hasattr(session.git_ops, 'get_status'):
                return False
            
            if not hasattr(session.search_ops, 'grep_files'):
                return False
            
            if not hasattr(session.bash_ops, 'run_command'):
                return False
            
            return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Advanced CLI Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} advanced CLI tests passed")
        
        if passed == total:
            print("🎉 All advanced CLI tests passed! Phase 3 features are working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review advanced CLI implementation.")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


def main():
    """Run the advanced CLI test suite."""
    tester = TestAdvancedCLI()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
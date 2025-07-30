#!/usr/bin/env python3
"""Test suite for Phase 3 CLI enhancements."""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.cli import main
from ollamacode.interactive_session import InteractiveSession
from ollamacode.permissions import PermissionManager, OperationType
from ollamacode.diff_utils import DiffPreview
from ollamacode.tools.file_ops import FileOperations


class TestPhase3:
    """Test Phase 3 CLI enhancements."""
    
    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_results = []
        
    def run_all_tests(self):
        """Run all Phase 3 tests."""
        print("🧪 Running Phase 3 Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_cli_help,
            self.test_permission_system,
            self.test_diff_preview,
            self.test_file_operations,
            self.test_slash_commands,
            self.test_file_references,
            self.test_headless_mode,
            self.test_session_persistence
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
        
    def test_cli_help(self) -> bool:
        """Test CLI help functionality."""
        try:
            # Test main help
            result = subprocess.run([
                sys.executable, "-m", "ollamacode.cli", "--help"
            ], cwd=str(Path(__file__).parent.parent / "src"), capture_output=True, text=True)
            
            expected_flags = ["-p", "--prompt", "-c", "--continue", "--model", "--url"]
            help_text = result.stdout
            
            return all(flag in help_text for flag in expected_flags)
        except Exception:
            return False
    
    def test_permission_system(self) -> bool:
        """Test permission management system."""
        perm_mgr = PermissionManager()
        
        # Test safe operation (no approval needed)
        if not perm_mgr.check_permission(OperationType.READ_FILE, auto_approve=True):
            return False
        
        # Test dangerous operation with auto-approve
        if not perm_mgr.check_permission(OperationType.WRITE_FILE, auto_approve=True):
            return False
        
        # Test session approval
        perm_mgr.approve_all_for_session()
        if OperationType.EXECUTE_COMMAND not in perm_mgr.session_approvals:
            return False
        
        # Test reset
        perm_mgr.reset_permissions()
        if len(perm_mgr.session_approvals) != 0:
            return False
        
        return True
    
    def test_diff_preview(self) -> bool:
        """Test diff preview functionality."""
        original = "Line 1\nLine 2\nLine 3"
        modified = "Line 1\nModified Line 2\nLine 3\nNew Line 4"
        
        # Test diff generation
        diff = DiffPreview.generate_diff(original, modified, "test.txt")
        
        if "Modified Line 2" not in diff or "New Line 4" not in diff:
            return False
        
        # Test change summary
        summary = DiffPreview.get_change_summary(original, modified)
        
        return "+1 lines" in summary and "~1 modified" in summary
    
    def test_file_operations(self) -> bool:
        """Test file operations with permissions."""
        test_file = self.test_dir / "test.txt"
        perm_mgr = PermissionManager()
        perm_mgr.approve_all_for_session()  # Auto-approve for testing
        
        file_ops = FileOperations(perm_mgr)
        
        # Test write
        if not file_ops.write_file(str(test_file), "Test content", show_diff=False):
            return False
        
        # Test read
        content = file_ops.read_file(str(test_file))
        if content != "Test content":
            return False
        
        # Test overwrite with diff (but skip preview for testing)
        if not file_ops.write_file(str(test_file), "Modified content", show_diff=False):
            return False
        
        return True
    
    def test_slash_commands(self) -> bool:
        """Test slash command parsing."""
        # Create a mock session for testing
        session = InteractiveSession()
        
        # Test help command
        help_result = session._handle_slash_command("/help")
        if "OllamaCode Slash Commands" not in help_result:
            return False
        
        # Test status command  
        status_result = session._handle_slash_command("/status")
        if "Session Status" not in status_result:
            return False
        
        # Test permissions command
        perm_result = session._handle_slash_command("/permissions status")
        if "No operations pre-approved" not in perm_result:
            return False
        
        return True
    
    def test_file_references(self) -> bool:
        """Test @filename reference processing."""
        # Create test file
        test_file = self.test_dir / "reference_test.py"
        test_file.write_text("print('Hello, World!')")
        
        session = InteractiveSession()
        
        # Test file reference processing
        input_text = f"Explain this code: @{test_file}"
        processed = session._process_file_references(input_text)
        
        return "print('Hello, World!')" in processed and "File:" in processed
    
    def test_headless_mode(self) -> bool:
        """Test headless mode functionality."""
        try:
            # Create a simple test - just check that headless mode doesn't crash
            # Note: This requires Ollama to be running, so we'll just test the setup
            session = InteractiveSession()
            
            # Test that run_headless method exists and can be called
            # (We can't actually test it without Ollama running)
            return hasattr(session, 'run_headless')
        except Exception:
            return False
    
    def test_session_persistence(self) -> bool:
        """Test session save/load functionality."""
        session = InteractiveSession()
        
        # Add some test messages
        session.messages = [
            {"role": "user", "content": "Test message 1"},
            {"role": "assistant", "content": "Test response 1"}
        ]
        
        # Test save
        session._save_and_exit()
        
        # Test that conversation files are created
        conv_dir = session.context_mgr.conversations_dir
        conv_files = list(conv_dir.glob("*.json"))
        
        return len(conv_files) > 0
    
    def print_summary(self):
        """Print test results summary."""
        print("\\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\\n📈 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Phase 3 implementation is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review implementation.")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


def main():
    """Run the test suite."""
    tester = TestPhase3()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Integration tests for auto-completion in interactive session."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.interactive_session import InteractiveSession


class TestAutoCompleteIntegration:
    """Test auto-completion integration with interactive session."""
    
    def __init__(self):
        self.test_results = []
    
    def run_all_tests(self):
        """Run all auto-completion integration tests."""
        print("🔍 Running Auto-Completion Integration Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_completion_command,
            self.test_slash_command_hints,
            self.test_completion_in_help,
            self.test_context_aware_completion
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
    
    def test_completion_command(self) -> bool:
        """Test the /complete slash command."""
        session = InteractiveSession()
        
        # Test /complete without arguments (should show help)
        result = session._handle_slash_command("/complete")
        
        if "Auto-Completion Help" not in result:
            return False
        
        if "Available Commands" not in result:
            return False
        
        # Test /complete with partial command
        result = session._handle_slash_command("/complete /h")
        
        if "Completions for '/h'" not in result or "Slash Commands" not in result:
            return False
        
        return True
    
    def test_slash_command_hints(self) -> bool:
        """Test that completion hints are shown for partial slash commands."""
        session = InteractiveSession()
        
        # Test hint showing method
        with patch('ollamacode.interactive_session.console') as mock_console:
            session._maybe_show_completion_hints("/h")
            
            # Should have printed completion hints
            if not mock_console.print.called:
                return False
        
        # Test with complete command (should not show hints)
        with patch('ollamacode.interactive_session.console') as mock_console:
            session._maybe_show_completion_hints("/help")
            
            # Should not print hints for complete commands
            if mock_console.print.called:
                return False
        
        return True
    
    def test_completion_in_help(self) -> bool:
        """Test that completion is mentioned in help."""
        session = InteractiveSession()
        
        help_result = session._handle_slash_command("/help")
        
        # Should mention the completion command
        if "/complete" not in help_result:
            return False
        
        return True
    
    def test_context_aware_completion(self) -> bool:
        """Test context-aware completion suggestions."""
        session = InteractiveSession()
        
        # Test completion suggestions method
        with patch('ollamacode.interactive_session.console') as mock_console:
            session._show_completion_suggestions("help me")
            
            # Should show suggestions
            if not mock_console.print.called:
                return False
        
        return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 Auto-Completion Integration Test Results Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} auto-completion integration tests passed")
        
        if passed == total:
            print("🎉 All auto-completion integration tests passed!")
            print("💡 Enhanced command completion is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review auto-completion integration.")


def main():
    """Run the auto-completion integration test suite."""
    tester = TestAutoCompleteIntegration()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
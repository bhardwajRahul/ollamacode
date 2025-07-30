#!/usr/bin/env python3
"""Tests for the auto-completion system."""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.autocomplete import AutoCompleter


class TestAutoCompleter:
    """Test the auto-completion functionality."""
    
    def __init__(self):
        self.test_results = []
        self.test_dir = Path(tempfile.mkdtemp())
    
    def run_all_tests(self):
        """Run all auto-completion tests."""
        print("🔍 Running Auto-Completion Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_slash_command_completion,
            self.test_partial_command_completion,
            self.test_command_argument_completion,
            self.test_file_reference_completion,
            self.test_context_aware_suggestions,
            self.test_completion_formatting,
            self.test_command_validation,
            self.test_help_system
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
    
    def test_slash_command_completion(self) -> bool:
        """Test basic slash command completion."""
        # Test completing '/h' -> should suggest '/help'
        completions = AutoCompleter.get_slash_completions('/h')
        
        if not completions:
            return False
        
        commands = [cmd for cmd, desc in completions]
        if '/help' not in commands:
            return False
        
        # Test completing '/c' -> should suggest '/clear', '/config', '/cache'
        completions = AutoCompleter.get_slash_completions('/c')
        commands = [cmd for cmd, desc in completions]
        
        expected = ['/clear', '/config', '/cache']
        if not all(cmd in commands for cmd in expected):
            return False
        
        return True
    
    def test_partial_command_completion(self) -> bool:
        """Test partial command name completion."""
        # Test '/mod' -> should complete to '/model'
        completions = AutoCompleter.get_slash_completions('/mod')
        
        if not completions:
            return False
        
        commands = [cmd for cmd, desc in completions]
        if '/model' not in commands:
            return False
        
        # Test '/perm' -> should complete to '/permissions'
        completions = AutoCompleter.get_slash_completions('/perm')
        commands = [cmd for cmd, desc in completions]
        
        if '/permissions' not in commands:
            return False
        
        return True
    
    def test_command_argument_completion(self) -> bool:
        """Test completion of command arguments."""
        # Test '/permissions s' -> should suggest 'status'
        completions = AutoCompleter.get_slash_completions('/permissions s')
        
        if not completions:
            return False
        
        commands = [cmd for cmd, desc in completions]
        if '/permissions status' not in commands:
            return False
        
        # Test '/cache c' -> should suggest 'clear'
        completions = AutoCompleter.get_slash_completions('/cache c')
        commands = [cmd for cmd, desc in completions]
        
        if '/cache clear' not in commands:
            return False
        
        return True
    
    def test_file_reference_completion(self) -> bool:
        """Test file reference completion."""
        # Create test files
        test_files = [
            'test.py',
            'main.js',
            'config.json',
            'README.md',
            'script.sh'
        ]
        
        for filename in test_files:
            (self.test_dir / filename).touch()
        
        # Test completion in the test directory
        os.chdir(self.test_dir)
        
        # Test '@test' -> should suggest something with test.py
        completions = AutoCompleter.get_file_completions('@test')
        
        if not completions:
            return False
        
        if not any('test.py' in comp for comp in completions):
            return False
        
        # Test '@main' -> should suggest something with main.js
        completions = AutoCompleter.get_file_completions('@main')
        
        if not any('main.js' in comp for comp in completions):
            return False
        
        return True
    
    def test_context_aware_suggestions(self) -> bool:
        """Test context-aware completion suggestions."""
        # Test help-related input
        completions = AutoCompleter.get_context_completions('help me', {})
        
        if not completions:
            return False
        
        suggestions = [suggestion for suggestion, desc in completions]
        if not any('help' in suggestion for suggestion in suggestions):
            return False
        
        # Test git-related input
        completions = AutoCompleter.get_context_completions('git status', {})
        suggestions = [suggestion for suggestion, desc in completions]
        
        if not any('git' in suggestion for suggestion in suggestions):
            return False
        
        return True
    
    def test_completion_formatting(self) -> bool:
        """Test formatting of completion suggestions."""
        suggestions = {
            'slash_commands': [('/help', 'Show help information'), ('/clear', 'Clear conversation')],
            'file_references': ['@test.py', '@main.js'],
            'context_suggestions': [('help me debug', 'Get debugging assistance')]
        }
        
        formatted = AutoCompleter.format_completion_display(suggestions)
        
        if not formatted:
            return False
        
        # Should contain section headers
        if 'Slash Commands:' not in formatted:
            return False
        
        if 'File References:' not in formatted:
            return False
        
        if 'Suggestions:' not in formatted:
            return False
        
        return True
    
    def test_command_validation(self) -> bool:
        """Test command validation."""
        # Valid complete commands
        valid_commands = [
            '/help',
            '/clear',
            '/exit',
            '/permissions status',
            '/cache clear'
        ]
        
        for cmd in valid_commands:
            if not AutoCompleter.is_complete_command(cmd):
                return False
        
        # Invalid or incomplete commands
        invalid_commands = [
            '/invalid',
            '/permissions',  # Missing required argument
            '/cache',        # Missing required argument
            'help',          # Not a slash command
            ''
        ]
        
        for cmd in invalid_commands:
            if AutoCompleter.is_complete_command(cmd):
                return False
        
        return True
    
    def test_help_system(self) -> bool:
        """Test command help system."""
        # Test help for existing command
        help_text = AutoCompleter.get_command_help('/help')
        
        if not help_text:
            return False
        
        if 'Show help information' not in help_text:
            return False
        
        # Test help for command with arguments
        help_text = AutoCompleter.get_command_help('/permissions')
        
        if 'Usage:' not in help_text:
            return False
        
        if 'Examples:' not in help_text:
            return False
        
        # Test help for non-existent command
        help_text = AutoCompleter.get_command_help('/nonexistent')
        
        if 'Unknown command' not in help_text:
            return False
        
        return True
    
    def test_suggest_completions_integration(self) -> bool:
        """Test the main suggestion integration."""
        # Test slash command suggestions
        suggestions = AutoCompleter.suggest_completions('/h')
        
        if not suggestions['slash_commands']:
            return False
        
        # Test file reference suggestions (need to be in test directory)
        os.chdir(self.test_dir)
        (self.test_dir / 'example.py').touch()
        
        suggestions = AutoCompleter.suggest_completions('explain @ex')
        
        # Should detect the @ex pattern
        if not suggestions['file_references']:
            return False
        
        return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Auto-Completion Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} auto-completion tests passed")
        
        if passed == total:
            print("🎉 All auto-completion tests passed! Command completion is working correctly.")
            print("\n📝 Available commands:")
            commands = AutoCompleter.get_all_commands()
            for i, cmd in enumerate(commands):
                if i % 4 == 0:
                    print()
                print(f"{cmd:15}", end="")
            print()
        else:
            print(f"⚠️  {total - passed} tests failed. Review auto-completion implementation.")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


def main():
    """Run the auto-completion test suite."""
    tester = TestAutoCompleter()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
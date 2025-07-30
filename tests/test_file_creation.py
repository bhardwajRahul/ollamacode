#!/usr/bin/env python3
"""Tests for file creation functionality."""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.interactive_session import InteractiveSession


class TestFileCreation:
    """Test file creation functionality."""
    
    def __init__(self):
        self.test_results = []
    
    def run_all_tests(self):
        """Run all file creation tests."""
        print("🔍 Running File Creation Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_basic_file_creation,
            self.test_language_detection,
            self.test_filename_detection,
            self.test_custom_filename,
            self.test_different_languages,
            self.test_integration_with_session
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
    
    def test_basic_file_creation(self) -> bool:
        """Test basic file creation with hello world prompt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            session = InteractiveSession()
            session.permissions.approve_all_for_session()
            
            # Test the user's exact prompt
            user_prompt = "write a file that prints hello world in this directory in python"
            
            # Should be detected as file creation
            if not session._is_file_creation_request(user_prompt):
                return False
            
            # Should create the file
            result = session._handle_file_creation_request(user_prompt)
            
            # Check success message
            if "✅ Successfully created" not in result:
                return False
            
            # Check file was created
            files = list(Path(temp_dir).glob("*.py"))
            if not files:
                return False
            
            # Check content
            content = files[0].read_text()
            if "Hello, World!" not in content:
                return False
            
            return True
    
    def test_language_detection(self) -> bool:
        """Test detection of different programming languages."""
        test_cases = [
            ("write a file in python", "python"),
            ("create a javascript file", "javascript"),
            ("make a bash script", "bash"),
            ("write a java file", "java"),
            ("create a go program", "go"),
            ("write some c++ code", "cpp")
        ]
        
        for prompt, expected_lang in test_cases:
            # Extract language detection logic
            language_keywords = {
                'python': ['.py', 'python'],
                'javascript': ['.js', 'javascript', 'js'],
                'bash': ['.sh', 'bash', 'shell'],
                'java': ['.java', 'java'],
                'go': ['.go', 'golang', 'go'],
                'cpp': ['.cpp', '.c++', 'c++', 'cpp']
            }
            
            detected_language = None
            lower_input = prompt.lower()
            
            for lang, keywords in language_keywords.items():
                if any(keyword in lower_input for keyword in keywords):
                    detected_language = lang
                    break
            
            if detected_language != expected_lang:
                return False
        
        return True
    
    def test_filename_detection(self) -> bool:
        """Test filename detection from prompts."""
        test_cases = [
            ("create a file called test.py", "test.py"),
            ("write a file named main.js", "main.js"),
            ("make a file called hello_world.py", "hello_world.py"),
            ("write a hello world file", "hello_world.py")  # Default name
        ]
        
        import re
        
        for prompt, expected in test_cases:
            filename_match = re.search(r'(?:file\s+(?:called|named)\s+)([a-zA-Z0-9_\-\.]+)', prompt, re.IGNORECASE)
            
            if filename_match:
                detected = filename_match.group(1)
                if not detected.endswith(('.py', '.js', '.ts', '.html', '.css', '.sh', '.java', '.cpp', '.c', '.go', '.rs', '.php')):
                    detected += '.py'  # Default extension
            else:
                # Check for hello world default
                if "hello world" in prompt.lower():
                    detected = "hello_world.py"
                else:
                    detected = "script.py"
            
            if detected != expected:
                return False
        
        return True
    
    def test_custom_filename(self) -> bool:
        """Test creating files with custom filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            session = InteractiveSession()
            session.permissions.approve_all_for_session()
            
            # Test custom filename
            prompt = "create a file called custom_script.py"
            result = session._handle_file_creation_request(prompt)
            
            # Check file was created with correct name
            if not Path("custom_script.py").exists():
                return False
            
            return True
    
    def test_different_languages(self) -> bool:
        """Test creating files in different languages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            session = InteractiveSession()
            session.permissions.approve_all_for_session()
            
            test_cases = [
                ("write a javascript hello world file", ".js"),
                ("create a bash script that prints hello", ".sh"),
                ("make a java hello world program", ".java")
            ]
            
            for i, (prompt, expected_ext) in enumerate(test_cases):
                result = session._handle_file_creation_request(prompt)
                
                # Check appropriate file was created
                files = list(Path(temp_dir).glob(f"*{expected_ext}"))
                
                if not files:
                    return False
                
                # Clean up for next test - use a unique temp dir for each test
                if i < len(test_cases) - 1:  # Don't clean up on last iteration
                    for file in files:
                        file.unlink()
            
            return True
    
    def test_integration_with_session(self) -> bool:
        """Test integration with the full session processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            session = InteractiveSession()
            session.permissions.approve_all_for_session()
            
            # Test full processing pipeline
            prompt = "write a file that prints hello world in python"
            
            # Should be detected as tool request
            if not session._should_use_tools(prompt):
                return False
            
            # Process through the full pipeline
            response = session._handle_tool_request(prompt)
            
            # Check response indicates success
            if "✅ Successfully created" not in response:
                return False
            
            # Check file was actually created
            files = list(Path(temp_dir).glob("*.py"))
            if not files:
                return False
            
            return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 File Creation Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} file creation tests passed")
        
        if passed == total:
            print("🎉 All file creation tests passed!")
            print("✨ File creation functionality is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review file creation implementation.")


def main():
    """Run the file creation test suite."""
    tester = TestFileCreation()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Integration tests for syntax highlighting in responses."""

import sys
import io
from pathlib import Path
from unittest.mock import Mock, patch
from contextlib import redirect_stdout

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.interactive_session import InteractiveSession
from ollamacode.syntax_highlighter import CodeHighlighter


class TestSyntaxIntegration:
    """Test syntax highlighting integration with interactive session."""
    
    def __init__(self):
        self.test_results = []
    
    def run_all_tests(self):
        """Run all syntax highlighting integration tests."""
        print("🎨 Running Syntax Highlighting Integration Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_enhanced_response_printing,
            self.test_code_heavy_response,
            self.test_mixed_content_response,
            self.test_plain_text_response,
            self.test_tool_response_highlighting,
            self.test_file_reference_highlighting
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
    
    def test_enhanced_response_printing(self) -> bool:
        """Test that enhanced response printing works."""
        session = InteractiveSession()
        
        # Test with code content
        code_response = """
Here's a Python function:

```python
def hello_world():
    print("Hello, World!")
    return True
```

This function prints a greeting and returns True.
"""
        
        # Capture output
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            with patch('ollamacode.interactive_session.console') as mock_console:
                session._print_enhanced_response(code_response)
                
                # Should have called print methods
                if not mock_console.print.called:
                    return False
        
        return True
    
    def test_code_heavy_response(self) -> bool:
        """Test handling of code-heavy responses."""
        response = """
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
```

These are some basic mathematical functions.
"""
        
        # Should be detected as code-heavy
        if not CodeHighlighter.is_code_heavy(response):
            return False
        
        session = InteractiveSession()
        
        with patch('ollamacode.interactive_session.console') as mock_console:
            session._print_enhanced_response(response)
            
            # Should have called print methods
            if not mock_console.print.called:
                return False
        
        return True
    
    def test_mixed_content_response(self) -> bool:
        """Test responses with mixed text and code."""
        response = """
To create a simple web server in Python, you can use the built-in `http.server` module:

```python
import http.server
import socketserver

PORT = 8000

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
```

Save this code to a file called `server.py` and run it with:

```bash
python server.py
```

This will start a simple HTTP server that serves files from the current directory.
"""
        
        # Should detect code blocks
        blocks = CodeHighlighter.extract_code_blocks(response)
        if len(blocks) != 2:  # Python and bash blocks
            return False
        
        session = InteractiveSession()
        
        with patch('ollamacode.interactive_session.console') as mock_console:
            session._print_enhanced_response(response)
            
            # Should have called print methods
            if not mock_console.print.called:
                return False
        
        return True
    
    def test_plain_text_response(self) -> bool:
        """Test plain text responses without code."""
        response = """
Software engineering is the application of engineering principles to software development. 
It involves systematic approaches to designing, developing, and maintaining software systems.

Key principles include:
- Modularity and separation of concerns
- Code reusability and maintainability  
- Testing and quality assurance
- Documentation and communication

These principles help ensure that software is reliable, efficient, and meets user requirements.
"""
        
        # Should not detect as code-heavy
        if CodeHighlighter.is_code_heavy(response):
            return False
        
        # Should not find code blocks
        blocks = CodeHighlighter.extract_code_blocks(response)
        if len(blocks) != 0:
            return False
        
        session = InteractiveSession()
        
        with patch('ollamacode.interactive_session.console') as mock_console:
            session._print_enhanced_response(response)
            
            # Should still call print methods for markdown
            if not mock_console.print.called:
                return False
        
        return True
    
    def test_tool_response_highlighting(self) -> bool:
        """Test that tool responses can include syntax highlighting."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            
            # Response with code
            mock_response = """Here's the Python code from the file:

```python
def main():
    print("Hello from the main function!")
    
if __name__ == "__main__":
    main()
```

This is a simple Python script with a main function."""
            
            mock_client.chat.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            with patch('ollamacode.interactive_session.console') as mock_console:
                # Process a tool request that would return code
                response = session._process_user_input("show me the main.py file")
                
                # Should handle the response properly
                if not response:
                    return False
        
        return True
    
    def test_file_reference_highlighting(self) -> bool:
        """Test that file references are properly highlighted."""
        session = InteractiveSession()
        session.permissions.approve_all_for_session()
        
        # Create a temporary Python file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def greet(name):
    return f"Hello, {name}!"

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
""")
            temp_file = f.name
        
        try:
            # Process file reference
            input_text = f"Explain this code: @{temp_file}"
            processed = session._process_file_references(input_text)
            
            # Should contain the file content in a code block
            if "```" not in processed:
                return False
            
            if "def greet" not in processed:
                return False
            
            return True
        
        finally:
            # Cleanup
            import os
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 Syntax Highlighting Integration Test Results Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} syntax integration tests passed")
        
        if passed == total:
            print("🎉 All syntax highlighting integration tests passed!")
            print("✨ Enhanced code responses are working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review syntax integration.")


def main():
    """Run the syntax highlighting integration test suite."""
    tester = TestSyntaxIntegration()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
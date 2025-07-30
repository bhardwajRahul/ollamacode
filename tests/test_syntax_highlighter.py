#!/usr/bin/env python3
"""Tests for the syntax highlighting system."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.syntax_highlighter import CodeHighlighter


class TestSyntaxHighlighter:
    """Test the syntax highlighting functionality."""
    
    def __init__(self):
        self.test_results = []
    
    def run_all_tests(self):
        """Run all syntax highlighting tests."""
        print("🎨 Running Syntax Highlighting Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_language_detection,
            self.test_code_block_extraction,
            self.test_python_detection,
            self.test_javascript_detection,
            self.test_multiple_languages,
            self.test_inline_code_detection,
            self.test_code_heavy_detection,
            self.test_edge_cases
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
    
    def test_language_detection(self) -> bool:
        """Test basic language detection."""
        # Python code
        python_code = """
def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
"""
        
        detected = CodeHighlighter.detect_language(python_code)
        if detected != "python":
            return False
        
        # JavaScript code
        js_code = """
function helloWorld() {
    console.log("Hello, World!");
    return true;
}

const result = helloWorld();
"""
        
        detected = CodeHighlighter.detect_language(js_code)
        if detected != "javascript":
            return False
        
        # SQL code
        sql_code = """
SELECT name, age FROM users 
WHERE age > 18 
ORDER BY name;
"""
        
        detected = CodeHighlighter.detect_language(sql_code)
        if detected != "sql":
            return False
        
        return True
    
    def test_code_block_extraction(self) -> bool:
        """Test extraction of code blocks from text."""
        text = """
Here's a Python function:

```python
def greet(name):
    return f"Hello, {name}!"
```

And here's some inline code: `print("test")`.

Another block without language specification:
```
echo "Hello World"
```
"""
        
        blocks = CodeHighlighter.extract_code_blocks(text)
        
        # Should find 3 code blocks
        if len(blocks) != 3:
            return False
        
        # First block should be Python
        original1, code1, lang1 = blocks[0]
        if lang1 != "python" or "def greet" not in code1:
            return False
        
        # Second block should have auto-detected language (bash)
        original2, code2, lang2 = blocks[1]
        if "echo" not in code2:
            return False
        
        # Third block should be inline code
        original3, code3, lang3 = blocks[2]
        if code3 != 'print("test")':
            return False
        
        return True
    
    def test_python_detection(self) -> bool:
        """Test Python-specific patterns."""
        python_samples = [
            "import numpy as np",
            "def function_name():",
            "class MyClass:",
            "from typing import List",
            "if __name__ == '__main__':",
            "print('hello world')"
        ]
        
        for sample in python_samples:
            if CodeHighlighter.detect_language(sample) != "python":
                return False
        
        return True
    
    def test_javascript_detection(self) -> bool:
        """Test JavaScript-specific patterns."""
        js_samples = [
            "const myVar = 42;",
            "let result = [];",
            "function myFunction() {}",
            "console.log('hello');",
            "const arrow = () => {};",
            "document.getElementById('test');"
        ]
        
        for sample in js_samples:
            detected = CodeHighlighter.detect_language(sample)
            if detected not in ["javascript", "typescript"]:  # TS patterns might match too
                return False
        
        return True
    
    def test_multiple_languages(self) -> bool:
        """Test detection with mixed content."""
        mixed_text = """
Here's some Python:

```python
def hello():
    print("Hello from Python!")
```

And some JavaScript:

```javascript
function hello() {
    console.log("Hello from JavaScript!");
}
```

And some Rust:

```rust
fn hello() {
    println!("Hello from Rust!");
}
```
"""
        
        blocks = CodeHighlighter.extract_code_blocks(mixed_text)
        
        if len(blocks) != 3:
            return False
        
        languages = [lang for _, _, lang in blocks]
        expected = ["python", "javascript", "rust"]
        
        return languages == expected
    
    def test_inline_code_detection(self) -> bool:
        """Test inline code detection and handling."""
        text = "Use `print()` to output text, or `len(list)` to get length."
        
        blocks = CodeHighlighter.extract_code_blocks(text)
        
        if len(blocks) != 2:
            return False
        
        # Inline code should be detected
        codes = [code for _, code, _ in blocks]
        if "print()" not in codes or "len(list)" not in codes:
            return False
        
        return True
    
    def test_code_heavy_detection(self) -> bool:
        """Test detection of code-heavy content."""
        # Text with lots of code
        code_heavy = """
```python
def function1():
    return "test"

def function2():
    return "test2"

def function3():
    return "test3"
```

Just a little text here.

```python
class MyClass:
    def __init__(self):
        self.value = 42
    
    def method(self):
        return self.value * 2
```
"""
        
        if not CodeHighlighter.is_code_heavy(code_heavy):
            return False
        
        # Text with little code
        text_heavy = """
This is a long explanation about programming concepts. We'll discuss 
various topics including algorithms, data structures, and design patterns.

The main idea is to understand how different approaches work and when
to apply them. For example, you might use `sorted()` in Python, but
that's just a small example.

Let's continue with more detailed explanations about computer science
fundamentals and software engineering best practices.
"""
        
        if CodeHighlighter.is_code_heavy(text_heavy):
            return False
        
        return True
    
    def test_edge_cases(self) -> bool:
        """Test edge cases and error handling."""
        # Empty text
        if CodeHighlighter.detect_language("") is not None:
            return False
        
        if CodeHighlighter.extract_code_blocks("") != []:
            return False
        
        # Text with no code
        plain_text = "This is just plain text with no code whatsoever."
        if CodeHighlighter.extract_code_blocks(plain_text) != []:
            return False
        
        # Malformed code blocks
        malformed = "```python\ndef test():\n    return True"  # Missing closing ```
        blocks = CodeHighlighter.extract_code_blocks(malformed)
        if len(blocks) != 0:  # Should not match malformed blocks
            return False
        
        # Very short code
        short_code = "`x`"
        blocks = CodeHighlighter.extract_code_blocks(short_code)
        if len(blocks) != 1:
            return False
        
        return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Syntax Highlighting Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} syntax highlighting tests passed")
        
        if passed == total:
            print("🎉 All syntax highlighting tests passed! Code highlighting is working correctly.")
            print("\n🎨 Supported languages:")
            languages = CodeHighlighter.get_supported_languages()
            for i, lang in enumerate(languages):
                if i % 6 == 0:
                    print()
                print(f"{lang:12}", end="")
            print()
        else:
            print(f"⚠️  {total - passed} tests failed. Review syntax highlighting implementation.")


def main():
    """Run the syntax highlighting test suite."""
    tester = TestSyntaxHighlighter()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
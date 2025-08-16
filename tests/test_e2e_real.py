#!/usr/bin/env python3
"""
Real End-to-End Integration Tests for OllamaCode

These tests actually execute `ollamacode` as a subprocess and verify the results.
They test the complete user workflow from command input to file system changes.
"""

import subprocess
import tempfile
import os
import time
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
import pytest


class OllamaCodeE2ETest:
    """Base class for end-to-end OllamaCode testing."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ollamacode_e2e_"))
        self.original_cwd = Path.cwd()
        self.test_results = []
        self.ollama_available = self._check_ollama_available()
        
    def setup(self):
        """Setup test environment."""
        os.chdir(self.temp_dir)
        print(f"🔧 Test environment: {self.temp_dir}")
        
    def teardown(self):
        """Cleanup test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def _check_ollama_available(self) -> bool:
        """Check if Ollama service is running."""
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/version"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def run_ollamacode_command(self, prompt: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Run ollamacode with a prompt and capture all output.
        
        Returns:
            Dict containing stdout, stderr, returncode, execution_time, and files_created
        """
        start_time = time.time()
        files_before = set(self.temp_dir.rglob("*"))
        
        try:
            # Run ollamacode in headless mode
            result = subprocess.run(
                ["ollamacode", "-p", prompt],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            files_after = set(self.temp_dir.rglob("*"))
            files_created = files_after - files_before
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr, 
                "returncode": result.returncode,
                "execution_time": execution_time,
                "files_created": [str(f.relative_to(self.temp_dir)) for f in files_created if f.is_file()],
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": 124,  # timeout exit code
                "execution_time": timeout,
                "files_created": [],
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": 1,
                "execution_time": 0,
                "files_created": [],
                "success": False
            }


class TestFileOperationChaining(OllamaCodeE2ETest):
    """Test file operation chaining - the core functionality."""
    
    def test_write_and_run_python_script(self):
        """Test: Create a Python script and run it."""
        if not self.ollama_available:
            pytest.skip("Ollama service not available")
            
        self.setup()
        
        prompt = "Create a Python script called hello.py that prints 'Hello from OllamaCode!' and then run it"
        result = self.run_ollamacode_command(prompt)
        
        # Verify the command succeeded  
        assert result["success"], f"Command failed: {result['stderr']}"
        
        # Verify the file was created
        hello_file = self.temp_dir / "hello.py"
        assert hello_file.exists(), "hello.py file was not created"
        
        # Verify the content is reasonable
        content = hello_file.read_text()
        assert "Hello from OllamaCode" in content or "print" in content, f"Unexpected file content: {content}"
        
        # Verify the script was actually run (check output)
        assert "Hello from OllamaCode" in result["stdout"] or "Hello" in result["stdout"], \
            f"Script output not found in stdout: {result['stdout']}"
        
        self.teardown()
        return True
        
    def test_calculator_creation_and_execution(self):
        """Test: Create a calculator script and test it.""" 
        if not self.ollama_available:
            pytest.skip("Ollama service not available")
            
        self.setup()
        
        prompt = """Create a Python calculator script called calc.py with functions for add, subtract, multiply, divide. 
        Then create a test script test_calc.py that imports calc and tests 2+3=5. Run the test."""
        
        result = self.run_ollamacode_command(prompt, timeout=90)
        
        # Verify both files were created
        calc_file = self.temp_dir / "calc.py"
        test_file = self.temp_dir / "test_calc.py" 
        
        assert calc_file.exists(), "calc.py was not created"
        assert test_file.exists(), "test_calc.py was not created"
        
        # Verify calc.py has calculator functions
        calc_content = calc_file.read_text()
        assert any(word in calc_content.lower() for word in ["def add", "def subtract", "def multiply", "def divide"]), \
            f"Calculator functions not found in calc.py: {calc_content}"
        
        # Verify test was run and passed  
        assert result["success"] or "5" in result["stdout"], \
            f"Calculator test did not run successfully: {result['stdout']}, {result['stderr']}"
        
        self.teardown()
        return True


class TestGitWorkflow(OllamaCodeE2ETest):
    """Test Git operation workflows."""
    
    def test_git_initialization_and_commit(self):
        """Test: Initialize git repo, create file, and commit."""
        if not self.ollama_available:
            pytest.skip("Ollama service not available")
            
        self.setup()
        
        prompt = """Initialize a git repository, create a README.md file with project description, 
        stage it, and make the first commit with message 'Initial commit'"""
        
        result = self.run_ollamacode_command(prompt, timeout=60)
        
        # Verify git repo was initialized
        assert (self.temp_dir / ".git").exists(), "Git repository not initialized"
        
        # Verify README was created
        readme_file = self.temp_dir / "README.md"
        assert readme_file.exists(), "README.md not created"
        
        # Verify content is reasonable
        content = readme_file.read_text()
        assert len(content.strip()) > 10, "README content too short"
        
        # Verify commit was made
        git_result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True
        )
        
        assert git_result.returncode == 0, "Git log failed"
        assert "Initial commit" in git_result.stdout or len(git_result.stdout.strip()) > 0, \
            f"No commits found: {git_result.stdout}"
        
        self.teardown()
        return True


class TestComplexChaining(OllamaCodeE2ETest):
    """Test complex multi-step workflows."""
    
    def test_web_scraper_creation(self):
        """Test: Create a web scraper, requirements file, and run it."""
        if not self.ollama_available:
            pytest.skip("Ollama service not available")
            
        self.setup()
        
        prompt = """Create a simple web scraper script called scraper.py that uses requests to fetch 
        httpbin.org/json and prints the JSON response. Also create a requirements.txt file with 
        the dependencies. Then try to install the dependencies and run the script."""
        
        result = self.run_ollamacode_command(prompt, timeout=120)
        
        # Verify files were created
        scraper_file = self.temp_dir / "scraper.py"
        requirements_file = self.temp_dir / "requirements.txt"
        
        assert scraper_file.exists(), "scraper.py not created"
        assert requirements_file.exists(), "requirements.txt not created"
        
        # Verify scraper has reasonable content
        scraper_content = scraper_file.read_text()
        assert "requests" in scraper_content and "httpbin" in scraper_content, \
            f"Scraper content invalid: {scraper_content}"
        
        # Verify requirements has requests
        req_content = requirements_file.read_text()
        assert "requests" in req_content, f"Requirements missing requests: {req_content}"
        
        self.teardown()
        return True


def run_comprehensive_e2e_tests():
    """Run all end-to-end tests with detailed reporting."""
    
    print("🚀 Running Comprehensive End-to-End OllamaCode Tests")
    print("=" * 60)
    
    test_classes = [TestFileOperationChaining, TestGitWorkflow, TestComplexChaining]
    all_results = {}
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)
        
        test_instance = test_class()
        class_results = {}
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) if method.startswith("test_")]
        
        for method_name in test_methods:
            print(f"  🔍 Running {method_name}...")
            
            start_time = time.time()
            try:
                method = getattr(test_instance, method_name)
                result = method()
                execution_time = time.time() - start_time
                
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"    {status} ({execution_time:.2f}s)")
                
                class_results[method_name] = {
                    "status": "PASS" if result else "FAIL",
                    "execution_time": execution_time,
                    "error": None
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"    ❌ ERROR ({execution_time:.2f}s): {str(e)}")
                
                class_results[method_name] = {
                    "status": "ERROR", 
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        all_results[test_class.__name__] = class_results
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    error_tests = 0
    
    for class_name, class_results in all_results.items():
        print(f"\n{class_name}:")
        for method_name, result in class_results.items():
            total_tests += 1
            status_symbol = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[result["status"]]
            
            if result["status"] == "PASS":
                passed_tests += 1
            elif result["status"] == "FAIL": 
                failed_tests += 1
            else:
                error_tests += 1
                
            print(f"  {status_symbol} {method_name} ({result['execution_time']:.2f}s)")
            if result["error"]:
                print(f"      Error: {result['error']}")
    
    print(f"\n📈 FINAL RESULTS:")
    print(f"  Total Tests: {total_tests}")
    print(f"  ✅ Passed: {passed_tests}")
    print(f"  ❌ Failed: {failed_tests}")
    print(f"  💥 Errors: {error_tests}")
    print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Save detailed report to file
    report_file = Path("e2e_test_report.json")
    with open(report_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "results": all_results,
            "summary": {
                "total": total_tests,
                "passed": passed_tests, 
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": (passed_tests/total_tests)*100 if total_tests > 0 else 0
            }
        }, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")
    return all_results


if __name__ == "__main__":
    # Allow running this file directly for testing
    run_comprehensive_e2e_tests()
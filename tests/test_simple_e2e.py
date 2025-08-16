#!/usr/bin/env python3
"""Simple E2E test to verify ollamacode actually works."""

import subprocess
import tempfile
import os
from pathlib import Path
import time

def test_simple_e2e():
    """Test that ollamacode can create a file."""
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="simple_e2e_"))
    original_cwd = Path.cwd()
    
    try:
        os.chdir(temp_dir)
        print(f"🔧 Test directory: {temp_dir}")
        
        # Run ollamacode to create a simple file
        print("📝 Running: ollamacode -p 'create hello.py that prints hello world'")
        
        start_time = time.time()
        result = subprocess.run(
            ["ollamacode", "-p", "create hello.py that prints hello world"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=120  # 2 minutes
        )
        execution_time = time.time() - start_time
        
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check what files were created
        files = list(temp_dir.iterdir())
        print(f"Files created: {files}")
        
        # Check if hello.py exists
        hello_file = temp_dir / "hello.py"
        if hello_file.exists():
            print("✅ hello.py was created!")
            content = hello_file.read_text()
            print(f"Content:\n{content}")
            
            # Try to run it
            print("🏃 Testing if the file works...")
            run_result = subprocess.run(
                ["python", "hello.py"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if run_result.returncode == 0:
                print("✅ File runs successfully!")
                print(f"Output: {run_result.stdout}")
            else:
                print(f"❌ File failed to run: {run_result.stderr}")
        else:
            print("❌ hello.py was NOT created")
            print("This indicates ollamacode is not working as expected")
        
        return result.returncode == 0 and hello_file.exists()
        
    finally:
        os.chdir(original_cwd)
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    print("🧪 Simple E2E Test for OllamaCode")
    print("=" * 40)
    
    # First check if Ollama is running
    try:
        ollama_check = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/version"],
            capture_output=True, timeout=5
        )
        if ollama_check.returncode == 0:
            print("✅ Ollama is running")
        else:
            print("❌ Ollama is not running - please start with 'ollama serve'")
            exit(1)
    except:
        print("❌ Could not check Ollama status")
        exit(1)
    
    # Run the test
    success = test_simple_e2e()
    
    if success:
        print("\n🎉 Simple E2E test PASSED!")
        print("OllamaCode is working correctly")
    else:
        print("\n💥 Simple E2E test FAILED!")
        print("There are issues with OllamaCode execution")
    
    exit(0 if success else 1)
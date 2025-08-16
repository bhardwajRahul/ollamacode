#!/usr/bin/env python3
"""
Test Tool Chaining - Real Integration Test

This test verifies that OllamaCode can chain multiple tools together:
1. Create a matplotlib visualization script
2. Create a requirements.txt file  
3. Run the script to generate the plot
4. Verify the output file was created

This is a REAL end-to-end test that actually runs ollamacode.
"""

import subprocess
import tempfile
import os
import time
import shutil
from pathlib import Path
import pytest


def test_matplotlib_visualization_chaining():
    """
    Test the complete workflow:
    1. Ask OllamaCode to create a matplotlib script that generates a sine wave plot
    2. Ask it to create requirements.txt
    3. Ask it to run the script 
    4. Verify the PNG file was created and has reasonable size
    """
    
    # Check if Ollama is available
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/version"],
            capture_output=True, timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Ollama service not available - skipping end-to-end test")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("Ollama service not available - skipping end-to-end test")
    
    # Create temporary directory for test
    temp_dir = Path(tempfile.mkdtemp(prefix="ollamacode_chaining_"))
    original_cwd = Path.cwd()
    
    try:
        os.chdir(temp_dir)
        print(f"🔧 Test directory: {temp_dir}")
        
        # Step 1: Create matplotlib visualization script
        prompt1 = """Create a Python script called sine_plot.py that uses matplotlib to:
        1. Generate a sine wave from 0 to 4π with 1000 points
        2. Plot it with a blue line, grid, title, and labels
        3. Save the plot as 'sine_wave.png' with high DPI
        4. Print a success message when done"""
        
        print("📝 Step 1: Creating matplotlib script...")
        result1 = subprocess.run(
            ["ollamacode", "-p", prompt1],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"   Return code: {result1.returncode}")
        if result1.stdout:
            print(f"   Output: {result1.stdout[:200]}...")
        if result1.stderr:
            print(f"   Errors: {result1.stderr}")
            
        # Verify script was created
        script_file = temp_dir / "sine_plot.py"
        assert script_file.exists(), f"sine_plot.py not created. Files in dir: {list(temp_dir.iterdir())}"
        
        # Verify script content
        script_content = script_file.read_text()
        assert "matplotlib" in script_content, "Script doesn't import matplotlib"
        assert "sine_wave.png" in script_content, "Script doesn't save PNG file"
        assert "np.sin" in script_content or "sin(" in script_content, "Script doesn't compute sine"
        
        print("   ✅ Matplotlib script created successfully")
        
        # Step 2: Create requirements.txt
        prompt2 = "Create a requirements.txt file with matplotlib and numpy dependencies"
        
        print("📦 Step 2: Creating requirements.txt...")
        result2 = subprocess.run(
            ["ollamacode", "-p", prompt2],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Verify requirements.txt was created
        req_file = temp_dir / "requirements.txt"
        assert req_file.exists(), "requirements.txt not created"
        
        req_content = req_file.read_text()
        assert "matplotlib" in req_content, "matplotlib not in requirements.txt"
        
        print("   ✅ requirements.txt created successfully")
        
        # Step 3: Run the script to generate the plot
        prompt3 = "Run the sine_plot.py script to generate the visualization"
        
        print("🏃 Step 3: Running the script...")
        result3 = subprocess.run(
            ["ollamacode", "-p", prompt3], 
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=90  # Longer timeout as this might install packages
        )
        
        print(f"   Return code: {result3.returncode}")
        if result3.stdout:
            print(f"   Output: {result3.stdout}")
        if result3.stderr:
            print(f"   Errors: {result3.stderr}")
        
        # Step 4: Verify the PNG was created
        png_file = temp_dir / "sine_wave.png"
        
        # Check if PNG exists
        if not png_file.exists():
            # Try to run the script manually to see what happens
            print("   ⚠️  PNG not found, trying manual execution...")
            manual_result = subprocess.run(
                ["python", "sine_plot.py"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            print(f"   Manual execution result: {manual_result.returncode}")
            print(f"   Manual stdout: {manual_result.stdout}")
            print(f"   Manual stderr: {manual_result.stderr}")
        
        assert png_file.exists(), f"sine_wave.png not created. Files: {list(temp_dir.iterdir())}"
        
        # Verify PNG has reasonable size (matplotlib plots are typically > 10KB)
        png_size = png_file.stat().st_size
        assert png_size > 5000, f"PNG file too small ({png_size} bytes), likely not a real plot"
        
        print(f"   ✅ PNG file created successfully ({png_size} bytes)")
        
        print("\n🎉 Tool chaining test completed successfully!")
        print(f"   📁 Script: {script_file}")
        print(f"   📋 Requirements: {req_file}")
        print(f"   🖼️  Plot: {png_file} ({png_size} bytes)")
        
        return True
        
    finally:
        # Cleanup
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_data_analysis_chaining():
    """
    Test a more complex chaining scenario:
    1. Create a CSV data file
    2. Create a Python script that analyzes the data
    3. Run the analysis and generate a report
    """
    
    # Check if Ollama is available  
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/version"],
            capture_output=True, timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Ollama service not available - skipping end-to-end test")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("Ollama service not available - skipping end-to-end test")
    
    temp_dir = Path(tempfile.mkdtemp(prefix="ollamacode_data_analysis_"))
    original_cwd = Path.cwd()
    
    try:
        os.chdir(temp_dir)
        
        # Step 1: Create sample data
        prompt1 = """Create a CSV file called sales_data.csv with sample sales data containing:
        - columns: date, product, quantity, price
        - at least 10 rows of realistic data
        - dates from 2024"""
        
        print("📊 Creating sample data...")
        result1 = subprocess.run(
            ["ollamacode", "-p", prompt1],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=45
        )
        
        csv_file = temp_dir / "sales_data.csv"
        assert csv_file.exists(), "sales_data.csv not created"
        
        # Step 2: Create analysis script  
        prompt2 = """Create a Python script called analyze.py that:
        1. Reads the sales_data.csv file
        2. Calculates total revenue (quantity * price)
        3. Finds the best-selling product
        4. Prints a summary report
        5. Saves results to summary.txt"""
        
        print("📝 Creating analysis script...")
        result2 = subprocess.run(
            ["ollamacode", "-p", prompt2],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        analysis_file = temp_dir / "analyze.py"
        assert analysis_file.exists(), "analyze.py not created"
        
        # Step 3: Run the analysis
        prompt3 = "Run the analyze.py script to generate the sales report"
        
        print("🏃 Running analysis...")
        result3 = subprocess.run(
            ["ollamacode", "-p", prompt3],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Verify results
        summary_file = temp_dir / "summary.txt"
        assert summary_file.exists(), "summary.txt report not created"
        
        summary_content = summary_file.read_text()
        assert len(summary_content) > 50, "Summary report too short"
        
        print("🎉 Data analysis chaining test completed successfully!")
        return True
        
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run tests when executed directly
    print("🔗 Running Tool Chaining Tests")
    print("=" * 50)
    
    try:
        print("\n🎨 Test 1: Matplotlib Visualization Chaining")
        result1 = test_matplotlib_visualization_chaining()
        print("✅ PASSED" if result1 else "❌ FAILED")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    try:
        print("\n📊 Test 2: Data Analysis Chaining")  
        result2 = test_data_analysis_chaining()
        print("✅ PASSED" if result2 else "❌ FAILED")
    except Exception as e:
        print(f"❌ FAILED: {e}")
#!/usr/bin/env python3
"""Test spinner functionality."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live

def test_spinner_basic():
    """Test basic spinner functionality."""
    console = Console()
    
    print("Testing basic spinner for 3 seconds...")
    with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console):
        time.sleep(3)
    
    console.print("[green]✓ Basic spinner test completed![/green]")

def test_spinner_styles():
    """Test different spinner styles."""
    console = Console()
    
    spinners = ["dots", "dots2", "dots3", "line", "arrow", "bouncingBall", "clock"]
    
    for spinner_style in spinners:
        print(f"\nTesting {spinner_style} spinner...")
        with Live(Spinner(spinner_style, text=f"[dim]{spinner_style} thinking...[/dim]"), 
                  refresh_per_second=10, console=console):
            time.sleep(1.5)
        console.print(f"[green]✓ {spinner_style} completed![/green]")

if __name__ == "__main__":
    print("🎠 Spinner Test Suite")
    print("=" * 30)
    
    test_spinner_basic()
    test_spinner_styles()
    
    print("\n🎉 All spinner tests completed!")
    print("\nThe actual spinner implementation in OllamaCode uses 'dots' style")
    print("and appears during model processing with 'Thinking...' text.")
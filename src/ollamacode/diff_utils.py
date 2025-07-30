"""Diff utilities for previewing file changes."""

import difflib
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


class DiffPreview:
    """Generate and display diff previews for file changes."""
    
    @staticmethod
    def generate_diff(original: str, modified: str, filename: str = "file") -> str:
        """Generate a unified diff between original and modified content."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines, 
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        
        return "".join(diff)
    
    @staticmethod
    def show_diff_preview(original: str, modified: str, filename: str = "file") -> bool:
        """Show diff preview and ask for confirmation."""
        diff_text = DiffPreview.generate_diff(original, modified, filename)
        
        if not diff_text.strip():
            console.print("[yellow]No changes detected.[/yellow]")
            return True
        
        # Display the diff with syntax highlighting
        console.print(f"\n[bold blue]Preview of changes to {filename}:[/bold blue]")
        
        try:
            # Try to display with diff syntax highlighting
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="Diff Preview", border_style="blue"))
        except Exception:
            # Fallback to plain text
            console.print(Panel(diff_text, title="Diff Preview", border_style="blue"))
        
        # Ask for confirmation
        try:
            response = console.input("\n[bold]Apply these changes? (y/N): [/bold]").strip().lower()
            return response in ['y', 'yes']
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Changes cancelled.[/yellow]")
            return False
    
    @staticmethod
    def show_side_by_side(original: str, modified: str, filename: str = "file", context: int = 3):
        """Show side-by-side comparison of changes."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Generate side-by-side diff
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="Original",
            tofile="Modified", 
            lineterm="",
            n=context
        )
        
        console.print(f"\n[bold blue]Side-by-side comparison for {filename}:[/bold blue]")
        
        # Simple side-by-side display
        max_lines = max(len(original_lines), len(modified_lines))
        
        for i in range(min(max_lines, 20)):  # Limit to first 20 lines for readability
            orig_line = original_lines[i] if i < len(original_lines) else ""
            mod_line = modified_lines[i] if i < len(modified_lines) else ""
            
            if orig_line != mod_line:
                console.print(f"[red]- {orig_line}[/red]")
                console.print(f"[green]+ {mod_line}[/green]")
            else:
                console.print(f"  {orig_line}")
        
        if max_lines > 20:
            console.print(f"[dim]... {max_lines - 20} more lines ...[/dim]")
    
    @staticmethod
    def get_change_summary(original: str, modified: str) -> str:
        """Get a summary of changes between original and modified content."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Calculate basic stats
        orig_len = len(original_lines)
        mod_len = len(modified_lines)
        
        # Count actual changes
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
        changes = 0
        additions = 0
        deletions = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                changes += max(i2 - i1, j2 - j1)
            elif tag == 'insert':
                additions += j2 - j1
            elif tag == 'delete':
                deletions += i2 - i1
        
        summary_parts = []
        
        if additions:
            summary_parts.append(f"[green]+{additions} lines[/green]")
        if deletions:
            summary_parts.append(f"[red]-{deletions} lines[/red]")
        if changes:
            summary_parts.append(f"[yellow]~{changes} modified[/yellow]")
        
        if not summary_parts:
            return "[dim]No changes[/dim]"
        
        return f"Changes: {', '.join(summary_parts)} (total: {orig_len} → {mod_len} lines)"
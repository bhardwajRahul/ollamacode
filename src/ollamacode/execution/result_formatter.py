"""Clean output formatting for Phase 5."""

from typing import Any, Dict, Optional
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text

console = Console()


class OutputFormatter:
    """Clean, consistent output formatting without verbose boxes."""
    
    @staticmethod
    def format_command_result(command: str, output: str, error: str = None) -> str:
        """Format command execution result cleanly."""
        if error:
            return f"$ {command}\n❌ Error: {error}"
        
        if not output.strip():
            return f"$ {command}\n(no output)"
        
        return f"$ {command}\n{output.rstrip()}"
    
    @staticmethod
    def format_file_content(filename: str, content: str, max_lines: int = 50) -> str:
        """Format file content with syntax highlighting."""
        language = OutputFormatter._detect_language(filename)
        
        # Truncate if too long
        lines = content.split('\n')
        if len(lines) > max_lines:
            content = '\n'.join(lines[:max_lines]) + f'\n... ({len(lines) - max_lines} more lines)'
        
        try:
            syntax = Syntax(content, language, theme="monokai", line_numbers=True)
            return f"📄 {filename}:\n" + console.render_str(syntax)
        except Exception:
            return f"📄 {filename}:\n{content}"
    
    @staticmethod
    def format_git_status(status: Dict[str, Any]) -> str:
        """Format git status cleanly."""
        lines = [f"📂 Repository: {status.get('branch', 'unknown')}"]
        
        if status.get('is_dirty', False):
            if status.get('modified'):
                lines.append(f"📝 Modified: {', '.join(status['modified'])}")
            if status.get('staged'):
                lines.append(f"✅ Staged: {', '.join(status['staged'])}")
            if status.get('untracked'):
                untracked = status['untracked'][:5]  # Limit to 5
                more = f" (+{len(status['untracked']) - 5} more)" if len(status['untracked']) > 5 else ""
                lines.append(f"❓ Untracked: {', '.join(untracked)}{more}")
        else:
            lines.append("✨ Working tree clean")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_search_results(pattern: str, results: list, max_results: int = 10) -> str:
        """Format search results cleanly."""
        if not results:
            return f"🔍 No matches found for '{pattern}'"
        
        lines = [f"🔍 Found {len(results)} matches for '{pattern}':"]
        
        for i, result in enumerate(results[:max_results]):
            if isinstance(result, dict):
                file_path = result.get('file', 'unknown')
                line_num = result.get('line', '?')
                content = result.get('content', '').strip()[:80]
                lines.append(f"  {file_path}:{line_num} - {content}")
            else:
                lines.append(f"  {result}")
        
        if len(results) > max_results:
            lines.append(f"  ... and {len(results) - max_results} more matches")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_error(operation: str, error: str, suggestions: list = None) -> str:
        """Format error messages with helpful suggestions."""
        lines = [f"❌ {operation.capitalize()} failed: {error}"]
        
        if suggestions:
            lines.append("\n💡 Suggestions:")
            for suggestion in suggestions:
                lines.append(f"  • {suggestion}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_file_created(filename: str, content: str, language: str = None) -> str:
        """Format file creation result."""
        lang_display = f" ({language})" if language else ""
        header = f"✅ Created {filename}{lang_display}"
        
        # Show first few lines of content
        lines = content.split('\n')
        if len(lines) > 10:
            preview = '\n'.join(lines[:10]) + f'\n... ({len(lines) - 10} more lines)'
        else:
            preview = content
        
        try:
            detected_lang = language or OutputFormatter._detect_language(filename)
            syntax = Syntax(preview, detected_lang, theme="monokai", line_numbers=True)
            return header + "\n\n" + console.render_str(syntax)
        except Exception:
            return f"{header}\n\n{preview}"
    
    @staticmethod
    def _detect_language(filename: str) -> str:
        """Detect programming language from filename."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.sql': 'sql',
            '.xml': 'xml',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin'
        }
        
        for ext, lang in ext_map.items():
            if filename.lower().endswith(ext):
                return lang
        
        return 'text'
    
    @staticmethod
    def format_simple_response(message: str) -> str:
        """Format simple text responses without extra formatting."""
        return message.strip()
    
    @staticmethod
    def format_list(items: list, title: str = None) -> str:
        """Format a simple list of items."""
        if not items:
            return f"{title}: (none)" if title else "(none)"
        
        lines = [title + ":"] if title else []
        for item in items:
            lines.append(f"  • {item}")
        
        return '\n'.join(lines)
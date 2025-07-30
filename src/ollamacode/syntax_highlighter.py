"""Syntax highlighting for code in responses."""

import re
from typing import Optional, Dict, List, Tuple
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


class CodeHighlighter:
    """Enhanced code highlighting for AI responses."""
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'python': [
            r'\bdef\s+\w+\s*\(',
            r'\bclass\s+\w+',
            r'\bimport\s+\w+',
            r'\bfrom\s+\w+\s+import',
            r'print\s*\(',
            r'if\s+__name__\s*==\s*["\']__main__["\']',
            r'#.*python',
            r'\.py\b'
        ],
        'javascript': [
            r'\bfunction\s+\w+\s*\(',
            r'\bconst\s+\w+\s*=',
            r'\blet\s+\w+\s*=',
            r'\bvar\s+\w+\s*=',
            r'console\.log\s*\(',
            r'=>\s*{',
            r'document\.',
            r'\.js\b',
            r'\bawait\s+',
            r'\basync\s+'
        ],
        'typescript': [
            r':\s*\w+\s*=',
            r'\binterface\s+\w+',
            r'\btype\s+\w+\s*=',
            r'<\w+>',
            r'\.ts\b',
            r'\.tsx\b'
        ],
        'rust': [
            r'\bfn\s+\w+\s*\(',
            r'\blet\s+mut\s+',
            r'\bstruct\s+\w+',
            r'\benum\s+\w+',
            r'\bimpl\s+',
            r'println!\s*\(',
            r'\.rs\b',
            r'\buse\s+\w+'
        ],
        'go': [
            r'\bfunc\s+\w+\s*\(',
            r'\bpackage\s+\w+',
            r'\bvar\s+\w+\s+\w+',
            r'\btype\s+\w+\s+struct',
            r'fmt\.Println',
            r'\.go\b'
        ],
        'java': [
            r'\bpublic\s+class\s+\w+',
            r'\bpublic\s+static\s+void\s+main',
            r'\bSystem\.out\.println',
            r'\bimport\s+java\.',
            r'\.java\b'
        ],
        'c': [
            r'#include\s*<\w+\.h>',
            r'\bint\s+main\s*\(',
            r'\bprintf\s*\(',
            r'\bstruct\s+\w+',
            r'\.c\b'
        ],
        'cpp': [
            r'#include\s*<\w+>',
            r'\bstd::',
            r'\busing\s+namespace\s+std',
            r'cout\s*<<',
            r'\.cpp\b',
            r'\.hpp\b'
        ],
        'bash': [
            r'#!/bin/bash',
            r'#!/bin/sh',
            r'\becho\s+',
            r'\bif\s*\[\s*',
            r'\bfor\s+\w+\s+in',
            r'\.sh\b',
            r'\$\w+',
            r'\$\{[^}]+\}'
        ],
        'sql': [
            r'\bSELECT\s+',
            r'\bFROM\s+\w+',
            r'\bWHERE\s+',
            r'\bINSERT\s+INTO',
            r'\bUPDATE\s+\w+\s+SET',
            r'\bCREATE\s+TABLE',
            r'\.sql\b'
        ],
        'json': [
            r'^\s*{',
            r'"\w+"\s*:',
            r'\.json\b'
        ],
        'yaml': [
            r'^\s*\w+\s*:',
            r'^\s*-\s+\w+',
            r'\.ya?ml\b'
        ],
        'html': [
            r'<html',
            r'<head>',
            r'<body>',
            r'<div',
            r'\.html?\b'
        ],
        'css': [
            r'\.\w+\s*{',
            r'#\w+\s*{',
            r'\w+\s*:\s*[^;]+;',
            r'\.css\b'
        ]
    }
    
    @classmethod
    def detect_language(cls, code: str) -> Optional[str]:
        """Detect programming language from code content."""
        code_lower = code.lower()
        scores = {}
        
        for lang, patterns in cls.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code, re.IGNORECASE | re.MULTILINE))
                score += matches
            
            if score > 0:
                scores[lang] = score
        
        if not scores:
            return None
        
        # Return language with highest score
        return max(scores, key=scores.get)
    
    @classmethod
    def extract_code_blocks(cls, text: str) -> List[Tuple[str, str, Optional[str]]]:
        """Extract code blocks from text.
        
        Returns list of (original_block, code_content, language) tuples.
        """
        code_blocks = []
        
        # Match fenced code blocks with language specification
        fenced_pattern = r'```(\w+)?\n(.*?)\n```'
        for match in re.finditer(fenced_pattern, text, re.DOTALL):
            lang = match.group(1)
            code = match.group(2)
            original = match.group(0)
            
            # Auto-detect language if not specified
            if not lang:
                lang = cls.detect_language(code)
            
            code_blocks.append((original, code, lang))
        
        # Match inline code blocks (single backticks)
        inline_pattern = r'`([^`\n]+)`'
        for match in re.finditer(inline_pattern, text):
            code = match.group(1)
            original = match.group(0)
            
            # Only auto-detect for longer inline code
            lang = None
            if len(code) > 20:
                lang = cls.detect_language(code)
            
            code_blocks.append((original, code, lang))
        
        return code_blocks
    
    @classmethod
    def highlight_response(cls, text: str, theme: str = "monokai") -> str:
        """Highlight code blocks in AI response text."""
        if not text:
            return text
        
        code_blocks = cls.extract_code_blocks(text)
        
        if not code_blocks:
            return text
        
        # Replace code blocks with highlighted versions
        highlighted_text = text
        
        for original, code, language in code_blocks:
            if language and len(code.strip()) > 5:  # Only highlight substantial code
                try:
                    # Create syntax-highlighted version
                    syntax = Syntax(code, language, theme=theme, line_numbers=False, word_wrap=True)
                    
                    # For now, we'll keep the original formatting but could enhance this
                    # The Rich console will handle the actual highlighting when printed
                    highlighted_text = highlighted_text.replace(original, original)
                    
                except Exception:
                    # If highlighting fails, keep original
                    pass
        
        return highlighted_text
    
    @classmethod
    def render_code_block(cls, code: str, language: Optional[str] = None, 
                         theme: str = "monokai", show_line_numbers: bool = False,
                         title: Optional[str] = None) -> Panel:
        """Render a single code block with syntax highlighting."""
        if not language:
            language = cls.detect_language(code) or "text"
        
        try:
            syntax = Syntax(
                code,
                language, 
                theme=theme,
                line_numbers=show_line_numbers,
                word_wrap=True,
                indent_guides=True
            )
            
            title_text = title or f"{language.title()} Code"
            
            return Panel(
                syntax,
                title=title_text,
                border_style="blue",
                expand=False
            )
        
        except Exception:
            # Fallback to plain text
            return Panel(
                code,
                title=title or "Code",
                border_style="dim",
                expand=False
            )
    
    @classmethod
    def print_highlighted_response(cls, text: str, theme: str = "monokai"):
        """Print AI response with syntax-highlighted code blocks."""
        if not text:
            return
        
        # Split text by code blocks
        code_blocks = cls.extract_code_blocks(text)
        
        if not code_blocks:
            # No code blocks, print as markdown
            try:
                console.print(Markdown(text))
            except Exception:
                console.print(text)
            return
        
        # Process text with code blocks
        current_pos = 0
        
        for original, code, language in code_blocks:
            # Find the position of this code block
            block_pos = text.find(original, current_pos)
            
            if block_pos > current_pos:
                # Print text before this code block
                before_text = text[current_pos:block_pos]
                if before_text.strip():
                    try:
                        console.print(Markdown(before_text))
                    except Exception:
                        console.print(before_text)
            
            # Print the highlighted code block
            if language and len(code.strip()) > 5:
                # Substantial code - highlight it
                highlighted_panel = cls.render_code_block(
                    code, language, theme, show_line_numbers=len(code.split('\n')) > 10
                )
                console.print(highlighted_panel)
            else:
                # Short code or no language - simple format
                console.print(f"[dim]`{code}`[/dim]")
            
            current_pos = block_pos + len(original)
        
        # Print any remaining text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text.strip():
                try:
                    console.print(Markdown(remaining_text))
                except Exception:
                    console.print(remaining_text)
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Get list of supported languages for syntax highlighting."""
        return sorted(cls.LANGUAGE_PATTERNS.keys())
    
    @classmethod
    def is_code_heavy(cls, text: str) -> bool:
        """Determine if text contains significant amounts of code."""
        code_blocks = cls.extract_code_blocks(text)
        
        if not code_blocks:
            return False
        
        total_code_chars = sum(len(code) for _, code, _ in code_blocks)
        total_chars = len(text)
        
        # Consider "code heavy" if more than 30% is code
        return total_code_chars / total_chars > 0.3 if total_chars > 0 else False
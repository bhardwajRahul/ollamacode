"""Intent-based tool detection for reliable execution."""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


class ToolType(Enum):
    """Types of tools available."""
    FILE_OP = "file_operation"
    GIT_OP = "git_operation" 
    SEARCH_OP = "search_operation"
    BASH_OP = "bash_operation"
    NONE = "none"


@dataclass
class ToolIntent:
    """Represents a detected tool intent."""
    type: ToolType
    action: str
    target: str
    confidence: float
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class IntentAnalyzer:
    """Analyze user input to determine tool intentions."""
    
    # Pattern definitions for different tool types
    FILE_PATTERNS = {
        'create': [
            r'(?:write|create|make|generate)\s+(?:a\s+)?(?:file|script|program)',
            r'write\s+(?:a\s+)?(?:script|program|file)',
            r'create\s+(?:a\s+)?(?:script|program|file)',
            r'save\s+(?:to\s+)?file',
            r'make\s+(?:a\s+)?script',
            r'generate\s+(?:a\s+)?\w+\s+file',
            r'create\s+(?:a\s+)?\w+\s+(?:script|file|program)'
        ],
        'read': [
            r'(?:read|show|open|display|view)\s+(?:the\s+)?(?:file|@?\w+\.\w+)',
            r'content\s+of\s+\w+\.\w+',
            r'show\s+me\s+(?:@?\w+\.\w+|(?:the\s+)?(?:file|code))',
            r'what\'?s\s+in\s+\w+\.\w+',
            r'@\w+\.\w+'  # File references like @main.py
        ],
        'edit': [
            r'(?:edit|modify|change|update)\s+(?:the\s+)?(?:file|@?\w+\.\w+)',
            r'(?:edit|modify|change|update)\s+\w+\.\w+',
            r'fix\s+(?:the\s+)?file'
        ]
    }
    
    GIT_PATTERNS = {
        'status': [
            r'git\s+status',
            r'repo(?:sitory)?\s+status',
            r'what\s+(?:files\s+)?(?:have\s+)?changed',
            r'show\s+(?:me\s+)?(?:git\s+)?status',
            r'current\s+(?:git\s+)?status'
        ],
        'diff': [
            r'git\s+diff',
            r'show\s+(?:me\s+)?(?:the\s+)?diff',
            r'what\s+(?:are\s+)?(?:the\s+)?changes',
            r'diff\s+(?:of\s+)?changes'
        ],
        'log': [
            r'git\s+log',
            r'(?:commit\s+)?history',
            r'recent\s+commits',
            r'show\s+(?:me\s+)?(?:the\s+)?log'
        ]
    }
    
    SEARCH_PATTERNS = {
        'grep': [
            r'(?:find|search|grep|look\s+for|locate)\s+',
            r'search\s+for\s+',
            r'find\s+(?:all\s+)?(?:instances\s+of|occurrences\s+of)',
            r'where\s+is\s+'
        ]
    }
    
    BASH_PATTERNS = {
        'run': [
            r'(?:run|execute)\s+(?:the\s+)?command',
            r'(?:run|execute)\s+["`\']?(?:npm|pip|python|node|cargo|go)',
            r'get\s+(?:my\s+)?(?:current\s+)?(?:pwd|directory)',
            r'what\s*\'?s\s+(?:my\s+)?(?:current\s+)?(?:pwd|directory)',
            r'run\s+\w+',
            r'execute\s+\w+'
        ]
    }

    @classmethod
    def analyze_intent(cls, user_input: str) -> List[ToolIntent]:
        """Analyze user input and return detected tool intentions."""
        intents = []
        lower_input = user_input.lower().strip()
        
        # Check for file operations
        file_intent = cls._detect_file_intent(user_input, lower_input)
        if file_intent:
            intents.append(file_intent)
        
        # Check for git operations
        git_intent = cls._detect_git_intent(user_input, lower_input)
        if git_intent:
            intents.append(git_intent)
        
        # Check for search operations
        search_intent = cls._detect_search_intent(user_input, lower_input)
        if search_intent:
            intents.append(search_intent)
        
        # Check for bash operations
        bash_intent = cls._detect_bash_intent(user_input, lower_input)
        if bash_intent:
            intents.append(bash_intent)
        
        # If no intents detected, return NONE
        if not intents:
            intents.append(ToolIntent(
                type=ToolType.NONE,
                action="none",
                target="",
                confidence=1.0
            ))
        
        return intents
    
    @classmethod
    def _detect_file_intent(cls, original: str, lower: str) -> Optional[ToolIntent]:
        """Detect file operation intents."""
        for action, patterns in cls.FILE_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    # Extract target filename if present
                    target = cls._extract_filename(original) or ""
                    confidence = 0.9 if target else 0.7
                    
                    return ToolIntent(
                        type=ToolType.FILE_OP,
                        action=action,
                        target=target,
                        confidence=confidence,
                        context={"original_text": original}
                    )
        return None
    
    @classmethod
    def _detect_git_intent(cls, original: str, lower: str) -> Optional[ToolIntent]:
        """Detect git operation intents."""
        for action, patterns in cls.GIT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lower):
                    return ToolIntent(
                        type=ToolType.GIT_OP,
                        action=action,
                        target="",
                        confidence=0.9
                    )
        return None
    
    @classmethod
    def _detect_search_intent(cls, original: str, lower: str) -> Optional[ToolIntent]:
        """Detect search operation intents."""
        for action, patterns in cls.SEARCH_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    # Extract search term
                    target = cls._extract_search_term(original, match) or ""
                    confidence = 0.8 if target else 0.6
                    
                    return ToolIntent(
                        type=ToolType.SEARCH_OP,
                        action=action,
                        target=target,
                        confidence=confidence
                    )
        return None
    
    @classmethod
    def _detect_bash_intent(cls, original: str, lower: str) -> Optional[ToolIntent]:
        """Detect bash operation intents."""
        for action, patterns in cls.BASH_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    # Extract command if present
                    target = cls._extract_command(original, match) or ""
                    confidence = 0.8 if target else 0.7
                    
                    return ToolIntent(
                        type=ToolType.BASH_OP,
                        action=action,
                        target=target,
                        confidence=confidence
                    )
        return None
    
    @staticmethod
    def _extract_filename(text: str) -> Optional[str]:
        """Extract filename from text."""
        # Look for file references like @filename.ext
        file_ref_pattern = r'@(\w+\.\w+)'
        match = re.search(file_ref_pattern, text)
        if match:
            return match.group(1)
        
        # Look for filename patterns
        filename_pattern = r'\b(\w+\.\w+)\b'
        matches = re.findall(filename_pattern, text)
        if matches:
            return matches[0]
        
        return None
    
    @staticmethod
    def _extract_search_term(text: str, match: re.Match) -> Optional[str]:
        """Extract search term from matched text."""
        # Get text after the match
        after_match = text[match.end():].strip()
        
        # Extract quoted strings first
        quoted_pattern = r'["\']([^"\']+)["\']'
        quoted_match = re.search(quoted_pattern, after_match)
        if quoted_match:
            return quoted_match.group(1)
        
        # Extract first word/phrase
        word_pattern = r'^(\w+(?:\s+\w+)*)'
        word_match = re.search(word_pattern, after_match)
        if word_match:
            return word_match.group(1)
        
        return None
    
    @staticmethod
    def _extract_command(text: str, match: re.Match) -> Optional[str]:
        """Extract command from matched text."""
        # Get text after the match
        after_match = text[match.end():].strip()
        
        # If the match already contains the command (like "run npm test")
        if any(cmd in match.group(0) for cmd in ['npm', 'pip', 'python', 'node', 'cargo', 'go']):
            # Extract the command part
            cmd_pattern = r'(npm|pip|python|node|cargo|go)(?:\s+[\w\-]+)*'
            cmd_match = re.search(cmd_pattern, match.group(0))
            if cmd_match:
                return cmd_match.group(0)
        
        # Look for quoted commands
        quoted_pattern = r'["\']([^"\']+)["\']'
        quoted_match = re.search(quoted_pattern, after_match)
        if quoted_match:
            return quoted_match.group(1)
        
        # Special case for pwd/directory requests
        if any(word in match.group(0) for word in ['pwd', 'directory']):
            return 'pwd'
        
        return None
"""Robust error recovery system for Phase 5."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from .result_formatter import OutputFormatter

# Set up logging
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can occur."""
    TOOL_NOT_FOUND = "tool_not_found"
    PERMISSION_DENIED = "permission_denied"
    FILE_NOT_FOUND = "file_not_found"
    COMMAND_FAILED = "command_failed"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error recovery."""
    error_type: ErrorType
    original_error: str
    user_input: str
    attempted_action: str
    suggestions: List[str] = None
    fallback_response: Optional[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class ErrorRecovery:
    """Handle errors gracefully with helpful suggestions."""
    
    # Common error patterns and their types
    ERROR_PATTERNS = {
        ErrorType.FILE_NOT_FOUND: [
            "no such file or directory",
            "file not found",
            "cannot find file",
            "no such file:"
        ],
        ErrorType.PERMISSION_DENIED: [
            "permission denied",
            "access denied",
            "not allowed"
        ],
        ErrorType.COMMAND_FAILED: [
            "command not found",
            "bad command",
            "invalid command"
        ],
        ErrorType.TIMEOUT: [
            "timeout",
            "timed out",
            "operation timed out"
        ]
    }
    
    # Suggestions for different error types
    ERROR_SUGGESTIONS = {
        ErrorType.FILE_NOT_FOUND: [
            "Check if the file path is correct",
            "Use tab completion or file browser to find the correct path",
            "Make sure you're in the right directory",
            "Try using absolute paths instead of relative paths"
        ],
        ErrorType.PERMISSION_DENIED: [
            "Check file permissions with 'ls -la'",
            "Try running with appropriate permissions",
            "Make sure you own the file or have write access",
            "Contact your system administrator if needed"
        ],
        ErrorType.COMMAND_FAILED: [
            "Check if the command is installed and available",
            "Verify the command syntax is correct",
            "Try using the full path to the command",
            "Check your PATH environment variable"
        ],
        ErrorType.TOOL_NOT_FOUND: [
            "The requested tool may not be available",
            "Try a different approach to accomplish your goal",
            "Check if required dependencies are installed"
        ],
        ErrorType.NETWORK_ERROR: [
            "Check your internet connection",
            "Verify the server/URL is accessible",
            "Try again in a few moments"
        ],
        ErrorType.TIMEOUT: [
            "The operation took too long to complete",
            "Try breaking down the task into smaller parts",
            "Check if the system is under heavy load"
        ],
        ErrorType.INVALID_INPUT: [
            "Check the input format and try again",
            "Refer to the help documentation for correct usage",
            "Try simplifying your request"
        ]
    }
    
    @classmethod
    def classify_error(cls, error_message: str) -> ErrorType:
        """Classify error type based on error message."""
        error_lower = error_message.lower()
        
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            if any(pattern in error_lower for pattern in patterns):
                return error_type
        
        return ErrorType.UNKNOWN
    
    @classmethod
    def create_error_context(cls, error: Exception, user_input: str, 
                           attempted_action: str) -> ErrorContext:
        """Create error context from exception."""
        error_message = str(error)
        error_type = cls.classify_error(error_message)
        suggestions = cls.ERROR_SUGGESTIONS.get(error_type, [])
        
        # Generate fallback response
        fallback_response = cls._generate_fallback_response(
            error_type, attempted_action, user_input
        )
        
        return ErrorContext(
            error_type=error_type,
            original_error=error_message,
            user_input=user_input,
            attempted_action=attempted_action,
            suggestions=suggestions.copy(),
            fallback_response=fallback_response
        )
    
    @classmethod
    def handle_tool_error(cls, error: Exception, tool_type: str, 
                         user_input: str) -> str:
        """Handle tool execution errors with recovery."""
        logger.error(f"Tool error in {tool_type}: {error}")
        
        error_context = cls.create_error_context(error, user_input, f"{tool_type} execution")
        
        # Try to provide a helpful response even if the tool failed
        if error_context.fallback_response:
            return error_context.fallback_response
        
        # Format error with suggestions
        return OutputFormatter.format_error(
            operation=f"{tool_type} operation",
            error=error_context.original_error,
            suggestions=error_context.suggestions
        )
    
    @classmethod
    def _generate_fallback_response(cls, error_type: ErrorType, 
                                  attempted_action: str, user_input: str) -> Optional[str]:
        """Generate fallback responses for common scenarios."""
        fallbacks = {
            ErrorType.FILE_NOT_FOUND: cls._file_not_found_fallback,
            ErrorType.COMMAND_FAILED: cls._command_failed_fallback,
            ErrorType.PERMISSION_DENIED: cls._permission_denied_fallback,
        }
        
        fallback_generator = fallbacks.get(error_type)
        if fallback_generator:
            return fallback_generator(user_input, attempted_action)
        
        return None
    
    @staticmethod
    def _file_not_found_fallback(user_input: str, attempted_action: str) -> str:
        """Generate fallback for file not found errors."""
        if "read" in attempted_action.lower():
            return ("I couldn't find the requested file. Would you like me to help you:\n"
                   "• Search for files with similar names\n"
                   "• List files in the current directory\n"
                   "• Create the file if it should exist")
        
        if "edit" in attempted_action.lower():
            return ("The file doesn't exist yet. I can help you:\n"
                   "• Create a new file with that name\n"
                   "• Search for files with similar names\n"
                   "• Check if you meant a different file")
        
        return "The requested file wasn't found. Let me know how you'd like to proceed."
    
    @staticmethod
    def _command_failed_fallback(user_input: str, attempted_action: str) -> str:
        """Generate fallback for command execution errors."""
        return ("The command couldn't be executed. This might be because:\n"
               "• The command isn't installed or available\n"
               "• There's a syntax error in the command\n"
               "• The command requires different permissions\n\n"
               "Would you like me to help you find an alternative approach?")
    
    @staticmethod
    def _permission_denied_fallback(user_input: str, attempted_action: str) -> str:
        """Generate fallback for permission errors."""
        return ("I don't have permission to perform this operation. This could be because:\n"
               "• The file/directory requires special permissions\n"
               "• You need to grant permission for file operations\n"
               "• The operation needs elevated privileges\n\n"
               "Please check the permissions and try again.")
    
    @classmethod
    def log_error_for_improvement(cls, error_context: ErrorContext):
        """Log errors for system improvement."""
        logger.info(f"Error recovery triggered: {error_context.error_type.value}")
        logger.debug(f"User input: {error_context.user_input}")
        logger.debug(f"Error: {error_context.original_error}")
        logger.debug(f"Attempted action: {error_context.attempted_action}")
    
    @classmethod
    def should_retry(cls, error_type: ErrorType, retry_count: int) -> bool:
        """Determine if operation should be retried."""
        max_retries = {
            ErrorType.NETWORK_ERROR: 2,
            ErrorType.TIMEOUT: 1,
            ErrorType.UNKNOWN: 1
        }
        
        return retry_count < max_retries.get(error_type, 0)
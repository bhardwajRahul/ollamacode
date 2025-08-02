"""Unified tool execution pipeline for Phase 5."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .intent_analyzer import IntentAnalyzer, ToolIntent, ToolType
from .result_formatter import OutputFormatter
from .error_recovery import ErrorRecovery, ErrorContext

from ..tools import FileOperations, GitOperations, SearchOperations, BashOperations
from ..permissions import PermissionManager

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    formatted_output: Optional[str] = None
    tool_type: Optional[ToolType] = None
    action: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Plan for executing tools based on user intent."""
    intents: List[ToolIntent]
    user_input: str
    needs_ai_response: bool = True


class ToolExecutor:
    """Unified tool execution pipeline."""
    
    def __init__(self, permission_manager: PermissionManager = None):
        """Initialize with tool instances."""
        self.permissions = permission_manager or PermissionManager()
        self.file_ops = FileOperations(self.permissions)
        self.git_ops = GitOperations()
        self.search_ops = SearchOperations()
        self.bash_ops = BashOperations()
        
        # Tool mapping
        self.tool_handlers = {
            ToolType.FILE_OP: self._execute_file_operation,
            ToolType.GIT_OP: self._execute_git_operation,
            ToolType.SEARCH_OP: self._execute_search_operation,
            ToolType.BASH_OP: self._execute_bash_operation,
        }
    
    def process_request(self, user_input: str) -> Tuple[List[ToolResult], ExecutionPlan]:
        """Main entry point - analyze intent and execute tools."""
        # Analyze user intent
        intents = IntentAnalyzer.analyze_intent(user_input)
        
        # Create execution plan
        plan = ExecutionPlan(
            intents=intents,
            user_input=user_input,
            needs_ai_response=self._should_include_ai_response(intents, user_input)
        )
        
        # Execute tools
        results = []
        for intent in intents:
            if intent.type != ToolType.NONE:
                result = self._execute_intent(intent, user_input)
                results.append(result)
        
        return results, plan
    
    def _execute_intent(self, intent: ToolIntent, user_input: str) -> ToolResult:
        """Execute a single tool intent."""
        logger.info(f"Executing intent: {intent.type.value}:{intent.action}")
        
        try:
            handler = self.tool_handlers.get(intent.type)
            if not handler:
                return ToolResult(
                    success=False,
                    error=f"No handler for tool type: {intent.type}",
                    tool_type=intent.type,
                    action=intent.action
                )
            
            return handler(intent, user_input)
            
        except Exception as e:
            logger.error(f"Error executing intent {intent.type}:{intent.action}: {e}")
            
            # Use error recovery
            error_msg = ErrorRecovery.handle_tool_error(
                e, intent.type.value, user_input
            )
            
            return ToolResult(
                success=False,
                error=str(e),
                formatted_output=error_msg,
                tool_type=intent.type,
                action=intent.action
            )
    
    def _execute_file_operation(self, intent: ToolIntent, user_input: str) -> ToolResult:
        """Execute file operations."""
        action = intent.action
        target = intent.target
        
        if action == "read":
            if not target:
                return ToolResult(
                    success=False,
                    error="No filename specified for read operation",
                    formatted_output="Please specify which file you'd like me to read."
                )
            
            content = self.file_ops.read_file(target)
            if content is not None:
                formatted = OutputFormatter.format_file_content(target, content)
                return ToolResult(
                    success=True,
                    data=content,
                    formatted_output=formatted,
                    tool_type=intent.type,
                    action=action
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Could not read file: {target}",
                    formatted_output=f"❌ Unable to read file: {target}"
                )
        
        elif action == "create":
            # For create operations, we need AI to generate content
            return ToolResult(
                success=True,
                data={"action": "create", "target": target, "user_input": user_input},
                formatted_output="I'll help you create that file. Let me generate appropriate content...",
                tool_type=intent.type,
                action=action
            )
        
        elif action == "edit":
            if not target:
                return ToolResult(
                    success=False,
                    error="No filename specified for edit operation",
                    formatted_output="Please specify which file you'd like me to edit."
                )
            
            # Check if file exists first
            existing_content = self.file_ops.read_file(target)
            if existing_content is not None:
                return ToolResult(
                    success=True,
                    data={"action": "edit", "target": target, "content": existing_content, "user_input": user_input},
                    formatted_output=f"I'll help you edit {target}. Let me analyze the current content...",
                    tool_type=intent.type,
                    action=action
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"File not found: {target}",
                    formatted_output=f"❌ File not found: {target}. Would you like me to create it instead?"
                )
        
        return ToolResult(
            success=False,
            error=f"Unknown file operation: {action}",
            tool_type=intent.type,
            action=action
        )
    
    def _execute_git_operation(self, intent: ToolIntent, user_input: str) -> ToolResult:
        """Execute git operations."""
        action = intent.action
        
        if not self.git_ops.is_git_repo():
            return ToolResult(
                success=False,
                error="Not in a git repository",
                formatted_output="❌ This directory is not a git repository."
            )
        
        try:
            if action == "status":
                status = self.git_ops.get_status()
                if status:
                    formatted = OutputFormatter.format_git_status(status)
                    return ToolResult(
                        success=True,
                        data=status,
                        formatted_output=formatted,
                        tool_type=intent.type,
                        action=action
                    )
            
            elif action == "diff":
                diff = self.git_ops.get_diff()
                if diff:
                    formatted = f"📋 Git diff:\n{diff}"
                    return ToolResult(
                        success=True,
                        data=diff,
                        formatted_output=formatted,
                        tool_type=intent.type,
                        action=action
                    )
                else:
                    return ToolResult(
                        success=True,
                        data="",
                        formatted_output="No changes to show (working tree is clean)",
                        tool_type=intent.type,
                        action=action
                    )
            
            elif action == "log":
                log_entries = self.git_ops.get_log(max_count=5)
                if log_entries:
                    lines = ["📜 Recent commits:"]
                    for entry in log_entries:
                        lines.append(f"  {entry['hash'][:8]} - {entry['message']} ({entry['date']})")
                    formatted = '\n'.join(lines)
                    return ToolResult(
                        success=True,
                        data=log_entries,
                        formatted_output=formatted,
                        tool_type=intent.type,
                        action=action
                    )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                formatted_output=f"❌ Git operation failed: {e}",
                tool_type=intent.type,
                action=action
            )
        
        return ToolResult(
            success=False,
            error=f"Unknown git operation: {action}",
            tool_type=intent.type,
            action=action
        )
    
    def _execute_search_operation(self, intent: ToolIntent, user_input: str) -> ToolResult:
        """Execute search operations."""
        action = intent.action
        target = intent.target
        
        if not target:
            # Try to extract from user input
            words = user_input.split()
            # Look for quoted strings or words after "for"
            for i, word in enumerate(words):
                if word.lower() in ["for", "find", "search"] and i + 1 < len(words):
                    target = words[i + 1]
                    break
        
        if not target:
            return ToolResult(
                success=False,
                error="No search pattern specified",
                formatted_output="Please specify what you'd like me to search for."
            )
        
        try:
            if action == "grep":
                results = self.search_ops.grep_files(target, max_results=10)
                formatted = OutputFormatter.format_search_results(target, results)
                return ToolResult(
                    success=True,
                    data=results,
                    formatted_output=formatted,
                    tool_type=intent.type,
                    action=action
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                formatted_output=f"❌ Search failed: {e}",
                tool_type=intent.type,
                action=action
            )
        
        return ToolResult(
            success=False,
            error=f"Unknown search operation: {action}",
            tool_type=intent.type,
            action=action
        )
    
    def _execute_bash_operation(self, intent: ToolIntent, user_input: str) -> ToolResult:
        """Execute bash operations."""
        action = intent.action
        target = intent.target
        
        if action == "run":
            if not target:
                # Extract command from user input
                import re
                patterns = [
                    r'(?:run|execute)\s+["`\']?([^"`\']+)["`\']?',
                    r'(?:run|execute)\s+(.+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, user_input, re.IGNORECASE)
                    if match:
                        target = match.group(1).strip()
                        break
            
            if not target:
                # Handle special cases
                if any(word in user_input.lower() for word in ['pwd', 'directory', 'current']):
                    target = 'pwd'
                else:
                    return ToolResult(
                        success=False,
                        error="No command specified",
                        formatted_output="Please specify which command you'd like me to run."
                    )
            
            try:
                result = self.bash_ops.run_command(target)
                if result['success']:
                    formatted = OutputFormatter.format_command_result(
                        target, result['stdout'], result.get('stderr')
                    )
                    return ToolResult(
                        success=True,
                        data=result,
                        formatted_output=formatted,
                        tool_type=intent.type,
                        action=action
                    )
                else:
                    error_msg = result.get('error', result.get('stderr', 'Unknown error'))
                    formatted = OutputFormatter.format_command_result(
                        target, "", error_msg
                    )
                    return ToolResult(
                        success=False,
                        error=error_msg,
                        formatted_output=formatted,
                        tool_type=intent.type,
                        action=action
                    )
            
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=str(e),
                    formatted_output=f"❌ Command execution failed: {e}",
                    tool_type=intent.type,
                    action=action
                )
        
        return ToolResult(
            success=False,
            error=f"Unknown bash operation: {action}",
            tool_type=intent.type,
            action=action
        )
    
    def _should_include_ai_response(self, intents: List[ToolIntent], user_input: str) -> bool:
        """Determine if AI response is needed after tool execution."""
        # Always include AI for file creation/editing
        for intent in intents:
            if intent.type == ToolType.FILE_OP and intent.action in ["create", "edit"]:
                return True
        
        # Include AI for complex requests or when tools fail
        if len(intents) > 1:
            return True
        
        # Include AI for conversational requests
        conversational_indicators = [
            "explain", "how", "why", "what", "help me", "can you", "please"
        ]
        
        lower_input = user_input.lower()
        if any(indicator in lower_input for indicator in conversational_indicators):
            return True
        
        # For single successful tool operations, AI response is optional
        return False
    
    def format_combined_response(self, results: List[ToolResult], 
                               plan: ExecutionPlan, ai_response: str = None) -> str:
        """Combine tool results with AI response."""
        response_parts = []
        
        # Add successful tool outputs
        for result in results:
            if result.success and result.formatted_output:
                response_parts.append(result.formatted_output)
        
        # Add error messages for failed tools
        failed_results = [r for r in results if not r.success]
        if failed_results:
            for result in failed_results:
                if result.formatted_output:
                    response_parts.append(result.formatted_output)
        
        # Add AI response if provided
        if ai_response and plan.needs_ai_response:
            if response_parts:
                response_parts.append("\n" + ai_response)
            else:
                response_parts.append(ai_response)
        
        return '\n\n'.join(response_parts) if response_parts else "No output generated."
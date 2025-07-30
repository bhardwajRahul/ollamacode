"""Permission system for OllamaCode operations."""

from enum import Enum
from typing import Dict, Set
from rich.console import Console
from rich.prompt import Confirm

console = Console()


class OperationType(Enum):
    """Types of operations that require permissions."""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    EXECUTE_COMMAND = "execute_command" 
    GIT_OPERATION = "git_operation"
    NETWORK_REQUEST = "network_request"


class PermissionManager:
    """Manage permissions for potentially dangerous operations."""
    
    def __init__(self):
        # Operations approved for this session
        self.session_approvals: Set[OperationType] = set()
        
        # Always safe operations (no approval needed)
        self.safe_operations = {
            OperationType.READ_FILE
        }
    
    def check_permission(self, operation: OperationType, 
                        description: str = "", 
                        auto_approve: bool = False) -> bool:
        """Check if operation is permitted."""
        
        # Always allow safe operations
        if operation in self.safe_operations:
            return True
        
        # Check if already approved for this session
        if operation in self.session_approvals:
            return True
        
        # Auto-approve if requested (for headless mode)
        if auto_approve:
            self.session_approvals.add(operation)
            return True
        
        # Ask user for permission
        return self._request_permission(operation, description)
    
    def _request_permission(self, operation: OperationType, description: str) -> bool:
        """Request permission from user."""
        operation_names = {
            OperationType.WRITE_FILE: "modify files",
            OperationType.DELETE_FILE: "delete files", 
            OperationType.EXECUTE_COMMAND: "execute commands",
            OperationType.GIT_OPERATION: "perform git operations",
            OperationType.NETWORK_REQUEST: "make network requests"
        }
        
        op_name = operation_names.get(operation, operation.value)
        
        if description:
            message = f"Permission needed to {op_name}: {description}"
        else:
            message = f"Permission needed to {op_name}"
        
        console.print(f"[yellow]⚠️  {message}[/yellow]")
        
        # Ask for permission with session approval option
        choices = [
            "Yes, once",
            "Yes, for this session", 
            "No"
        ]
        
        try:
            choice = console.input(
                "[dim]Allow? (1=once, 2=session, 3=no) [default: 1]: [/dim]"
            ).strip()
            
            if choice == "2":
                self.session_approvals.add(operation)
                console.print("[green]✓ Approved for session[/green]")
                return True
            elif choice == "3" or choice.lower() == "no":
                console.print("[red]✗ Permission denied[/red]")
                return False
            else:  # Default to "1" or "yes"
                console.print("[green]✓ Approved once[/green]")
                return True
                
        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]✗ Permission denied[/red]")
            return False
    
    def approve_all_for_session(self):
        """Approve all operations for this session (dangerous!)."""
        self.session_approvals = set(OperationType)
        console.print("[yellow]⚠️  All operations approved for this session[/yellow]")
    
    def reset_permissions(self):
        """Reset all session approvals."""
        self.session_approvals.clear()
        console.print("[green]✓ Permissions reset[/green]")
    
    def get_status(self) -> str:
        """Get current permission status."""
        if not self.session_approvals:
            return "[yellow]No operations pre-approved[/yellow]"
        
        approved = [op.value for op in self.session_approvals]
        return f"[green]Approved for session: {', '.join(approved)}[/green]"
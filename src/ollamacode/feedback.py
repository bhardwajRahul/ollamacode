"""Feedback collection system for OllamaCode using secure Pi endpoint."""

import json
import requests
import time
import hashlib
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.prompt import Confirm

from .config import Config

console = Console()


class FeedbackCollector:
    """Collect and submit user feedback via secure Pi endpoint."""
    
    def __init__(self):
        self.config = Config()
        feedback_config = self.config.get('feedback', {})
        
        # Pi endpoint configuration
        self.api_url = feedback_config.get('endpoint_url', 'http://100.76.97.90:8080/api/feedback')
        self.api_key = feedback_config.get('api_key', '')  # Optional API key for extra security
        self.enabled = feedback_config.get('enabled', True)
        self.include_session_data = feedback_config.get('include_session_data', True)
        
        # HTTP configuration
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "OllamaCode-Feedback/1.0",
            "X-Client-Version": "1.0.0"
        }
        
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    def is_configured(self) -> bool:
        """Check if feedback system is properly configured."""
        return bool(self.api_url and self.enabled)
    
    def submit_feedback(self, 
                       feedback_text: str, 
                       feedback_type: str = "general",
                       session_data: Optional[Dict[str, Any]] = None,
                       error_context: Optional[str] = None) -> bool:
        """Submit feedback to secure Pi endpoint."""
        
        if not self.is_configured():
            console.print("[yellow]⚠️  Feedback system not configured. Feedback saved locally only.[/yellow]")
            self._save_locally(feedback_text, feedback_type, session_data, error_context)
            return False
        
        try:
            # Create feedback payload
            feedback_payload = self._create_feedback_payload(feedback_text, feedback_type, session_data, error_context)
            
            # Submit to Pi endpoint
            response = requests.post(self.api_url, headers=self.headers, json=feedback_payload, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                feedback_id = response_data.get('feedback_id', 'unknown')
                console.print(f"[green]✅ Feedback submitted successfully![/green]")
                console.print(f"[dim]Feedback ID: {feedback_id}[/dim]")
                return True
            else:
                console.print(f"[red]❌ Failed to submit feedback: {response.status_code}[/red]")
                try:
                    error_info = response.json().get('error', response.text)
                    console.print(f"[dim]Error: {error_info}[/dim]")
                except:
                    console.print(f"[dim]{response.text}[/dim]")
                self._save_locally(feedback_text, feedback_type, session_data, error_context)
                return False
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Network error submitting feedback: {e}[/red]")
            self._save_locally(feedback_text, feedback_type, session_data, error_context)
            return False
        except Exception as e:
            console.print(f"[red]❌ Error submitting feedback: {e}[/red]")
            self._save_locally(feedback_text, feedback_type, session_data, error_context)
            return False
    
    def _create_feedback_payload(self, 
                                feedback_text: str, 
                                feedback_type: str, 
                                session_data: Optional[Dict[str, Any]], 
                                error_context: Optional[str]) -> Dict[str, Any]:
        """Create feedback payload for Pi endpoint."""
        
        # Generate unique feedback ID
        feedback_id = str(uuid.uuid4())
        
        # Create base payload
        payload = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now().isoformat(),
            "feedback_type": feedback_type,
            "feedback_text": feedback_text,
            "client_info": {
                "app": "OllamaCode",
                "version": "1.0.0",
                "platform": "CLI"
            }
        }
        
        # Add optional fields
        if error_context:
            payload["error_context"] = error_context
        
        if session_data and self.include_session_data:
            payload["session_data"] = session_data
        
        # Add basic security headers
        payload["client_hash"] = self._generate_client_hash(feedback_id, feedback_text)
        
        return payload
    
    def _generate_client_hash(self, feedback_id: str, feedback_text: str) -> str:
        """Generate a simple hash for basic integrity checking."""
        # Simple hash to verify the request isn't tampered with
        content = f"{feedback_id}:{feedback_text}:{datetime.now().strftime('%Y-%m-%d')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _save_locally(self, feedback_text: str, feedback_type: str, 
                     session_data: Optional[Dict[str, Any]], error_context: Optional[str]):
        """Save feedback locally as backup."""
        try:
            feedback_dir = self.config.config_dir / "feedback"
            feedback_dir.mkdir(exist_ok=True)
            
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": feedback_type,
                "feedback": feedback_text,
                "session_data": session_data,
                "error_context": error_context,
                "submitted": False
            }
            
            filename = f"feedback_{int(time.time())}.json"
            filepath = feedback_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(feedback_entry, f, indent=2)
            
            console.print(f"[dim]💾 Feedback saved locally to {filepath}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Failed to save feedback locally: {e}[/red]")
    
    def show_configuration_help(self):
        """Show help for configuring the feedback system."""
        console.print("\n[bold blue]📋 Feedback System Configuration[/bold blue]")
        console.print("\nTo enable feedback submission, add to your config:")
        console.print("\n[dim]~/.ollamacode/config.json[/dim]")
        console.print("""
{
  "feedback": {
    "endpoint_url": "http://100.76.97.90:8080/api/feedback",
    "api_key": "optional_api_key_for_extra_security",
    "include_session_data": true,
    "enabled": true
  }
}""")
        console.print("\n[dim]The feedback endpoint is securely hosted and processes all submissions.[/dim]")
    
    def configure_interactively(self):
        """Interactive configuration setup."""
        console.print("\n[bold blue]🔧 Feedback System Setup[/bold blue]")
        
        if not Confirm.ask("Would you like to enable feedback collection?"):
            self.config.set('feedback', {'enabled': False})
            console.print("[yellow]Feedback collection disabled.[/yellow]")
            return
        
        # Default to Pi endpoint
        console.print(f"\n[bold]Feedback Endpoint:[/bold] http://100.76.97.90:8080/api/feedback")
        console.print("[dim]This is the default secure endpoint for OllamaCode feedback.[/dim]")
        
        custom_endpoint = console.input("\n[bold]Custom endpoint (optional)[/bold]: ").strip()
        endpoint_url = custom_endpoint if custom_endpoint else "http://100.76.97.90:8080/api/feedback"
        
        api_key = console.input("\n[bold]API Key (optional, for extra security)[/bold]: ", password=True).strip()
        
        include_session = Confirm.ask("\nInclude session data in feedback? (helps with debugging)", default=True)
        
        # Save configuration
        feedback_config = {
            "endpoint_url": endpoint_url,
            "include_session_data": include_session,
            "enabled": True
        }
        
        if api_key:
            feedback_config["api_key"] = api_key
        
        current_config = self.config._config.copy()
        current_config["feedback"] = feedback_config
        self.config.update(current_config)
        
        console.print("\n[green]✅ Feedback system configured successfully![/green]")
        console.print(f"[dim]Endpoint: {endpoint_url}[/dim]")
        console.print("\nTest it with: [dim]/feedback \"Test message\"[/dim]")


def create_session_data(messages: List[Dict], recent_commands: List[str]) -> Dict[str, Any]:
    """Create session data for feedback submission."""
    return {
        "message_count": len(messages),
        "recent_commands": recent_commands[-10:],  # Last 10 commands
        "session_length_minutes": None,  # Could calculate from timestamps
        "last_messages": messages[-3:] if messages else [],  # Last 3 messages
        "ollamacode_version": "1.0.0"  # TODO: Get from version
    }
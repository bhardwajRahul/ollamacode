"""Ollama API client for OllamaCode."""

import json
import requests
import threading
import time
from typing import Dict, Any, Optional, Iterator
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live

from .cache import ResponseCache

console = Console()


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma3", enable_cache: bool = True):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        self.cache = ResponseCache() if enable_cache else None
    
    def generate(self, prompt: str, stream: bool = False) -> str:
        """Generate text using the specified model."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        
        try:
            if stream:
                # For streaming, show spinner only briefly then stream response
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console) as live:
                    response = self.session.post(url, json=payload, timeout=60, stream=True)
                    response.raise_for_status()
                    live.stop()
                    console.print("\n[bold green]Assistant[/bold green]: ", end="")
                    return self._handle_stream(response)
            else:
                # For non-streaming, show spinner during entire request
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console):
                    response = self.session.post(url, json=payload, timeout=60)
                    response.raise_for_status()
                    return response.json()["response"]
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error connecting to Ollama: {e}[/red]")
            return "Error: Could not connect to Ollama service"
    
    def _handle_stream(self, response: requests.Response) -> str:
        """Handle streaming response from Ollama."""
        result = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        chunk = data["response"]
                        console.print(chunk, end="")
                        result += chunk
                except json.JSONDecodeError:
                    continue
        console.print()  # New line after streaming
        return result
    
    def chat(self, messages: list, stream: bool = False) -> str:
        """Chat with the model using conversation format."""
        # Check cache first (only for non-streaming requests with recent user message)
        if self.cache and not stream and messages:
            last_user_msg = next((msg['content'] for msg in reversed(messages) 
                                if msg.get('role') == 'user'), None)
            
            if last_user_msg and self.cache.is_cacheable(last_user_msg):
                cached_response = self.cache.get(last_user_msg, self.model, messages)
                if cached_response:
                    console.print(f"\n[dim]💨 Cached response[/dim]")
                    return cached_response
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        
        try:
            if stream:
                # For streaming, show spinner only briefly then stream response
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console) as live:
                    response = self.session.post(url, json=payload, timeout=60, stream=True)
                    response.raise_for_status()
                    live.stop()
                    console.print("\n[bold green]Assistant[/bold green]: ", end="")
                    return self._handle_chat_stream(response)
            else:
                # For non-streaming, show spinner during entire request
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console):
                    response = self.session.post(url, json=payload, timeout=60)
                    response.raise_for_status()
                    result = response.json()["message"]["content"]
                    
                    # Cache the response if caching is enabled
                    if self.cache and messages:
                        last_user_msg = next((msg['content'] for msg in reversed(messages) 
                                            if msg.get('role') == 'user'), None)
                        if last_user_msg and self.cache.is_cacheable(last_user_msg):
                            self.cache.set(last_user_msg, self.model, result, messages)
                    
                    return result
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error connecting to Ollama: {e}[/red]")
            return "Error: Could not connect to Ollama service"
    
    def _handle_chat_stream(self, response: requests.Response) -> str:
        """Handle streaming chat response from Ollama."""
        result = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        chunk = data["message"]["content"]
                        console.print(chunk, end="")
                        result += chunk
                except json.JSONDecodeError:
                    continue
        console.print()  # New line after streaming
        return result
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
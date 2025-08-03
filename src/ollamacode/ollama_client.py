"""Ollama API client for OllamaCode."""

import json
import requests
import threading
import time
from typing import Dict, Any, Optional, Iterator, List
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live

from .cache import ResponseCache
from .tool_schemas import get_ollamacode_tools

console = Console()


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma3", enable_cache: bool = True, timeout: int = 60):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
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
                    response = self.session.post(url, json=payload, timeout=self.timeout, stream=True)
                    response.raise_for_status()
                    live.stop()
                    console.print("\n[bold green]Assistant[/bold green]: ", end="")
                    return self._handle_stream(response)
            else:
                # For non-streaming, show spinner during entire request
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console):
                    response = self.session.post(url, json=payload, timeout=self.timeout)
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
    
    def chat(self, messages: list, stream: bool = False, tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Chat with the model using conversation format, with optional tool calling support."""
        # Check cache first (only for non-streaming requests with recent user message and no tools)
        if self.cache and not stream and not tools and messages:
            last_user_msg = next((msg['content'] for msg in reversed(messages) 
                                if msg.get('role') == 'user'), None)
            
            if last_user_msg and self.cache.is_cacheable(last_user_msg):
                cached_response = self.cache.get(last_user_msg, self.model, messages)
                if cached_response:
                    console.print(f"\n[dim]💨 Cached response[/dim]")
                    return {"type": "text", "content": cached_response}
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
        
        try:
            if stream:
                # For streaming, show spinner only briefly then stream response
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console) as live:
                    response = self.session.post(url, json=payload, timeout=self.timeout, stream=True)
                    response.raise_for_status()
                    live.stop()
                    console.print("\n[bold green]Assistant[/bold green]: ", end="")
                    return {"type": "text", "content": self._handle_chat_stream(response)}
            else:
                # For non-streaming, show spinner during entire request
                with Live(Spinner("dots", text="[dim]Thinking...[/dim]"), refresh_per_second=10, console=console):
                    response = self.session.post(url, json=payload, timeout=self.timeout)
                    
                    # Check for tool support error before raising for status
                    if response.status_code == 400:
                        try:
                            error_data = response.json()
                            if "error" in error_data and "does not support tools" in error_data["error"]:
                                return {"type": "error", "content": error_data["error"]}
                        except json.JSONDecodeError:
                            pass
                    
                    response.raise_for_status()
                    response_data = response.json()
                    
                    # Handle tool calling response
                    message = response_data["message"]
                    
                    if "tool_calls" in message and message["tool_calls"]:
                        # Model wants to call tools
                        return {
                            "type": "tool_calls",
                            "tool_calls": message["tool_calls"],
                            "content": message.get("content", "")
                        }
                    else:
                        # Regular text response
                        result = message["content"]
                        
                        # Cache the response if caching is enabled (only for non-tool responses)
                        if self.cache and not tools and messages:
                            last_user_msg = next((msg['content'] for msg in reversed(messages) 
                                                if msg.get('role') == 'user'), None)
                            if last_user_msg and self.cache.is_cacheable(last_user_msg):
                                self.cache.set(last_user_msg, self.model, result, messages)
                        
                        return {"type": "text", "content": result}
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error connecting to Ollama: {e}[/red]")
            return {"type": "error", "content": f"Error: Could not connect to Ollama service: {e}"}
    
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
            response = self.session.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 10))
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def chat_with_tools(self, messages: list, stream: bool = False) -> Dict[str, Any]:
        """Chat with the model using OllamaCode's built-in tools."""
        tools = get_ollamacode_tools()
        response = self.chat(messages, stream=stream, tools=tools)
        
        # If model doesn't support tools, fall back to regular chat
        if response["type"] == "error" and "does not support tools" in response["content"]:
            console.print("[yellow]Model doesn't support tools, falling back to legacy mode[/yellow]")
            return self.chat(messages, stream=stream, tools=None)
        
        return response
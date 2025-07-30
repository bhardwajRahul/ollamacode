#!/usr/bin/env python3
"""Quick test script to verify tool functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.interactive_session import InteractiveSession
from unittest.mock import patch, Mock

def test_tool_execution():
    """Test that tools execute properly."""
    
    # Mock Ollama client
    with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.model = "gemma3"
        mock_client.chat.return_value = "Let me check the git status for you."
        mock_client_class.return_value = mock_client
        
        # Create session
        session = InteractiveSession()
        
        # Test git status detection and execution
        print("Testing git status tool...")
        response = session._execute_suggested_tools("Let me check git status", "check git status")
        print("Response:", response)
        
        # Test search detection
        print("\nTesting search tool...")
        response = session._execute_suggested_tools("I'll search for functions", "find all functions")
        print("Response:", response)

if __name__ == "__main__":
    test_tool_execution()
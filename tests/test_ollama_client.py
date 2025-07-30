"""Tests for OllamaClient."""

import pytest
from unittest.mock import Mock, patch
from ollamacode.ollama_client import OllamaClient


def test_ollama_client_init():
    """Test OllamaClient initialization."""
    client = OllamaClient()
    assert client.base_url == "http://localhost:11434"
    assert client.model == "gemma3"
    
    client = OllamaClient(base_url="http://example.com", model="llama2")
    assert client.base_url == "http://example.com"
    assert client.model == "llama2"


@patch('ollamacode.ollama_client.requests.Session.post')
def test_generate_success(mock_post):
    """Test successful text generation."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"response": "Hello, world!"}
    mock_post.return_value = mock_response
    
    client = OllamaClient()
    result = client.generate("Test prompt")
    
    assert result == "Hello, world!"
    mock_post.assert_called_once()


@patch('ollamacode.ollama_client.requests.Session.get')
def test_is_available_success(mock_get):
    """Test service availability check."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    client = OllamaClient()
    assert client.is_available() is True


@patch('ollamacode.ollama_client.requests.Session.get')
def test_is_available_failure(mock_get):
    """Test service availability check when service is down."""
    from requests.exceptions import RequestException
    mock_get.side_effect = RequestException("Connection error")
    
    client = OllamaClient()
    assert client.is_available() is False
#!/usr/bin/env python3
"""Test streaming functionality for OllamaCode."""

import sys
import json
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from contextlib import redirect_stdout

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.ollama_client import OllamaClient
from ollamacode.interactive_session import InteractiveSession


class MockResponse:
    """Mock response for streaming tests."""
    
    def __init__(self, stream_data, status_code=200):
        self.stream_data = stream_data
        self.status_code = status_code
    
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP {self.status_code}")
    
    def iter_lines(self, decode_unicode=True):
        for data in self.stream_data:
            yield json.dumps(data)


class TestStreaming:
    """Test streaming functionality."""
    
    def __init__(self):
        self.test_results = []
    
    def run_all_tests(self):
        """Run all streaming tests."""
        print("🌊 Running Streaming Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_stream_response_parsing,
            self.test_chat_stream_parsing,
            self.test_streaming_with_interruption,
            self.test_interactive_session_streaming,
            self.test_streaming_error_handling,
            self.test_streaming_vs_non_streaming
        ]
        
        for test in tests:
            try:
                print(f"\n📋 Running {test.__name__}...")
                result = test()
                self.test_results.append((test.__name__, "PASS" if result else "FAIL"))
                print(f"✅ {test.__name__}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                self.test_results.append((test.__name__, f"ERROR: {e}"))
                print(f"❌ {test.__name__}: ERROR - {e}")
        
        self.print_summary()
    
    def test_stream_response_parsing(self) -> bool:
        """Test streaming response parsing."""
        # Mock streaming data
        stream_data = [
            {"response": "Hello "},
            {"response": "world! "},
            {"response": "How can I help?"},
            {"done": True}
        ]
        
        mock_response = MockResponse(stream_data)
        
        # Create client and test streaming
        client = OllamaClient()
        
        # Capture output to verify streaming behavior
        captured_output = io.StringIO()
        
        with patch.object(client.session, 'post', return_value=mock_response):
            with redirect_stdout(captured_output):
                with patch('ollamacode.ollama_client.console') as mock_console:
                    result = client._handle_stream(mock_response)
        
        expected = "Hello world! How can I help?"
        return result == expected
    
    def test_chat_stream_parsing(self) -> bool:
        """Test chat streaming response parsing."""
        # Mock chat streaming data
        stream_data = [
            {"message": {"content": "I understand "}},
            {"message": {"content": "your question. "}},
            {"message": {"content": "Let me help!"}},
            {"done": True}
        ]
        
        mock_response = MockResponse(stream_data)
        
        # Create client and test chat streaming
        client = OllamaClient()
        
        with patch.object(client.session, 'post', return_value=mock_response):
            with patch('ollamacode.ollama_client.console'):
                result = client._handle_chat_stream(mock_response)
        
        expected = "I understand your question. Let me help!"
        return result == expected
    
    def test_streaming_with_interruption(self) -> bool:
        """Test streaming handles malformed JSON gracefully."""
        # Mock streaming data with bad JSON
        stream_data = [
            {"message": {"content": "Hello "}},
            "invalid json line",  # This should be skipped
            {"message": {"content": "world!"}},
            {"done": True}
        ]
        
        # Create a mock response that yields both valid and invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.iter_lines = Mock(return_value=[
            json.dumps({"message": {"content": "Hello "}}),
            "invalid json line",
            json.dumps({"message": {"content": "world!"}}),
            json.dumps({"done": True})
        ])
        
        client = OllamaClient()
        
        with patch('ollamacode.ollama_client.console'):
            result = client._handle_chat_stream(mock_response)
        
        # Should skip invalid JSON and continue processing
        expected = "Hello world!"
        return result == expected
    
    def test_interactive_session_streaming(self) -> bool:
        """Test that interactive session uses streaming by default."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            mock_client.chat.return_value = "Streamed response"
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            session.messages = [{"role": "user", "content": "Test"}]
            
            # Trigger AI response
            session._get_ai_response()
            
            # Verify chat was called with stream=True
            mock_client.chat.assert_called_with(session.messages, stream=True)
            
            return True
    
    def test_streaming_error_handling(self) -> bool:
        """Test streaming error handling."""
        # Mock a request exception
        import requests
        client = OllamaClient()
        
        with patch.object(client.session, 'post', side_effect=requests.exceptions.RequestException("Connection error")):
            with patch('ollamacode.ollama_client.console'):
                result = client.chat([], stream=True)
        
        # Should handle error gracefully
        return "Error: Could not connect to Ollama service" in result
    
    def test_streaming_vs_non_streaming(self) -> bool:
        """Test that both streaming and non-streaming modes work."""
        # Mock responses
        stream_response = MockResponse([
            {"message": {"content": "Streamed "}},
            {"message": {"content": "response"}},
            {"done": True}
        ])
        
        non_stream_response = Mock()
        non_stream_response.status_code = 200
        non_stream_response.raise_for_status = Mock()
        non_stream_response.json.return_value = {
            "message": {"content": "Non-streamed response"}
        }
        
        client = OllamaClient()
        
        # Test streaming
        with patch.object(client.session, 'post', return_value=stream_response):
            with patch('ollamacode.ollama_client.console'):
                stream_result = client.chat([], stream=True)
        
        # Test non-streaming
        with patch.object(client.session, 'post', return_value=non_stream_response):
            with patch('ollamacode.ollama_client.console'):
                non_stream_result = client.chat([], stream=False)
        
        return (stream_result == "Streamed response" and 
                non_stream_result == "Non-streamed response")
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Streaming Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} streaming tests passed")
        
        if passed == total:
            print("🎉 All streaming tests passed! Streaming functionality is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review streaming implementation.")


def main():
    """Run the streaming test suite."""
    tester = TestStreaming()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
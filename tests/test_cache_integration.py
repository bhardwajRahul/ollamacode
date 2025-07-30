#!/usr/bin/env python3
"""Integration tests for response caching in OllamaCode."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.ollama_client import OllamaClient
from ollamacode.interactive_session import InteractiveSession


class TestCacheIntegration:
    """Test cache integration with OllamaClient and InteractiveSession."""
    
    def __init__(self):
        self.test_results = []
        self.test_dir = Path(tempfile.mkdtemp())
    
    def run_all_tests(self):
        """Run all cache integration tests."""
        print("🔗 Running Cache Integration Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_client_cache_integration,
            self.test_cache_hit_behavior,
            self.test_cache_miss_behavior,
            self.test_non_cacheable_requests,
            self.test_streaming_bypasses_cache,
            self.test_session_cache_commands,
            self.test_cache_with_context_sensitivity
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
    
    def test_client_cache_integration(self) -> bool:
        """Test basic cache integration with OllamaClient."""
        # Mock the requests to avoid actual API calls
        with patch('ollamacode.ollama_client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.json.return_value = {"message": {"content": "Test response"}}
            mock_response.raise_for_status = Mock()
            mock_session.post.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = OllamaClient(enable_cache=True)
            # Clear any existing cache to ensure clean test
            if client.cache:
                client.cache.clear()
            
            # First request should call API
            messages = [{"role": "user", "content": "What is Python?"}]
            response1 = client.chat(messages, stream=False)
            
            if response1 != "Test response":
                return False
            
            # Second identical request should use cache (no API call)
            mock_session.post.reset_mock()
            response2 = client.chat(messages, stream=False)
            
            if response2 != "Test response":
                return False
            
            # Should not have called API the second time
            if mock_session.post.called:
                return False
            
            return True
    
    def test_cache_hit_behavior(self) -> bool:
        """Test cache hit behavior with console output."""
        with patch('ollamacode.ollama_client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.json.return_value = {"message": {"content": "Cached response"}}
            mock_response.raise_for_status = Mock()
            mock_session.post.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            with patch('ollamacode.ollama_client.console') as mock_console:
                client = OllamaClient(enable_cache=True)
            # Clear any existing cache to ensure clean test
            if client.cache:
                client.cache.clear()
                
                # First request
                messages = [{"role": "user", "content": "Explain recursion"}]
                client.chat(messages, stream=False)
                
                # Second request should show cache indicator
                client.chat(messages, stream=False)
                
                # Check that cache indicator was printed
                cache_printed = any("💨 Cached response" in str(call) for call in mock_console.print.call_args_list)
                return cache_printed
    
    def test_cache_miss_behavior(self) -> bool:
        """Test cache miss with different prompts."""
        with patch('ollamacode.ollama_client.requests.Session') as mock_session_class:
            mock_session = Mock()
            
            # Return different responses for different calls
            mock_response1 = Mock()
            mock_response1.json.return_value = {"message": {"content": "Python response"}}
            mock_response1.raise_for_status = Mock()
            
            mock_response2 = Mock()
            mock_response2.json.return_value = {"message": {"content": "JavaScript response"}}
            mock_response2.raise_for_status = Mock()
            
            mock_session.post.side_effect = [mock_response1, mock_response2]
            mock_session_class.return_value = mock_session
            
            client = OllamaClient(enable_cache=True)
            # Clear any existing cache to ensure clean test
            if client.cache:
                client.cache.clear()
            
            # Two different requests should both call API
            response1 = client.chat([{"role": "user", "content": "What is Python?"}], stream=False)
            response2 = client.chat([{"role": "user", "content": "What is JavaScript?"}], stream=False)
            
            # Should get different responses
            if response1 != "Python response" or response2 != "JavaScript response":
                return False
            
            # Should have called API twice
            if mock_session.post.call_count != 2:
                return False
            
            return True
    
    def test_non_cacheable_requests(self) -> bool:
        """Test that time-sensitive requests are not cached."""
        with patch('ollamacode.ollama_client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.json.return_value = {"message": {"content": "Current time is..."}}
            mock_response.raise_for_status = Mock()
            mock_session.post.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = OllamaClient(enable_cache=True)
            # Clear any existing cache to ensure clean test
            if client.cache:
                client.cache.clear()
            
            # Time-sensitive request should not be cached
            messages = [{"role": "user", "content": "What is the current time?"}]
            response1 = client.chat(messages, stream=False)
            response2 = client.chat(messages, stream=False)
            
            # Should call API both times (not cached)
            if mock_session.post.call_count != 2:
                return False
            
            return True
    
    def test_streaming_bypasses_cache(self) -> bool:
        """Test that streaming requests bypass cache."""
        with patch('ollamacode.ollama_client.requests.Session') as mock_session_class:
            mock_session = Mock()
            
            # Mock streaming response
            mock_response = Mock()
            mock_response.iter_lines.return_value = [
                '{"message": {"content": "Stream "}}',
                '{"message": {"content": "response"}}'
            ]
            mock_response.raise_for_status = Mock()
            mock_session.post.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = OllamaClient(enable_cache=True)
            # Clear any existing cache to ensure clean test
            if client.cache:
                client.cache.clear()
            
            with patch('ollamacode.ollama_client.console'):
                # Streaming requests should always call API
                messages = [{"role": "user", "content": "What is Python?"}]
                client.chat(messages, stream=True)
                client.chat(messages, stream=True)
                
                # Should call API both times (streaming bypasses cache)
                if mock_session.post.call_count != 2:
                    return False
            
            return True
    
    def test_session_cache_commands(self) -> bool:
        """Test cache management slash commands."""
        with patch('ollamacode.interactive_session.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = "gemma3"
            
            # Mock cache
            mock_cache = Mock()
            mock_cache.get_stats.return_value = {
                'total_entries': 5,
                'total_hits': 10,
                'hit_rate': 2.0,
                'cache_size_mb': 0.5,
                'oldest_entry': 1640995200.0  # 2022-01-01
            }
            mock_client.cache = mock_cache
            mock_client_class.return_value = mock_client
            
            session = InteractiveSession()
            
            # Test cache status command
            status_result = session._handle_slash_command("/cache status")
            if "Cache Status" not in status_result:
                return False
            
            # Test cache clear command
            clear_result = session._handle_slash_command("/cache clear")
            if "Cache cleared" not in clear_result:
                return False
            
            # Verify clear was called
            mock_cache.clear.assert_called_once()
            
            # Test cache stats command
            stats_result = session._handle_slash_command("/cache stats")
            if "Detailed Cache Statistics" not in stats_result:
                return False
            
            return True
    
    def test_cache_with_context_sensitivity(self) -> bool:
        """Test that cache is sensitive to conversation context."""
        with patch('ollamacode.ollama_client.requests.Session') as mock_session_class:
            mock_session = Mock()
            
            # Create separate mock responses
            mock_response1 = Mock()
            mock_response1.json.return_value = {"message": {"content": "Python context response"}}
            mock_response1.raise_for_status = Mock()
            
            mock_response2 = Mock()
            mock_response2.json.return_value = {"message": {"content": "JavaScript context response"}}
            mock_response2.raise_for_status = Mock()
            
            mock_session.post.side_effect = [mock_response1, mock_response2]
            mock_session_class.return_value = mock_session
            
            client = OllamaClient(enable_cache=True)
            # Clear any existing cache to ensure clean test
            if client.cache:
                client.cache.clear()
            
            # Same user message, different contexts
            context1 = [
                {"role": "system", "content": "You are a Python expert"},
                {"role": "user", "content": "Explain this"}
            ]
            
            context2 = [
                {"role": "system", "content": "You are a JavaScript expert"},
                {"role": "user", "content": "Explain this"}
            ]
            
            # Should cache separately due to different contexts
            response1 = client.chat(context1, stream=False)
            response2 = client.chat(context2, stream=False)
            
            # Both should call API (different contexts)
            if mock_session.post.call_count != 2:
                return False
            
            # Same context should hit cache
            mock_session.post.reset_mock()
            response3 = client.chat(context1, stream=False)
            
            # Should not call API (cache hit) and should return cached response
            if mock_session.post.called:
                return False
            
            if response3 != "Python context response":
                return False
            
            return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Cache Integration Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} cache integration tests passed")
        
        if passed == total:
            print("🎉 All cache integration tests passed! Response caching is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review cache integration.")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


def main():
    """Run the cache integration test suite."""
    tester = TestCacheIntegration()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
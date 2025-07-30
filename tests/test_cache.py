#!/usr/bin/env python3
"""Tests for the response caching system."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollamacode.cache import ResponseCache, CacheEntry


class TestResponseCache:
    """Test the response caching system."""
    
    def __init__(self):
        self.test_results = []
        self.test_dir = Path(tempfile.mkdtemp())
    
    def run_all_tests(self):
        """Run all cache tests."""
        print("🗄️  Running Cache Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_cache_basic_operations,
            self.test_cache_key_generation,
            self.test_cache_expiration,
            self.test_cache_context_sensitivity,
            self.test_cache_eviction,
            self.test_cache_persistence,
            self.test_cache_statistics,
            self.test_cacheable_detection
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
    
    def test_cache_basic_operations(self) -> bool:
        """Test basic cache set/get operations."""
        cache = ResponseCache(cache_dir=self.test_dir / "cache1")
        
        # Test setting and getting
        prompt = "What is Python?"
        model = "gemma3"
        response = "Python is a programming language."
        
        cache.set(prompt, model, response)
        cached_response = cache.get(prompt, model)
        
        if cached_response != response:
            return False
        
        # Test cache miss
        miss_response = cache.get("Different prompt", model)
        if miss_response is not None:
            return False
        
        # Test clearing cache
        cache.clear()
        cleared_response = cache.get(prompt, model)
        if cleared_response is not None:
            return False
        
        return True
    
    def test_cache_key_generation(self) -> bool:
        """Test cache key generation and normalization."""
        cache = ResponseCache(cache_dir=self.test_dir / "cache2")
        
        # Test prompt normalization (whitespace should be normalized)
        prompt1 = "What is    Python?"
        prompt2 = "What is Python?"
        model = "gemma3"
        
        key1 = cache._generate_key(prompt1, model)
        key2 = cache._generate_key(prompt2, model)
        
        if key1 != key2:
            return False
        
        # Different models should generate different keys
        key3 = cache._generate_key(prompt1, "different-model")
        if key1 == key3:
            return False
        
        # Different context should generate different keys
        context1 = [{"role": "user", "content": "Previous message"}]
        context2 = [{"role": "user", "content": "Different message"}]
        
        hash1 = cache._get_context_hash(context1)
        hash2 = cache._get_context_hash(context2)
        
        if hash1 == hash2:
            return False
        
        return True
    
    def test_cache_expiration(self) -> bool:
        """Test cache entry expiration."""
        cache = ResponseCache(cache_dir=self.test_dir / "cache3")
        
        prompt = "Test prompt"
        model = "gemma3"
        response = "Test response"
        
        # Set with short TTL
        cache.set(prompt, model, response, ttl_seconds=1)
        
        # Should be available immediately
        cached = cache.get(prompt, model)
        if cached != response:
            return False
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        expired = cache.get(prompt, model)
        if expired is not None:
            return False
        
        return True
    
    def test_cache_context_sensitivity(self) -> bool:
        """Test that cache is sensitive to conversation context."""
        cache = ResponseCache(cache_dir=self.test_dir / "cache4")
        
        prompt = "Continue the conversation"
        model = "gemma3"
        
        # Same prompt, different contexts
        context1 = [{"role": "user", "content": "Let's talk about Python"}]
        context2 = [{"role": "user", "content": "Let's talk about JavaScript"}]
        
        response1 = "About Python..."
        response2 = "About JavaScript..."
        
        # Cache responses with different contexts
        cache.set(prompt, model, response1, context1)
        cache.set(prompt, model, response2, context2)
        
        # Should retrieve different responses based on context
        cached1 = cache.get(prompt, model, context1)
        cached2 = cache.get(prompt, model, context2)
        
        if cached1 != response1 or cached2 != response2:
            return False
        
        return True
    
    def test_cache_eviction(self) -> bool:
        """Test cache eviction when max entries is reached."""
        # Create cache with small max size
        cache = ResponseCache(cache_dir=self.test_dir / "cache5", max_entries=3)
        
        # Add entries up to the limit
        for i in range(3):
            cache.set(f"prompt_{i}", "gemma3", f"response_{i}")
        
        # All should be cached
        for i in range(3):
            if cache.get(f"prompt_{i}", "gemma3") != f"response_{i}":
                return False
        
        # Add one more (should evict oldest)
        time.sleep(0.1)  # Ensure different timestamps
        cache.set("prompt_3", "gemma3", "response_3")
        
        # First entry should be evicted
        if cache.get("prompt_0", "gemma3") is not None:
            return False
        
        # Others should still be there
        for i in range(1, 4):
            if cache.get(f"prompt_{i}", "gemma3") != f"response_{i}":
                return False
        
        return True
    
    def test_cache_persistence(self) -> bool:
        """Test cache persistence to disk."""
        cache_dir = self.test_dir / "cache6"
        
        # Create cache and add entries
        cache1 = ResponseCache(cache_dir=cache_dir)
        cache1.set("test_prompt", "gemma3", "test_response")
        
        # Create new cache instance (should load from disk)
        cache2 = ResponseCache(cache_dir=cache_dir)
        cached_response = cache2.get("test_prompt", "gemma3")
        
        if cached_response != "test_response":
            return False
        
        return True
    
    def test_cache_statistics(self) -> bool:
        """Test cache statistics functionality."""
        cache = ResponseCache(cache_dir=self.test_dir / "cache7")
        
        # Empty cache stats
        stats = cache.get_stats()
        if stats['total_entries'] != 0:
            return False
        
        # Add some entries and hits
        cache.set("prompt1", "gemma3", "response1")
        cache.set("prompt2", "gemma3", "response2")
        
        # Generate some hits
        cache.get("prompt1", "gemma3")
        cache.get("prompt1", "gemma3")
        cache.get("prompt2", "gemma3")
        
        stats = cache.get_stats()
        
        if stats['total_entries'] != 2:
            return False
        
        if stats['total_hits'] != 3:
            return False
        
        if stats['cache_size_mb'] < 0:
            return False
        
        return True
    
    def test_cacheable_detection(self) -> bool:
        """Test detection of cacheable vs non-cacheable prompts."""
        cache = ResponseCache(cache_dir=self.test_dir / "cache8")
        
        # Cacheable prompts
        cacheable_prompts = [
            "What is Python?",
            "Explain object-oriented programming",
            "How do I create a list in Python?"
        ]
        
        for prompt in cacheable_prompts:
            if not cache.is_cacheable(prompt):
                return False
        
        # Non-cacheable prompts (time-sensitive)
        non_cacheable_prompts = [
            "What is the current time?",
            "Generate a random number",
            "What's today's date?",
            "Give me a UUID now"
        ]
        
        for prompt in non_cacheable_prompts:
            if cache.is_cacheable(prompt):
                return False
        
        return True
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 Cache Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print(f"\n📈 Overall: {passed}/{total} cache tests passed")
        
        if passed == total:
            print("🎉 All cache tests passed! Response caching system is working correctly.")
        else:
            print(f"⚠️  {total - passed} tests failed. Review cache implementation.")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


def main():
    """Run the cache test suite."""
    tester = TestResponseCache()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
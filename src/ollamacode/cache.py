"""Response caching system for OllamaCode."""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    content: str
    timestamp: float
    hit_count: int = 0
    ttl_seconds: int = 3600  # 1 hour default


class ResponseCache:
    """Intelligent response caching system."""
    
    def __init__(self, cache_dir: Path = None, max_entries: int = 1000):
        self.cache_dir = cache_dir or Path.home() / ".ollamacode" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self.cache_file = self.cache_dir / "response_cache.json"
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._load_cache()
    
    def _generate_key(self, prompt: str, model: str, context_hash: str = "") -> str:
        """Generate a unique cache key for the prompt."""
        # Normalize prompt (remove extra whitespace, etc.)
        normalized_prompt = " ".join(prompt.strip().split())
        
        # Create hash from prompt + model + context
        key_string = f"{normalized_prompt}|{model}|{context_hash}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def _get_context_hash(self, messages: list) -> str:
        """Generate a hash of the conversation context."""
        # Only include the last few messages for context sensitivity
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        context_str = json.dumps([msg for msg in recent_messages if msg.get('role') != 'system'])
        return hashlib.md5(context_str.encode()).hexdigest()[:8]
    
    def get(self, prompt: str, model: str, messages: list = None) -> Optional[str]:
        """Get cached response if available and fresh."""
        context_hash = self._get_context_hash(messages or [])
        cache_key = self._generate_key(prompt, model, context_hash)
        
        entry = self._memory_cache.get(cache_key)
        if not entry:
            return None
        
        # Check if entry has expired
        if time.time() - entry.timestamp > entry.ttl_seconds:
            self._invalidate_key(cache_key)
            return None
        
        # Update hit count and return
        entry.hit_count += 1
        entry.timestamp = time.time()  # Update access time
        return entry.content
    
    def set(self, prompt: str, model: str, response: str, messages: list = None, ttl_seconds: int = 3600):
        """Cache a response."""
        context_hash = self._get_context_hash(messages or [])
        cache_key = self._generate_key(prompt, model, context_hash)
        
        entry = CacheEntry(
            content=response,
            timestamp=time.time(),
            hit_count=0,
            ttl_seconds=ttl_seconds
        )
        
        self._memory_cache[cache_key] = entry
        
        # Evict old entries if cache is too large
        self._evict_if_needed()
        
        # Save to disk
        self._save_cache()
    
    def _invalidate_key(self, cache_key: str):
        """Remove a cache entry."""
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
    
    def _evict_if_needed(self):
        """Evict least recently used entries if cache is too large."""
        if len(self._memory_cache) <= self.max_entries:
            return
        
        # Sort by timestamp (oldest first)
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1].timestamp
        )
        
        # Remove oldest entries until we're under the limit
        entries_to_remove = len(self._memory_cache) - self.max_entries
        for i in range(entries_to_remove):
            key, _ = sorted_entries[i]
            del self._memory_cache[key]
    
    def _load_cache(self):
        """Load cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
            
            for key, entry_data in data.items():
                entry = CacheEntry(
                    content=entry_data['content'],
                    timestamp=entry_data['timestamp'],
                    hit_count=entry_data.get('hit_count', 0),
                    ttl_seconds=entry_data.get('ttl_seconds', 3600)
                )
                self._memory_cache[key] = entry
        
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            # If cache is corrupted, start fresh
            self._memory_cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            data = {}
            for key, entry in self._memory_cache.items():
                data[key] = {
                    'content': entry.content,
                    'timestamp': entry.timestamp,
                    'hit_count': entry.hit_count,
                    'ttl_seconds': entry.ttl_seconds
                }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception:
            # If we can't save, that's OK - we'll just lose the cache
            pass
    
    def clear(self):
        """Clear all cached responses."""
        self._memory_cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._memory_cache:
            return {
                'total_entries': 0,
                'total_hits': 0,
                'cache_size_mb': 0,
                'oldest_entry': None,
                'hit_rate': 0
            }
        
        total_hits = sum(entry.hit_count for entry in self._memory_cache.values())
        total_size = sum(len(entry.content.encode()) for entry in self._memory_cache.values())
        oldest_timestamp = min(entry.timestamp for entry in self._memory_cache.values())
        
        return {
            'total_entries': len(self._memory_cache),
            'total_hits': total_hits,
            'cache_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_entry': oldest_timestamp,
            'hit_rate': round(total_hits / len(self._memory_cache), 2) if self._memory_cache else 0
        }
    
    def is_cacheable(self, prompt: str) -> bool:
        """Determine if a prompt should be cached."""
        # Don't cache certain types of prompts
        non_cacheable_patterns = [
            "current time",
            "now",
            "today",
            "random",
            "generate uuid",
            "timestamp"
        ]
        
        prompt_lower = prompt.lower()
        return not any(pattern in prompt_lower for pattern in non_cacheable_patterns)
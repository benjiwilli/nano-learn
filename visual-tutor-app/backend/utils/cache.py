"""Caching utilities for Visual Tutor App."""

import asyncio
import hashlib
import json
import time
from typing import Any, Optional, TypeVar, Generic, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Single cache entry with metadata."""
    value: T
    created_at: float
    expires_at: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def touch(self) -> None:
        """Record a cache hit."""
        self.hits += 1


class LRUCache(Generic[T]):
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    async def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats["hits"] += 1
            
            return entry.value
    
    async def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        now = time.time()
        
        async with self._lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl
            )
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> int:
        """Clear all entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "hit_rate": hit_rate
        }


class ExplanationCache:
    """Specialized cache for educational explanations."""
    
    def __init__(self, max_size: int = 500, ttl: int = 7200):
        self._cache = LRUCache[dict](max_size=max_size, default_ttl=ttl)
    
    @staticmethod
    def _generate_key(
        concept: str,
        subject: str,
        difficulty: str,
        style: str
    ) -> str:
        """Generate cache key from explanation parameters."""
        key_data = f"{concept.lower().strip()}:{subject}:{difficulty}:{style}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    async def get_explanation(
        self,
        concept: str,
        subject: str,
        difficulty: str = "intermediate",
        style: str = "schematic"
    ) -> Optional[dict]:
        """Get cached explanation if available."""
        key = self._generate_key(concept, subject, difficulty, style)
        return await self._cache.get(key)
    
    async def store_explanation(
        self,
        concept: str,
        subject: str,
        explanation: dict,
        difficulty: str = "intermediate",
        style: str = "schematic",
        ttl: Optional[int] = None
    ) -> None:
        """Store explanation in cache."""
        key = self._generate_key(concept, subject, difficulty, style)
        await self._cache.set(key, explanation, ttl)
        logger.debug(f"Cached explanation for: {concept}")
    
    async def get_similar(
        self,
        concept: str,
        subject: str,
        threshold: float = 0.8
    ) -> Optional[dict]:
        """
        Find similar cached explanation using fuzzy matching.
        This is a simplified version - production would use embeddings.
        """
        # For now, just check exact matches
        # Future: use sentence embeddings for similarity
        return await self.get_explanation(concept, subject)
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.get_stats()


class PromptCache:
    """Cache for generated prompts."""
    
    def __init__(self, max_size: int = 200, ttl: int = 3600):
        self._cache = LRUCache[str](max_size=max_size, default_ttl=ttl)
    
    @staticmethod
    def _generate_key(analysis: dict) -> str:
        """Generate cache key from analysis."""
        key_data = json.dumps(analysis, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    async def get_prompt(self, analysis: dict) -> Optional[str]:
        """Get cached prompt."""
        key = self._generate_key(analysis)
        return await self._cache.get(key)
    
    async def store_prompt(self, analysis: dict, prompt: str, ttl: Optional[int] = None) -> None:
        """Store prompt in cache."""
        key = self._generate_key(analysis)
        await self._cache.set(key, prompt, ttl)


# Global cache instances
explanation_cache = ExplanationCache()
prompt_cache = PromptCache()


def cached_explanation(ttl: int = 3600):
    """Decorator for caching explanation results."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Extract cache key parameters from kwargs or args
            analysis = kwargs.get('analysis', args[1] if len(args) > 1 else {})
            
            concept = analysis.get('confusion_concept', '')
            subject = analysis.get('subject', 'general')
            difficulty = analysis.get('difficulty_level', 'intermediate')
            style = kwargs.get('style', 'schematic')
            
            # Check cache
            cached = await explanation_cache.get_explanation(
                concept, subject, difficulty, style
            )
            if cached:
                logger.info(f"Cache hit for explanation: {concept}")
                return cached
            
            # Generate new explanation
            result = await func(*args, **kwargs)
            
            # Store in cache
            await explanation_cache.store_explanation(
                concept, subject, result, difficulty, style, ttl
            )
            
            return result
        return wrapper
    return decorator

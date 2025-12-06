"""
Rate limiting middleware for Visual Tutor App.

Provides token bucket and sliding window rate limiting strategies
with per-client and global rate limiting capabilities.
"""

import asyncio
import time
import hashlib
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps
import logging

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .exceptions import RateLimitError


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    window_size_seconds: int = 60
    enable_global_limit: bool = True
    global_requests_per_minute: int = 1000


@dataclass 
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)
    refill_rate: float = 1.0  # tokens per second
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
        
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        
        # Refill tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_tokens(self, tokens: int = 1) -> float:
        """Calculate time until tokens are available."""
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.refill_rate


@dataclass
class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    window_size: int  # in seconds
    max_requests: int
    requests: list[float] = field(default_factory=list)
    
    def record_request(self) -> bool:
        """
        Record a request and check if rate limit exceeded.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_size
        
        # Remove old requests outside the window
        self.requests = [t for t in self.requests if t > window_start]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True
    
    def time_until_slot(self) -> float:
        """Calculate time until a slot opens up."""
        if len(self.requests) < self.max_requests:
            return 0
        
        now = time.time()
        window_start = now - self.window_size
        
        # Find oldest request that's still in window
        oldest_in_window = min(t for t in self.requests if t > window_start)
        return oldest_in_window + self.window_size - now


class RateLimiter:
    """
    Comprehensive rate limiter supporting multiple strategies.
    
    Features:
    - Per-client rate limiting
    - Global rate limiting
    - Token bucket for burst handling
    - Sliding window for sustained rate limiting
    - Automatic cleanup of stale entries
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        
        # Per-client rate limiters
        self._token_buckets: dict[str, TokenBucket] = {}
        self._sliding_windows: dict[str, SlidingWindowCounter] = {}
        
        # Global rate limiter
        self._global_bucket: Optional[TokenBucket] = None
        if self.config.enable_global_limit:
            self._global_bucket = TokenBucket(
                capacity=self.config.global_requests_per_minute,
                refill_rate=self.config.global_requests_per_minute / 60.0
            )
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Statistics
        self._total_requests = 0
        self._rate_limited_requests = 0
        self._clients_seen: set[str] = set()
    
    def _get_client_key(self, request: Request) -> str:
        """Extract a unique client identifier from the request."""
        # Try to get real IP from forwarded headers
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user agent for additional differentiation
        user_agent = request.headers.get("user-agent", "")
        
        # Create a hash for privacy
        key_data = f"{client_ip}:{user_agent[:50]}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _get_or_create_bucket(self, client_key: str) -> TokenBucket:
        """Get or create a token bucket for a client."""
        if client_key not in self._token_buckets:
            self._token_buckets[client_key] = TokenBucket(
                capacity=self.config.burst_size,
                refill_rate=self.config.requests_per_minute / 60.0
            )
        return self._token_buckets[client_key]
    
    def _get_or_create_window(self, client_key: str) -> SlidingWindowCounter:
        """Get or create a sliding window counter for a client."""
        if client_key not in self._sliding_windows:
            self._sliding_windows[client_key] = SlidingWindowCounter(
                window_size=self.config.window_size_seconds,
                max_requests=self.config.requests_per_minute
            )
        return self._sliding_windows[client_key]
    
    async def check_rate_limit(
        self,
        request: Request,
        cost: int = 1
    ) -> tuple[bool, Optional[float]]:
        """
        Check if a request should be rate limited.
        
        Args:
            request: The incoming request
            cost: The cost of this request in tokens
            
        Returns:
            Tuple of (allowed: bool, retry_after: Optional[float])
        """
        async with self._lock:
            self._total_requests += 1
            
            client_key = self._get_client_key(request)
            self._clients_seen.add(client_key)
            
            # Check global rate limit first
            if self._global_bucket and not self._global_bucket.consume(cost):
                self._rate_limited_requests += 1
                retry_after = self._global_bucket.time_until_tokens(cost)
                logger.warning(
                    f"Global rate limit exceeded",
                    extra={"retry_after": retry_after}
                )
                return False, retry_after
            
            # Check per-client token bucket (burst control)
            bucket = self._get_or_create_bucket(client_key)
            if not bucket.consume(cost):
                self._rate_limited_requests += 1
                retry_after = bucket.time_until_tokens(cost)
                logger.warning(
                    f"Client rate limit exceeded (burst)",
                    extra={"client_key": client_key[:8], "retry_after": retry_after}
                )
                return False, retry_after
            
            # Check per-client sliding window (sustained rate)
            window = self._get_or_create_window(client_key)
            if not window.record_request():
                self._rate_limited_requests += 1
                retry_after = window.time_until_slot()
                logger.warning(
                    f"Client rate limit exceeded (sustained)",
                    extra={"client_key": client_key[:8], "retry_after": retry_after}
                )
                return False, retry_after
            
            return True, None
    
    async def cleanup_stale_entries(self, max_age_seconds: int = 3600):
        """Remove stale rate limiter entries."""
        async with self._lock:
            now = time.time()
            stale_threshold = now - max_age_seconds
            
            # Clean up token buckets
            stale_buckets = [
                key for key, bucket in self._token_buckets.items()
                if bucket.last_update < stale_threshold
            ]
            for key in stale_buckets:
                del self._token_buckets[key]
            
            # Clean up sliding windows with empty request lists
            empty_windows = [
                key for key, window in self._sliding_windows.items()
                if not window.requests or max(window.requests) < stale_threshold
            ]
            for key in empty_windows:
                del self._sliding_windows[key]
            
            logger.info(
                f"Cleaned up rate limiter entries",
                extra={
                    "removed_buckets": len(stale_buckets),
                    "removed_windows": len(empty_windows)
                }
            )
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "rate_limited_requests": self._rate_limited_requests,
            "rate_limit_percentage": (
                self._rate_limited_requests / self._total_requests * 100
                if self._total_requests > 0 else 0
            ),
            "unique_clients": len(self._clients_seen),
            "active_buckets": len(self._token_buckets),
            "active_windows": len(self._sliding_windows),
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "burst_size": self.config.burst_size,
                "global_limit_enabled": self.config.enable_global_limit
            }
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Applies rate limiting to all incoming requests with configurable
    exclusions for health checks and static files.
    """
    
    def __init__(
        self,
        app,
        limiter: Optional[RateLimiter] = None,
        exclude_paths: Optional[list[str]] = None,
        cost_by_path: Optional[dict[str, int]] = None
    ):
        """
        Initialize the middleware.
        
        Args:
            app: The FastAPI application
            limiter: Rate limiter instance (uses global if not provided)
            exclude_paths: Paths to exclude from rate limiting
            cost_by_path: Custom costs for specific paths
        """
        super().__init__(app)
        self.limiter = limiter or rate_limiter
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.cost_by_path = cost_by_path or {
            "/api/v1/snap-and-explain": 5,  # Higher cost for generation
            "/api/v1/live-lens": 2,  # Moderate cost for live mode
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process the request with rate limiting."""
        path = request.url.path
        
        # Skip rate limiting for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Determine request cost
        cost = self.cost_by_path.get(path, 1)
        
        # Check rate limit
        allowed, retry_after = await self.limiter.check_rate_limit(request, cost)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(int(retry_after or 60))}
            )
        
        return await call_next(request)


def rate_limit(
    cost: int = 1,
    limiter: Optional[RateLimiter] = None
):
    """
    Decorator for rate limiting specific endpoints.
    
    Args:
        cost: Token cost for this endpoint
        limiter: Rate limiter instance (uses global if not provided)
    """
    _limiter = limiter or rate_limiter
    
    def decorator(func: Callable[..., Awaitable]):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            if request:
                allowed, retry_after = await _limiter.check_rate_limit(request, cost)
                if not allowed:
                    raise RateLimitError(
                        message="Rate limit exceeded",
                        retry_after=int(retry_after or 60)
                    )
            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator


async def cleanup_rate_limiters():
    """Background task to periodically clean up rate limiters."""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        await rate_limiter.cleanup_stale_entries()

"""
ENTERPRISE RATE LIMITER
Protects against brute force, DoS, and abuse
"""
from fastapi import HTTPException, status, Request
from functools import wraps
from typing import Callable
import time
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter
    For production, use Redis for distributed rate limiting
    """
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = {}
    
    def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """Check if request should be rate limited"""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        # Check if exceeded limit
        if len(self.requests[key]) >= max_requests:
            return True
        
        # Add current request
        self.requests[key].append(current_time)
        return False
    
    def block_ip(self, ip: str, duration_seconds: int = 3600):
        """Block IP address temporarily"""
        self.blocked_ips[ip] = time.time() + duration_seconds
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """
    Rate limit decorator
    
    Usage:
        @rate_limit(max_requests=10, window_seconds=60)
        async def endpoint():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Try to get from kwargs
                request = kwargs.get('request')
            
            if request:
                # Get client IP
                client_ip = request.client.host
                
                # Check if IP is blocked
                if rate_limiter.is_blocked(client_ip):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your IP has been temporarily blocked due to suspicious activity"
                    )
                
                # Check rate limit
                rate_limit_key = f"{func.__name__}:{client_ip}"
                
                if rate_limiter.is_rate_limited(rate_limit_key, max_requests, window_seconds):
                    logger.warning(f"Rate limit exceeded for {client_ip} on {func.__name__}")
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many requests. Try again in {window_seconds} seconds."
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class RedisRateLimiter:
    """
    Redis-based rate limiter for production
    Supports distributed rate limiting across multiple servers
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """Check rate limit using Redis"""
        current = int(time.time())
        window_start = current - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old requests
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {current: current})
        
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        request_count = results[1]
        
        return request_count >= max_requests

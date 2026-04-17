"""
FastAPI middleware for request tracking, timing, and authentication.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.core.security import extract_api_key_prefix
from app.repositories.tenant_repo import TenantRepository
from app.db.session import get_async_session


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Add request timing information."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Extract API key from header and attach to request state."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            request.state.api_key = api_key
            # Extract prefix for display
            request.state.api_key_prefix = extract_api_key_prefix(api_key)
        
        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""
    
    def __init__(self, app, redis_client, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.redis_client = redis_client
        self.calls = calls
        self.period = period
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get API key for rate limiting
        api_key = getattr(request.state, "api_key", None)
        if not api_key:
            return await call_next(request)
        
        # Check rate limit
        from app.core.security import hash_api_key
        api_key_hash = hash_api_key(api_key)
        
        current_time = int(time.time())
        window_start = current_time - self.period
        
        # Use Redis sorted set for sliding window
        await self.redis_client.zremrangebyscore(
            f"ratelimit:{api_key_hash}", 0, window_start
        )
        
        current_calls = await self.redis_client.zcard(f"ratelimit:{api_key_hash}")
        
        if current_calls >= self.calls:
            response = Response(
                content={"error": "Rate limit exceeded"},
                status_code=429
            )
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(window_start + self.period)
            return response
        
        # Add current request to rate limit
        await self.redis_client.zadd(
            f"ratelimit:{api_key_hash}",
            {str(current_time): current_time}
        )
        await self.redis_client.expire(f"ratelimit:{api_key_hash}", self.period)
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - current_calls - 1)
        response.headers["X-RateLimit-Reset"] = str(window_start + self.period)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured logging middleware."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        request_id = getattr(request.state, "request_id", "unknown")
        api_key_prefix = getattr(request.state, "api_key_prefix", "anonymous")
        
        # Log request
        import logging
        logger = logging.getLogger("api")
        logger.info(
            "API Request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "status_code": response.status_code,
                "process_time": f"{process_time:.4f}",
                "api_key_prefix": api_key_prefix,
                "user_agent": request.headers.get("User-Agent"),
                "content_length": len(response.body) if hasattr(response, 'body') else 0
            }
        )
        
        return response

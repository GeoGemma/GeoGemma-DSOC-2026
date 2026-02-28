import time
import json
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    Uses an in-memory data structure to track requests by IP.
    
    For production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(self, app, requests_per_minute=60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_timestamps = defaultdict(list)
        logger.info(f"Rate limit middleware initialized: {requests_per_minute} requests per minute")

    async def dispatch(self, request: Request, call_next):
        # Get client IP, with handling for proxies
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean up old timestamps (older than 60 seconds)
        self.request_timestamps[client_ip] = [
            timestamp for timestamp in self.request_timestamps[client_ip]
            if current_time - timestamp < 60
        ]
        
        # Check if too many requests
        if len(self.request_timestamps[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content=json.dumps({
                    "error": "Too many requests",
                    "message": "Rate limit exceeded. Please try again in a moment."
                }),
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
        
        # Record the current request timestamp
        self.request_timestamps[client_ip].append(current_time)
        
        # Process the request
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get the client IP address, handling proxies.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Return the first IP in the list (client IP)
            return forwarded.split(",")[0].strip()
        
        # Fall back to the client's direct IP
        return request.client.host 
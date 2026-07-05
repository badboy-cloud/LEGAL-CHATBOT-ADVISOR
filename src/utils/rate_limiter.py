import os
import time
from fastapi import Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

class RateLimiter:
    def __init__(self):
        # Read rate limit from env, default to 20 requests per minute
        self.rpm = int(os.getenv("RATE_LIMIT_RPM", "20"))
        # Memory storage: {ip_or_user: [timestamps]}
        self.requests = {}

    def is_rate_limited(self, request: Request, identifier: str = None) -> bool:
        """
        Enforce requests per minute limit.
        """
        # If no custom identifier is passed, fall back to client IP
        if not identifier:
            identifier = request.client.host if request.client else "unknown"

        now = time.time()
        
        # Initialize list for this identifier if not exists
        if identifier not in self.requests:
            self.requests[identifier] = []

        # Filter out timestamps older than 60 seconds
        self.requests[identifier] = [t for t in self.requests[identifier] if now - t < 60]

        # Check limit
        if len(self.requests[identifier]) >= self.rpm:
            return True

        # Log new request timestamp
        self.requests[identifier].append(now)
        return False

# Global instance of rate limiter
limiter = RateLimiter()

def check_rate_limit(request: Request):
    """
    FastAPI Dependency to check rate limits before processing requests.
    """
    # Try to identify by user id if already authenticated (would be attached to state),
    # otherwise default to client IP
    user_id = getattr(request.state, "user_id", None)
    identifier = f"user_{user_id}" if user_id else None
    
    if limiter.is_rate_limited(request, identifier):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 20 requests per minute allowed."
        )

import time
import threading
from fastapi import Request, HTTPException
from collections import defaultdict

class RateLimiter:
    """A thread-safe sliding-window rate limiter for FastAPI endpoints."""
    
    def __init__(self, requests_limit: int = 10, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history = defaultdict(list)
        self.lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        with self.lock:
            # Clean up timestamps older than the sliding window
            self.history[client_ip] = [t for t in self.history[client_ip] if now - t < self.window_seconds]
            
            if len(self.history[client_ip]) >= self.requests_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {self.requests_limit} requests per {self.window_seconds} seconds. Please try again later."
                )
            
            self.history[client_ip].append(now)

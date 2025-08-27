"""HTTP request logging middleware."""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...config.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""
    
    def __init__(self, app, log_request_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        
        # Log request start (INFO level for API access)
        if path.startswith("/api/"):
            logger.info(f"{method} {path} start - Client: {client_ip}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Log response (INFO level for API responses)
            if path.startswith("/api/"):
                status_code = response.status_code
                logger.info(f"{method} {path} end - {status_code} - {process_time:.3f}s")
                
                # DEBUG level: Log response details
                if logger.isEnabledFor(10):  # DEBUG level
                    content_length = response.headers.get("content-length", "unknown")
                    content_type = response.headers.get("content-type", "unknown")
                    logger.debug(f"Response details {path} - Size: {content_length}, Type: {content_type}")
            
            # Add response time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log errors
            process_time = time.time() - start_time
            logger.error(f"{method} {path} - ERROR - {process_time:.3f}s - {str(e)}")
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (for reverse proxy setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


def add_request_logging_middleware(app, log_request_body: bool = False):
    """Add request logging middleware to FastAPI app."""
    app.add_middleware(RequestLoggingMiddleware, log_request_body=log_request_body)
    logger.info("Request logging middleware added")

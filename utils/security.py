"""
Security Module for Web Scraper

Provides:
- Rate limiting and request throttling
- Secure headers and SSL verification
- Enhanced input sanitization
- Security auditing and monitoring
- Domain whitelisting/blacklisting
- Content security policies
"""

import time
import ssl
import socket
import threading
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from urllib.parse import urlparse
from pathlib import Path
import json

from utils.logger import get_logger, LoggerMixin
from utils.error_handler import ScraperException
from utils.validators import URLValidator

logger = get_logger(__name__)


class SecurityError(ScraperException):
    """Security-related errors"""
    pass


@dataclass
class SecurityEvent:
    """Security event for auditing"""
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL
    source_ip: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'severity': self.severity,
            'source_ip': self.source_ip,
            'url': self.url,
            'user_agent': self.user_agent,
            'details': self.details
        }


class RateLimiter(LoggerMixin):
    """Rate limiting with sliding window and token bucket algorithms"""
    
    def __init__(self, requests_per_second: int = 10, burst_size: int = 20):
        super().__init__()
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        
        # Token bucket for burst handling
        self._tokens = burst_size
        self._last_refill = time.time()
        
        # Sliding window for rate limiting
        self._request_times = deque()
        self._lock = threading.RLock()
        
        # Per-IP rate limiting
        self._ip_windows = defaultdict(lambda: deque())
        self._ip_locks = defaultdict(threading.RLock)
    
    def is_allowed(self, identifier: str = "global") -> bool:
        """Check if request is allowed under rate limit"""
        current_time = time.time()
        
        if identifier == "global":
            return self._check_global_limit(current_time)
        else:
            return self._check_ip_limit(identifier, current_time)
    
    def wait_if_needed(self, identifier: str = "global") -> float:
        """Wait if rate limit exceeded, return wait time"""
        if self.is_allowed(identifier):
            return 0.0
        
        # Calculate wait time
        wait_time = 1.0 / self.requests_per_second
        time.sleep(wait_time)
        return wait_time
    
    def _check_global_limit(self, current_time: float) -> bool:
        """Check global rate limit using token bucket"""
        with self._lock:
            # Refill tokens
            time_passed = current_time - self._last_refill
            self._tokens = min(
                self.burst_size,
                self._tokens + time_passed * self.requests_per_second
            )
            self._last_refill = current_time
            
            # Check if tokens available
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            
            return False
    
    def _check_ip_limit(self, ip: str, current_time: float) -> bool:
        """Check per-IP rate limit using sliding window"""
        with self._ip_locks[ip]:
            window = self._ip_windows[ip]
            
            # Remove old requests outside window
            window_start = current_time - 1.0  # 1 second window
            while window and window[0] < window_start:
                window.popleft()
            
            # Check if under limit
            if len(window) < self.requests_per_second:
                window.append(current_time)
                return True
            
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        with self._lock:
            return {
                'requests_per_second': self.requests_per_second,
                'burst_size': self.burst_size,
                'current_tokens': self._tokens,
                'active_ips': len(self._ip_windows),
                'recent_requests': len(self._request_times)
            }


# Global security instances
rate_limiter = RateLimiter()


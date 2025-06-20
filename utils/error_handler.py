"""
Comprehensive error handling utilities for the web scraper.
"""

import time
import logging
import traceback
from typing import Any, Callable, Optional, Dict, List
from functools import wraps
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ErrorInfo:
    """Structure to hold error information"""
    error_type: str
    message: str
    timestamp: datetime
    traceback: str
    context: Dict[str, Any]


class ScraperException(Exception):
    """Base exception for scraper-related errors"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now()


class CrawlException(ScraperException):
    """Exception for crawling-related errors"""
    pass


class AnalysisException(ScraperException):
    """Exception for analysis-related errors"""
    pass


class APIException(ScraperException):
    """Exception for API-related errors"""
    pass


class ValidationException(ScraperException):
    """Exception for validation errors"""
    pass


class ErrorHandler:
    """Centralized error handling with retry logic and error tracking"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.error_history: List[ErrorInfo] = []
        self.logger = logging.getLogger(__name__)
    
    def retry_with_exponential_backoff(
        self, 
        func: Callable, 
        *args, 
        exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry logic
        
        Args:
            func: Function to execute
            *args: Function arguments
            exceptions: Tuple of exceptions to catch and retry on
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    # Record final failure
                    self._record_error(e, {
                        'function': func.__name__,
                        'attempt': attempt + 1,
                        'max_retries': self.max_retries
                    })
                    raise e
                
                # Calculate wait time with exponential backoff
                wait_time = self.backoff_factor ** attempt
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                    f"Retrying in {wait_time:.2f} seconds..."
                )
                
                time.sleep(wait_time)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
    
    def safe_execute(
        self, 
        func: Callable, 
        *args, 
        default_return: Any = None,
        log_errors: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute function safely, returning default value on error
        
        Args:
            func: Function to execute
            *args: Function arguments
            default_return: Value to return on error
            log_errors: Whether to log errors
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_errors:
                self._record_error(e, {
                    'function': func.__name__,
                    'safe_execution': True
                })
            return default_return
    
    def _record_error(self, error: Exception, context: Dict[str, Any]):
        """Record error information for tracking and debugging"""
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            timestamp=datetime.now(),
            traceback=traceback.format_exc(),
            context=context
        )
        
        self.error_history.append(error_info)
        
        # Keep only last 100 errors to prevent memory issues
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        # Log the error
        self.logger.error(
            f"Error in {context.get('function', 'unknown')}: {error_info.message}",
            extra={'context': context}
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors"""
        if not self.error_history:
            return {'total_errors': 0, 'recent_errors': []}
        
        # Group errors by type
        error_counts = {}
        for error in self.error_history:
            error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
        
        # Get recent errors (last 10)
        recent_errors = [
            {
                'type': error.error_type,
                'message': error.message,
                'timestamp': error.timestamp.isoformat(),
                'context': error.context
            }
            for error in self.error_history[-10:]
        ]
        
        return {
            'total_errors': len(self.error_history),
            'error_counts': error_counts,
            'recent_errors': recent_errors
        }
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        self.logger.info("Error history cleared")


def handle_errors(
    exceptions: tuple = (Exception,),
    default_return: Any = None,
    log_errors: bool = True,
    max_retries: int = 0
):
    """
    Decorator for automatic error handling
    
    Args:
        exceptions: Tuple of exceptions to catch
        default_return: Value to return on error
        log_errors: Whether to log errors
        max_retries: Number of retries (0 = no retries)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler(max_retries=max_retries)
            
            if max_retries > 0:
                return error_handler.retry_with_exponential_backoff(
                    func, *args, exceptions=exceptions, **kwargs
                )
            else:
                # For safe execution, we need to only catch specified exceptions
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if log_errors:
                        error_handler._record_error(e, {
                            'function': func.__name__,
                            'safe_execution': True
                        })
                    return default_return
        
        return wrapper
    return decorator


# Global error handler instance
global_error_handler = ErrorHandler() 
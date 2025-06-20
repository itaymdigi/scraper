"""
Unit tests for error handling utilities.
"""

import pytest
import time
from unittest.mock import Mock, patch
from utils.error_handler import (
    ErrorHandler, ScraperException, CrawlException, 
    AnalysisException, APIException, ValidationException,
    handle_errors, global_error_handler
)


class TestCustomExceptions:
    """Test custom exception classes"""
    
    def test_scraper_exception(self):
        """Test ScraperException base class"""
        context = {"operation": "test", "data": "test_data"}
        exception = ScraperException("Test error", context)
        
        assert str(exception) == "Test error"
        assert exception.message == "Test error"
        assert exception.context == context
        assert exception.timestamp is not None
    
    def test_specific_exceptions(self):
        """Test specific exception subclasses"""
        crawl_ex = CrawlException("Crawl failed")
        analysis_ex = AnalysisException("Analysis failed")
        api_ex = APIException("API failed")
        validation_ex = ValidationException("Validation failed")
        
        assert isinstance(crawl_ex, ScraperException)
        assert isinstance(analysis_ex, ScraperException)
        assert isinstance(api_ex, ScraperException)
        assert isinstance(validation_ex, ScraperException)


class TestErrorHandler:
    """Test ErrorHandler class functionality"""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization"""
        handler = ErrorHandler(max_retries=5, backoff_factor=1.5)
        
        assert handler.max_retries == 5
        assert handler.backoff_factor == 1.5
        assert len(handler.error_history) == 0
    
    def test_retry_with_exponential_backoff_success(self):
        """Test successful execution with retry logic"""
        handler = ErrorHandler(max_retries=3)
        
        def successful_function():
            return "success"
        
        result = handler.retry_with_exponential_backoff(successful_function)
        assert result == "success"
    
    def test_retry_with_exponential_backoff_eventual_success(self):
        """Test eventual success after retries"""
        handler = ErrorHandler(max_retries=3, backoff_factor=0.1)  # Fast backoff for testing
        
        call_count = 0
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = handler.retry_with_exponential_backoff(
            eventually_successful_function,
            exceptions=(ValueError,)
        )
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_exponential_backoff_final_failure(self):
        """Test final failure after all retries"""
        handler = ErrorHandler(max_retries=2, backoff_factor=0.1)
        
        def always_failing_function():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            handler.retry_with_exponential_backoff(
                always_failing_function,
                exceptions=(ValueError,)
            )
        
        # Check that error was recorded
        assert len(handler.error_history) == 1
        assert handler.error_history[0].error_type == "ValueError"
    
    def test_safe_execute_success(self):
        """Test safe execution with successful function"""
        handler = ErrorHandler()
        
        def successful_function():
            return "success"
        
        result = handler.safe_execute(successful_function)
        assert result == "success"
    
    def test_safe_execute_with_error(self):
        """Test safe execution with failing function"""
        handler = ErrorHandler()
        
        def failing_function():
            raise ValueError("Test error")
        
        result = handler.safe_execute(
            failing_function,
            default_return="default"
        )
        assert result == "default"
        assert len(handler.error_history) == 1
    
    def test_error_summary(self):
        """Test error summary generation"""
        handler = ErrorHandler()
        
        # Generate some errors
        handler._record_error(ValueError("Error 1"), {"test": 1})
        handler._record_error(TypeError("Error 2"), {"test": 2})
        handler._record_error(ValueError("Error 3"), {"test": 3})
        
        summary = handler.get_error_summary()
        
        assert summary["total_errors"] == 3
        assert summary["error_counts"]["ValueError"] == 2
        assert summary["error_counts"]["TypeError"] == 1
        assert len(summary["recent_errors"]) == 3
    
    def test_clear_error_history(self):
        """Test clearing error history"""
        handler = ErrorHandler()
        
        # Add some errors
        handler._record_error(ValueError("Test"), {})
        assert len(handler.error_history) == 1
        
        # Clear history
        handler.clear_error_history()
        assert len(handler.error_history) == 0
    
    def test_error_history_limit(self):
        """Test error history size limit"""
        handler = ErrorHandler()
        
        # Add more than 100 errors
        for i in range(150):
            handler._record_error(ValueError(f"Error {i}"), {"index": i})
        
        # Should be limited to 100
        assert len(handler.error_history) == 100
        # Should keep the most recent ones
        assert handler.error_history[-1].context["index"] == 149


class TestHandleErrorsDecorator:
    """Test the handle_errors decorator"""
    
    def test_decorator_success(self):
        """Test decorator with successful function"""
        @handle_errors()
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_decorator_with_error_and_default(self):
        """Test decorator with error and default return"""
        @handle_errors(default_return="default")
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result == "default"
    
    def test_decorator_with_retries(self):
        """Test decorator with retry logic"""
        call_count = 0
        
        @handle_errors(max_retries=2, exceptions=(ValueError,))
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        result = eventually_successful_function()
        assert result == "success"
        assert call_count == 2
    
    def test_decorator_specific_exceptions(self):
        """Test decorator with specific exception handling"""
        @handle_errors(exceptions=(ValueError,), default_return="handled")
        def function_with_specific_error():
            raise ValueError("Specific error")
        
        @handle_errors(exceptions=(ValueError,), default_return="handled")
        def function_with_other_error():
            raise TypeError("Other error")
        
        # ValueError should be handled
        result1 = function_with_specific_error()
        assert result1 == "handled"
        
        # TypeError should not be handled (will raise)
        with pytest.raises(TypeError):
            function_with_other_error()


class TestGlobalErrorHandler:
    """Test global error handler instance"""
    
    def test_global_error_handler_exists(self):
        """Test that global error handler exists"""
        assert global_error_handler is not None
        assert isinstance(global_error_handler, ErrorHandler)
    
    def test_global_error_handler_usage(self):
        """Test using global error handler"""
        def test_function():
            return "test_result"
        
        result = global_error_handler.safe_execute(test_function)
        assert result == "test_result"


class TestErrorContextRecording:
    """Test error context recording functionality"""
    
    def test_error_context_recording(self):
        """Test that error context is properly recorded"""
        handler = ErrorHandler()
        
        context = {
            "operation": "test_operation",
            "url": "https://example.com",
            "parameters": {"depth": 2, "max_pages": 10}
        }
        
        error = ValueError("Test error with context")
        handler._record_error(error, context)
        
        assert len(handler.error_history) == 1
        recorded_error = handler.error_history[0]
        
        assert recorded_error.error_type == "ValueError"
        assert recorded_error.message == "Test error with context"
        assert recorded_error.context == context
        assert recorded_error.timestamp is not None
        assert recorded_error.traceback is not None
    
    def test_error_info_structure(self):
        """Test ErrorInfo dataclass structure"""
        handler = ErrorHandler()
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            handler._record_error(e, {"test": "context"})
        
        error_info = handler.error_history[0]
        
        # Check all required fields are present
        assert hasattr(error_info, 'error_type')
        assert hasattr(error_info, 'message')
        assert hasattr(error_info, 'timestamp')
        assert hasattr(error_info, 'traceback')
        assert hasattr(error_info, 'context')
        
        # Check field values
        assert error_info.error_type == "ValueError"
        assert error_info.message == "Test error"
        assert error_info.context == {"test": "context"}
        assert "ValueError: Test error" in error_info.traceback 
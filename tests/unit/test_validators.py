"""
Unit tests for validation utilities.
"""

import pytest
from utils.validators import (
    URLValidator, InputSanitizer, ParameterValidator,
    ValidationResult, validate_and_sanitize_input
)


class TestURLValidator:
    """Test URL validation functionality"""
    
    def test_valid_urls(self, valid_urls):
        """Test validation of valid URLs"""
        for url in valid_urls:
            result = URLValidator.validate_url(url)
            assert result.is_valid, f"URL {url} should be valid"
            assert result.value is not None
            assert len(result.errors) == 0
    
    def test_invalid_urls(self, invalid_urls):
        """Test validation of invalid URLs"""
        for url in invalid_urls:
            result = URLValidator.validate_url(url)
            assert not result.is_valid, f"URL {url} should be invalid"
            assert len(result.errors) > 0
    
    def test_dangerous_patterns(self):
        """Test detection of dangerous URL patterns"""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')"
        ]
        
        for url in dangerous_urls:
            result = URLValidator.validate_url(url)
            assert not result.is_valid
            assert any("dangerous" in error.lower() for error in result.errors)
    
    def test_malicious_patterns(self):
        """Test detection of malicious patterns"""
        malicious_urls = [
            "https://example.com/<script>alert('xss')</script>",
            "https://example.com/?param=javascript:alert('xss')"
        ]
        
        for url in malicious_urls:
            result = URLValidator.validate_url(url)
            assert not result.is_valid
            assert any("malicious" in error.lower() for error in result.errors)
    
    def test_localhost_detection(self):
        """Test localhost and private IP detection"""
        localhost_urls = [
            "http://localhost",
            "http://127.0.0.1",
            "http://192.168.1.1",
            "http://10.0.0.1"
        ]
        
        for url in localhost_urls:
            result = URLValidator.validate_url(url, allow_localhost=False)
            assert result.is_valid  # Should be valid but with warnings
            assert any("localhost" in warning.lower() or "private" in warning.lower() 
                      for warning in result.warnings)
    
    def test_domain_list_validation(self):
        """Test domain list validation"""
        valid_domains = "example.com\ntest.org\nsubdomain.example.com"
        result = URLValidator.validate_domain_list(valid_domains)
        
        assert result.is_valid
        assert len(result.value) == 3
        assert "example.com" in result.value
        
        # Test invalid domains
        invalid_domains = "invalid..domain\n-invalid.com\n"
        result = URLValidator.validate_domain_list(invalid_domains)
        
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_url_sanitization(self):
        """Test URL sanitization"""
        test_url = "HTTPS://EXAMPLE.COM/PATH WITH SPACES#fragment"
        result = URLValidator.validate_url(test_url)
        
        assert result.is_valid
        assert result.value.startswith("https://example.com")
        assert "#fragment" not in result.value  # Fragment should be removed


class TestInputSanitizer:
    """Test input sanitization functionality"""
    
    def test_string_sanitization(self):
        """Test string sanitization"""
        # Test normal string
        result = InputSanitizer.sanitize_string("Hello World")
        assert result == "Hello World"
        
        # Test string with HTML
        html_string = "<script>alert('xss')</script>Hello"
        result = InputSanitizer.sanitize_string(html_string, allow_html=False)
        assert "<script>" not in result
        assert "Hello" in result
        
        # Test length limiting
        long_string = "a" * 2000
        result = InputSanitizer.sanitize_string(long_string, max_length=100)
        assert len(result) <= 100
        
        # Test control character removal
        control_string = "Hello\x00\x01World"
        result = InputSanitizer.sanitize_string(control_string)
        assert result == "HelloWorld"
    
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        # Test dangerous characters
        dangerous_filename = "file<>:\"/\\|?*.txt"
        result = InputSanitizer.sanitize_filename(dangerous_filename)
        assert not any(char in result for char in '<>:"/\\|?*')
        
        # Test empty filename
        result = InputSanitizer.sanitize_filename("")
        assert result == "untitled"
        
        # Test very long filename
        long_filename = "a" * 300 + ".txt"
        result = InputSanitizer.sanitize_filename(long_filename)
        assert len(result) <= 255
        assert result.endswith(".txt")


class TestParameterValidator:
    """Test parameter validation functionality"""
    
    def test_crawl_params_validation(self):
        """Test crawl parameters validation"""
        valid_params = {
            'url': 'https://example.com',
            'depth': 2,
            'max_pages': 50,
            'timeout': 30,
            'max_workers': 10,
            'user_agent': 'Mozilla/5.0 Test Agent'
        }
        
        result = ParameterValidator.validate_crawl_params(**valid_params)
        assert result.is_valid
        assert len(result.errors) == 0
        
        # Test invalid parameters
        invalid_params = {
            'url': 'not-a-url',
            'depth': 0,  # Too low
            'max_pages': 2000,  # Too high
            'timeout': 1,  # Too low
            'max_workers': 100,  # Too high
            'user_agent': 'short'  # Too short
        }
        
        result = ParameterValidator.validate_crawl_params(**invalid_params)
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_ai_params_validation(self):
        """Test AI parameters validation"""
        valid_params = {
            'api_key': 'sk-1234567890abcdef',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        result = ParameterValidator.validate_ai_params(**valid_params)
        assert result.is_valid
        
        # Test invalid parameters
        invalid_params = {
            'api_key': 'short',  # Too short
            'temperature': 3.0,  # Too high
            'max_tokens': 50000  # Too high
        }
        
        result = ParameterValidator.validate_ai_params(**invalid_params)
        assert not result.is_valid
        assert len(result.errors) > 0


class TestValidationDispatcher:
    """Test the validation dispatcher function"""
    
    def test_url_validation_dispatch(self):
        """Test URL validation through dispatcher"""
        result = validate_and_sanitize_input("https://example.com", "url")
        assert result.is_valid
        
        result = validate_and_sanitize_input("invalid-url", "url")
        assert not result.is_valid
    
    def test_unknown_validation_type(self):
        """Test handling of unknown validation types"""
        result = validate_and_sanitize_input("test", "unknown_type")
        assert not result.is_valid
        assert "Unknown validation type" in result.errors[0]
    
    def test_validation_exception_handling(self):
        """Test exception handling in validation"""
        # This should trigger an exception due to missing parameters
        result = validate_and_sanitize_input(None, "crawl_params")
        assert not result.is_valid
        assert len(result.errors) > 0


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and properties"""
        result = ValidationResult(
            is_valid=True,
            value="test_value",
            errors=[],
            warnings=["warning1"]
        )
        
        assert result.is_valid is True
        assert result.value == "test_value"
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.warnings[0] == "warning1" 
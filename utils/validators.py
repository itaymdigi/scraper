"""
Input validation and sanitization utilities for the web scraper.
"""

import re
import html
from urllib.parse import urlparse, urlunparse, quote
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

from utils.error_handler import ValidationException
from utils.logger import get_logger

logger = get_logger("validators")


@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    value: Any
    errors: List[str]
    warnings: List[str]


class URLValidator:
    """Comprehensive URL validation and sanitization"""
    
    # Dangerous URL patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'file:',
        r'ftp:',
        r'about:',
        r'chrome:',
        r'chrome-extension:',
        r'moz-extension:'
    ]
    
    # Valid URL schemes
    VALID_SCHEMES = ['http', 'https']
    
    # Common malicious patterns
    MALICIOUS_PATTERNS = [
        r'<script',
        r'javascript:',
        r'onload=',
        r'onerror=',
        r'onclick=',
        r'eval\(',
        r'document\.cookie',
        r'window\.location'
    ]
    
    @classmethod
    def validate_url(cls, url: str, allow_localhost: bool = False) -> ValidationResult:
        """
        Comprehensive URL validation
        
        Args:
            url: URL to validate
            allow_localhost: Whether to allow localhost URLs
            
        Returns:
            ValidationResult with validation status and sanitized URL
        """
        errors = []
        warnings = []
        
        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                value=None,
                errors=["URL must be a non-empty string"],
                warnings=[]
            )
        
        # Remove leading/trailing whitespace
        url = url.strip()
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                errors.append(f"Dangerous URL pattern detected: {pattern}")
        
        # Check for malicious patterns
        for pattern in cls.MALICIOUS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                errors.append(f"Potentially malicious pattern detected: {pattern}")
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            errors.append(f"Invalid URL format: {str(e)}")
            return ValidationResult(False, None, errors, warnings)
        
        # Validate scheme
        if parsed.scheme.lower() not in cls.VALID_SCHEMES:
            errors.append(f"Invalid URL scheme: {parsed.scheme}. Only {cls.VALID_SCHEMES} are allowed")
        
        # Validate netloc (domain)
        if not parsed.netloc:
            errors.append("URL must have a valid domain")
        
        # Check for localhost/private IPs if not allowed
        if not allow_localhost:
            if cls._is_localhost_or_private(parsed.netloc):
                warnings.append("URL points to localhost or private IP address")
        
        # Sanitize URL
        sanitized_url = cls._sanitize_url(parsed) if not errors else None
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            value=sanitized_url,
            errors=errors,
            warnings=warnings
        )
    
    @classmethod
    def _is_localhost_or_private(cls, netloc: str) -> bool:
        """Check if netloc is localhost or private IP"""
        localhost_patterns = [
            r'^localhost$',
            r'^127\.',
            r'^192\.168\.',
            r'^10\.',
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^::1$',
            r'^fc00:',
            r'^fe80:'
        ]
        
        for pattern in localhost_patterns:
            if re.match(pattern, netloc, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _sanitize_url(cls, parsed_url) -> str:
        """Sanitize URL components"""
        # Encode path properly
        path = quote(parsed_url.path.encode('utf-8'), safe='/:@!$&\'()*+,;=')
        
        # Reconstruct URL with sanitized components
        sanitized = urlunparse((
            parsed_url.scheme.lower(),
            parsed_url.netloc.lower(),
            path,
            parsed_url.params,
            parsed_url.query,
            ''  # Remove fragment for security
        ))
        
        return sanitized
    
    @classmethod
    def validate_domain_list(cls, domains_text: str) -> ValidationResult:
        """Validate a list of domains from text input"""
        errors = []
        warnings = []
        valid_domains = []
        
        if not domains_text:
            return ValidationResult(True, [], [], [])
        
        lines = domains_text.strip().split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Basic domain validation
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', line):
                errors.append(f"Line {i}: Invalid domain format: {line}")
                continue
            
            valid_domains.append(line.lower())
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            value=valid_domains,
            errors=errors,
            warnings=warnings
        )


class InputSanitizer:
    """General input sanitization utilities"""
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """
        Sanitize string input
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags
            
        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes and control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Input truncated to {max_length} characters")
        
        # HTML escape if HTML not allowed
        if not allow_html:
            text = html.escape(text)
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations"""
        if not isinstance(filename, str):
            return "untitled"
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure it's not empty
        if not filename:
            filename = "untitled"
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 255 - len(ext) - 1 if ext else 255
            filename = f"{name[:max_name_length]}.{ext}" if ext else name[:255]
        
        return filename


class ParameterValidator:
    """Validate crawler and analysis parameters"""
    
    @staticmethod
    def validate_crawl_params(
        url: str,
        depth: int,
        max_pages: int,
        timeout: int,
        max_workers: int,
        user_agent: str
    ) -> ValidationResult:
        """Validate crawling parameters"""
        errors = []
        warnings = []
        
        # Validate URL
        url_result = URLValidator.validate_url(url)
        if not url_result.is_valid:
            errors.extend([f"URL: {error}" for error in url_result.errors])
        
        # Validate depth
        if not isinstance(depth, int) or depth < 1 or depth > 10:
            errors.append("Depth must be an integer between 1 and 10")
        
        # Validate max_pages
        if not isinstance(max_pages, int) or max_pages < 1 or max_pages > 1000:
            errors.append("Max pages must be an integer between 1 and 1000")
        
        # Validate timeout
        if not isinstance(timeout, int) or timeout < 5 or timeout > 300:
            errors.append("Timeout must be an integer between 5 and 300 seconds")
        
        # Validate max_workers
        if not isinstance(max_workers, int) or max_workers < 1 or max_workers > 50:
            errors.append("Max workers must be an integer between 1 and 50")
        
        # Validate user_agent
        if not isinstance(user_agent, str) or len(user_agent.strip()) < 10:
            warnings.append("User agent should be a meaningful string")
        
        # Performance warnings
        if depth > 3 and max_pages > 100:
            warnings.append("High depth and page count may result in long crawl times")
        
        if max_workers > 20:
            warnings.append("High worker count may overwhelm target server")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            value={
                'url': url_result.value if url_result.is_valid else url,
                'depth': depth,
                'max_pages': max_pages,
                'timeout': timeout,
                'max_workers': max_workers,
                'user_agent': InputSanitizer.sanitize_string(user_agent, 500)
            },
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_ai_params(
        api_key: str,
        temperature: float,
        max_tokens: Optional[int] = None
    ) -> ValidationResult:
        """Validate AI API parameters"""
        errors = []
        warnings = []
        
        # Validate API key
        if not isinstance(api_key, str) or len(api_key.strip()) < 10:
            errors.append("API key must be a valid string")
        
        # Validate temperature
        if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
            errors.append("Temperature must be a number between 0 and 2")
        
        # Validate max_tokens
        if max_tokens is not None:
            if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 32000:
                errors.append("Max tokens must be an integer between 1 and 32000")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            value={
                'api_key': api_key.strip() if isinstance(api_key, str) else '',
                'temperature': float(temperature),
                'max_tokens': max_tokens
            },
            errors=errors,
            warnings=warnings
        )


def validate_and_sanitize_input(
    input_value: Any,
    input_type: str,
    **validation_kwargs
) -> ValidationResult:
    """
    General validation dispatcher
    
    Args:
        input_value: Value to validate
        input_type: Type of validation ('url', 'string', 'crawl_params', etc.)
        **validation_kwargs: Additional validation parameters
        
    Returns:
        ValidationResult
    """
    try:
        if input_type == 'url':
            return URLValidator.validate_url(input_value, **validation_kwargs)
        elif input_type == 'domain_list':
            return URLValidator.validate_domain_list(input_value)
        elif input_type == 'crawl_params':
            return ParameterValidator.validate_crawl_params(**input_value)
        elif input_type == 'ai_params':
            return ParameterValidator.validate_ai_params(**input_value)
        else:
            return ValidationResult(
                is_valid=False,
                value=None,
                errors=[f"Unknown validation type: {input_type}"],
                warnings=[]
            )
    except Exception as e:
        logger.error(f"Validation error for type {input_type}: {str(e)}")
        return ValidationResult(
            is_valid=False,
            value=None,
            errors=[f"Validation failed: {str(e)}"],
            warnings=[]
        ) 
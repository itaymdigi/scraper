"""
Pytest configuration and common fixtures for the scraper tests.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Add project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_html():
    """Sample HTML content for testing"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Page</title>
        <meta name="description" content="This is a test page for scraper testing">
    </head>
    <body>
        <header>
            <nav>
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/about">About</a></li>
                </ul>
            </nav>
        </header>
        <main>
            <h1>Welcome to Test Page</h1>
            <p>This is a paragraph with some text content.</p>
            <img src="/image.jpg" alt="Test image">
            <div class="content">
                <h2>Section Title</h2>
                <p>More content here.</p>
            </div>
        </main>
        <footer>
            <p>&copy; 2024 Test Site</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_crawl_result():
    """Sample crawl result for testing"""
    return [
        {
            "url": "https://example.com",
            "content": """
            <html>
                <head><title>Example</title></head>
                <body><h1>Hello World</h1><p>Test content</p></body>
            </html>
            """
        },
        {
            "url": "https://example.com/about",
            "content": """
            <html>
                <head><title>About - Example</title></head>
                <body><h1>About Us</h1><p>About content</p></body>
            </html>
            """
        }
    ]


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing"""
    session = MagicMock()
    response = MagicMock()
    response.status = 200
    response.text = asyncio.coroutine(lambda: "<html><body>Test</body></html>")()
    
    session.get.return_value.__aenter__ = asyncio.coroutine(lambda: response)
    session.get.return_value.__aexit__ = asyncio.coroutine(lambda *args: None)
    
    return session


@pytest.fixture
def temp_cache_dir():
    """Temporary directory for cache testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_deepseek_response():
    """Mock DeepSeek API response"""
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a mock AI response for testing purposes."
                }
            }
        ]
    }


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests"""
    import logging
    logging.getLogger().setLevel(logging.DEBUG)


@pytest.fixture
def valid_urls():
    """List of valid URLs for testing"""
    return [
        "https://example.com",
        "http://test.org",
        "https://subdomain.example.com/path",
        "https://example.com:8080/path?query=value"
    ]


@pytest.fixture
def invalid_urls():
    """List of invalid URLs for testing"""
    return [
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "not-a-url",
        "",
        None,
        "ftp://example.com",
        "file:///etc/passwd"
    ] 
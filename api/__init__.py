"""
API module for the web scraper.
Provides REST API endpoints using FastAPI.
"""

from .endpoints import create_app, get_app, start_server

__all__ = ['create_app', 'get_app', 'start_server'] 
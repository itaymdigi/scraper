"""
Structured logging utilities for the web scraper.
"""

import logging
import logging.handlers
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        # Create log entry dictionary
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra context if present
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
        
        # Add any other custom attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'context']:
                log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)


class ScraperLogger:
    """Centralized logging configuration for the scraper application"""
    
    def __init__(self, 
                 name: str = "scraper",
                 log_level: str = "INFO",
                 log_dir: str = "logs",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_json: bool = True):
        
        self.name = name
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        
        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize logger
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup and configure the logger with handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        
        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            
            console_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # File handler (rotating)
        if self.enable_file:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=self.log_dir / f"{self.name}.log",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        # JSON file handler for structured logs
        if self.enable_json:
            json_handler = logging.handlers.RotatingFileHandler(
                filename=self.log_dir / f"{self.name}_structured.json",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            json_handler.setLevel(self.log_level)
            json_handler.setFormatter(JSONFormatter())
            logger.addHandler(json_handler)
        
        return logger
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance"""
        if name:
            return logging.getLogger(f"{self.name}.{name}")
        return self.logger
    
    def log_crawl_start(self, url: str, depth: int, max_pages: int):
        """Log crawl operation start"""
        self.logger.info(
            f"Starting crawl operation",
            extra={
                'context': {
                    'operation': 'crawl_start',
                    'url': url,
                    'depth': depth,
                    'max_pages': max_pages
                }
            }
        )
    
    def log_crawl_complete(self, url: str, pages_crawled: int, duration: float):
        """Log crawl operation completion"""
        self.logger.info(
            f"Crawl operation completed",
            extra={
                'context': {
                    'operation': 'crawl_complete',
                    'url': url,
                    'pages_crawled': pages_crawled,
                    'duration_seconds': duration
                }
            }
        )
    
    def log_api_call(self, api_name: str, endpoint: str, status: str, duration: float):
        """Log API call details"""
        self.logger.info(
            f"API call to {api_name}",
            extra={
                'context': {
                    'operation': 'api_call',
                    'api_name': api_name,
                    'endpoint': endpoint,
                    'status': status,
                    'duration_seconds': duration
                }
            }
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        """Log error with additional context"""
        self.logger.error(
            f"Error occurred: {str(error)}",
            exc_info=True,
            extra={'context': context}
        )
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metrics"""
        self.logger.info(
            f"Performance metric: {metric_name}",
            extra={
                'context': {
                    'operation': 'performance_metric',
                    'metric_name': metric_name,
                    'value': value,
                    'unit': unit
                }
            }
        )


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for this class"""
        if self._logger is None:
            class_name = self.__class__.__name__
            self._logger = logging.getLogger(f"scraper.{class_name}")
        return self._logger
    
    def log_method_call(self, method_name: str, **kwargs):
        """Log method call with parameters"""
        self.logger.debug(
            f"Calling {method_name}",
            extra={
                'context': {
                    'operation': 'method_call',
                    'method': method_name,
                    'class': self.__class__.__name__,
                    'parameters': kwargs
                }
            }
        )
    
    def log_method_result(self, method_name: str, result_summary: str):
        """Log method result"""
        self.logger.debug(
            f"Method {method_name} completed",
            extra={
                'context': {
                    'operation': 'method_result',
                    'method': method_name,
                    'class': self.__class__.__name__,
                    'result': result_summary
                }
            }
        )


# Global logger instance
scraper_logger = ScraperLogger()

def get_logger(name: str = "") -> logging.Logger:
    """Get a logger instance"""
    return scraper_logger.get_logger(name)

def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """Setup logging configuration"""
    global scraper_logger
    scraper_logger = ScraperLogger(
        log_level=log_level,
        log_dir=log_dir
    )
    return scraper_logger.logger 
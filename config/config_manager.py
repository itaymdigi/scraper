"""
Enhanced Configuration Manager for Web Scraper

Provides centralized configuration management with:
- Environment variable support
- Configuration validation
- Multiple environment profiles
- Dynamic configuration updates
- Configuration file loading
"""

import os
import json
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from utils.logger import get_logger
from utils.error_handler import ScraperException

logger = get_logger(__name__)


class ConfigurationError(ScraperException):
    """Configuration-related errors"""
    pass


@dataclass
class CrawlerConfig:
    """Crawler-specific configuration"""
    max_depth: int = 3
    max_pages: int = 100
    delay_between_requests: float = 1.0
    concurrent_requests: int = 5
    timeout: int = 30
    user_agent: str = "ScraperBot/1.0"
    follow_redirects: bool = True
    respect_robots_txt: bool = True
    max_retries: int = 3
    retry_delay: float = 2.0


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    ttl: int = 3600  # 1 hour
    max_size: int = 1000
    cleanup_interval: int = 300  # 5 minutes
    storage_path: str = "cache"
    compression_enabled: bool = True


@dataclass
class APIConfig:
    """API configuration"""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class SecurityConfig:
    """Security configuration"""
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    enable_ssl_verification: bool = True
    max_redirects: int = 5


@dataclass
class PerformanceConfig:
    """Performance configuration"""
    enable_async: bool = True
    worker_threads: int = 4
    memory_limit_mb: int = 512
    cpu_limit_percent: int = 80
    enable_profiling: bool = False
    metrics_interval: int = 60


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file_enabled: bool = True
    console_enabled: bool = True
    structured_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class ConfigManager:
    """Enhanced configuration manager with environment support"""
    
    def __init__(self, config_file: Optional[str] = None, environment: str = "development"):
        self.environment = environment
        self.config_file = config_file
        self._config_data = {}
        self._watchers = []
        
        # Initialize configurations
        self.crawler = CrawlerConfig()
        self.cache = CacheConfig()
        self.api = APIConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.logging = LoggingConfig()
        
        # Load configuration
        self._load_configuration()
        logger.info(f"Configuration loaded for environment: {environment}")
    
    def _load_configuration(self):
        """Load configuration from multiple sources"""
        # 1. Load from file if specified
        if self.config_file:
            self._load_from_file(self.config_file)
        
        # 2. Load from environment-specific file
        env_config_file = f"config/{self.environment}.json"
        if os.path.exists(env_config_file):
            self._load_from_file(env_config_file)
        
        # 3. Load from environment variables
        self._load_from_env()
        
        # 4. Validate configuration
        self._validate_configuration()
    
    def _load_from_file(self, file_path: str):
        """Load configuration from JSON file"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Configuration file not found: {file_path}")
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._merge_config(data)
            logger.info(f"Loaded configuration from: {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {file_path}: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        env_mapping = {
            # Crawler config
            'SCRAPER_MAX_DEPTH': ('crawler', 'max_depth', int),
            'SCRAPER_MAX_PAGES': ('crawler', 'max_pages', int),
            'SCRAPER_DELAY': ('crawler', 'delay_between_requests', float),
            'SCRAPER_CONCURRENT': ('crawler', 'concurrent_requests', int),
            'SCRAPER_TIMEOUT': ('crawler', 'timeout', int),
            'SCRAPER_USER_AGENT': ('crawler', 'user_agent', str),
            
            # API config
            'DEEPSEEK_API_KEY': ('api', 'deepseek_api_key', str),
            'DEEPSEEK_BASE_URL': ('api', 'deepseek_base_url', str),
            'DEEPSEEK_MAX_TOKENS': ('api', 'max_tokens', int),
            'DEEPSEEK_TEMPERATURE': ('api', 'temperature', float),
            
            # Cache config
            'CACHE_ENABLED': ('cache', 'enabled', bool),
            'CACHE_TTL': ('cache', 'ttl', int),
            'CACHE_MAX_SIZE': ('cache', 'max_size', int),
            
            # Security config
            'RATE_LIMIT_REQUESTS': ('security', 'rate_limit_requests', int),
            'RATE_LIMIT_WINDOW': ('security', 'rate_limit_window', int),
            'MAX_FILE_SIZE': ('security', 'max_file_size', int),
            
            # Performance config
            'ENABLE_ASYNC': ('performance', 'enable_async', bool),
            'WORKER_THREADS': ('performance', 'worker_threads', int),
            'MEMORY_LIMIT_MB': ('performance', 'memory_limit_mb', int),
            
            # Logging config
            'LOG_LEVEL': ('logging', 'level', str),
            'LOG_FILE_ENABLED': ('logging', 'file_enabled', bool),
        }
        
        for env_var, (section, key, type_func) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # Convert boolean strings
                    if type_func == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        value = type_func(value)
                    
                    setattr(getattr(self, section), key, value)
                    logger.debug(f"Set {section}.{key} = {value} from env var {env_var}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {value} ({e})")
    
    def _merge_config(self, data: Dict[str, Any]):
        """Merge configuration data into existing config"""
        for section, values in data.items():
            if hasattr(self, section) and isinstance(values, dict):
                config_obj = getattr(self, section)
                for key, value in values.items():
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
                        logger.debug(f"Set {section}.{key} = {value}")
    
    def _validate_configuration(self):
        """Validate configuration values"""
        errors = []
        
        # Validate crawler config
        if self.crawler.max_depth < 1:
            errors.append("crawler.max_depth must be >= 1")
        if self.crawler.max_pages < 1:
            errors.append("crawler.max_pages must be >= 1")
        if self.crawler.delay_between_requests < 0:
            errors.append("crawler.delay_between_requests must be >= 0")
        if self.crawler.concurrent_requests < 1:
            errors.append("crawler.concurrent_requests must be >= 1")
        
        # Validate API config
        if not self.api.deepseek_api_key and self.environment != "test":
            logger.warning("api.deepseek_api_key is not set")
        if self.api.max_tokens < 1:
            errors.append("api.max_tokens must be >= 1")
        if not (0 <= self.api.temperature <= 2):
            errors.append("api.temperature must be between 0 and 2")
        
        # Validate cache config
        if self.cache.ttl < 0:
            errors.append("cache.ttl must be >= 0")
        if self.cache.max_size < 1:
            errors.append("cache.max_size must be >= 1")
        
        # Validate security config
        if self.security.rate_limit_requests < 1:
            errors.append("security.rate_limit_requests must be >= 1")
        if self.security.rate_limit_window < 1:
            errors.append("security.rate_limit_window must be >= 1")
        
        # Validate performance config
        if self.performance.worker_threads < 1:
            errors.append("performance.worker_threads must be >= 1")
        if self.performance.memory_limit_mb < 1:
            errors.append("performance.memory_limit_mb must be >= 1")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        try:
            parts = key.split('.')
            obj = self
            for part in parts:
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        parts = key.split('.')
        if len(parts) < 2:
            raise ConfigurationError(f"Invalid config key format: {key}")
        
        section = parts[0]
        attr = parts[1]
        
        if not hasattr(self, section):
            raise ConfigurationError(f"Unknown config section: {section}")
        
        config_obj = getattr(self, section)
        if not hasattr(config_obj, attr):
            raise ConfigurationError(f"Unknown config attribute: {section}.{attr}")
        
        setattr(config_obj, attr, value)
        logger.info(f"Updated config: {key} = {value}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'crawler': self.crawler.__dict__,
            'cache': self.cache.__dict__,
            'api': self.api.__dict__,
            'security': self.security.__dict__,
            'performance': self.performance.__dict__,
            'logging': self.logging.__dict__,
        }
    
    def save_to_file(self, file_path: str):
        """Save current configuration to file"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = self.to_dict()
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Configuration saved to: {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {file_path}: {e}")
    
    def reload(self):
        """Reload configuration from sources"""
        logger.info("Reloading configuration...")
        self._load_configuration()
        
        # Notify watchers
        for callback in self._watchers:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")
    
    def add_watcher(self, callback):
        """Add configuration change watcher"""
        self._watchers.append(callback)
    
    def remove_watcher(self, callback):
        """Remove configuration change watcher"""
        if callback in self._watchers:
            self._watchers.remove(callback)


# Global configuration instance
_config = None


def get_config(environment: str = None) -> ConfigManager:
    """Get global configuration instance"""
    global _config
    if _config is None or (environment and _config.environment != environment):
        env = environment or os.getenv('SCRAPER_ENV', 'development')
        _config = ConfigManager(environment=env)
    return _config


def reload_config():
    """Reload global configuration"""
    global _config
    if _config:
        _config.reload() 
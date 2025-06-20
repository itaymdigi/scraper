"""
Performance Optimization Module for Web Scraper

Provides:
- Async/await support for concurrent operations
- Advanced caching with compression and TTL
- Memory management and monitoring
- Performance metrics and profiling
- Resource pooling and connection management
"""

import asyncio
import time
import psutil
import threading
import functools
import gzip
import pickle
from typing import Dict, Any, Optional, Callable, List, Tuple, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import weakref
import gc
from pathlib import Path

try:
    import aiohttp
except ImportError:
    aiohttp = None

from utils.logger import get_logger, LoggerMixin
from utils.error_handler import error_handler, ScraperException

logger = get_logger(__name__)


class PerformanceError(ScraperException):
    """Performance-related errors"""
    pass


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage: Dict[str, float] = field(default_factory=dict)
    cpu_usage: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    requests_made: int = 0
    errors_count: int = 0
    
    def finish(self):
        """Mark metrics as finished"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        
        # Get current system metrics
        process = psutil.Process()
        self.memory_usage = {
            'rss': process.memory_info().rss / 1024 / 1024,  # MB
            'vms': process.memory_info().vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
        self.cpu_usage = process.cpu_percent()


class AsyncHTTPClient(LoggerMixin):
    """Async HTTP client with connection pooling and rate limiting"""
    
    def __init__(self, max_connections: int = 100, rate_limit: int = 10):
        super().__init__()
        self.max_connections = max_connections
        self.rate_limit = rate_limit
        self.session = None
        self._semaphore = None
        self._rate_limiter = None
        self._last_request_time = 0
        
        if aiohttp is None:
            self.log_warning("aiohttp not available, async features disabled")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if aiohttp is None:
            raise PerformanceError("aiohttp not available")
            
        connector = aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections // 4,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'ScraperBot/1.0 (Async)'}
        )
        
        self._semaphore = asyncio.Semaphore(self.max_connections)
        self._rate_limiter = asyncio.Semaphore(self.rate_limit)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch(self, url: str, **kwargs):
        """Fetch URL with rate limiting and connection pooling"""
        if aiohttp is None:
            raise PerformanceError("aiohttp not available")
            
        async with self._semaphore:
            async with self._rate_limiter:
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - self._last_request_time
                if time_since_last < (1.0 / self.rate_limit):
                    await asyncio.sleep((1.0 / self.rate_limit) - time_since_last)
                
                self._last_request_time = time.time()
                
                try:
                    response = await self.session.get(url, **kwargs)
                    self.log_debug(f"Fetched {url} - Status: {response.status}")
                    return response
                except Exception as e:
                    self.log_error(f"Error fetching {url}: {e}")
                    raise


class AdvancedCache(LoggerMixin):
    """Advanced caching system with compression, TTL, and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600, 
                 compression: bool = True, storage_path: Optional[str] = None):
        super().__init__()
        self.max_size = max_size
        self.ttl = ttl
        self.compression = compression
        self.storage_path = Path(storage_path) if storage_path else None
        
        self._cache = {}
        self._access_times = {}
        self._creation_times = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # Load persistent cache
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_persistent_cache()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            # Check TTL
            if self._is_expired(key):
                self._remove_key(key)
                self._misses += 1
                return None
            
            # Update access time
            self._access_times[key] = time.time()
            self._hits += 1
            
            # Decompress if needed
            value = self._cache[key]
            if self.compression and isinstance(value, bytes):
                try:
                    value = pickle.loads(gzip.decompress(value))
                except Exception as e:
                    self.log_error(f"Error decompressing cache value: {e}")
                    self._remove_key(key)
                    return None
            
            return value
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        with self._lock:
            # Compress if needed
            if self.compression:
                try:
                    value = gzip.compress(pickle.dumps(value))
                except Exception as e:
                    self.log_error(f"Error compressing cache value: {e}")
                    return
            
            # Evict if at max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = value
            self._access_times[key] = time.time()
            self._creation_times[key] = time.time()
            
            # Save to persistent storage
            if self.storage_path:
                self._save_to_persistent(key, value)
    
    def delete(self, key: str):
        """Delete key from cache"""
        with self._lock:
            self._remove_key(key)
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._creation_times.clear()
            
            if self.storage_path:
                for file in self.storage_path.glob("*.cache"):
                    file.unlink()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'memory_usage': self._estimate_memory_usage()
            }
    
    def _is_expired(self, key: str) -> bool:
        """Check if key is expired"""
        if key not in self._creation_times:
            return True
        return time.time() - self._creation_times[key] > self.ttl
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self._remove_key(lru_key)
    
    def _remove_key(self, key: str):
        """Remove key from all structures"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._creation_times.pop(key, None)
        
        if self.storage_path:
            cache_file = self.storage_path / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
    
    def _cleanup_loop(self):
        """Background cleanup thread"""
        while True:
            try:
                time.sleep(300)  # 5 minutes
                self._cleanup_expired()
            except Exception as e:
                self.log_error(f"Error in cache cleanup: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        with self._lock:
            expired_keys = [key for key in self._cache.keys() if self._is_expired(key)]
            for key in expired_keys:
                self._remove_key(key)
            
            if expired_keys:
                self.log_info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        import sys
        total_size = 0
        for key, value in self._cache.items():
            total_size += sys.getsizeof(key) + sys.getsizeof(value)
        return total_size
    
    def _load_persistent_cache(self):
        """Load cache from persistent storage"""
        try:
            for cache_file in self.storage_path.glob("*.cache"):
                key = cache_file.stem
                with open(cache_file, 'rb') as f:
                    value = f.read()
                self._cache[key] = value
                self._creation_times[key] = cache_file.stat().st_mtime
                self._access_times[key] = time.time()
        except Exception as e:
            self.log_error(f"Error loading persistent cache: {e}")
    
    def _save_to_persistent(self, key: str, value: bytes):
        """Save cache entry to persistent storage"""
        try:
            cache_file = self.storage_path / f"{key}.cache"
            with open(cache_file, 'wb') as f:
                f.write(value)
        except Exception as e:
            self.log_error(f"Error saving to persistent cache: {e}")


class MemoryManager(LoggerMixin):
    """Memory management and monitoring"""
    
    def __init__(self, memory_limit_mb: int = 512):
        super().__init__()
        self.memory_limit_mb = memory_limit_mb
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self._weak_refs = weakref.WeakSet()
        self._monitoring = False
        
    def start_monitoring(self, interval: int = 60):
        """Start memory monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        thread.start()
        self.log_info(f"Memory monitoring started (limit: {self.memory_limit_mb}MB)")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self._monitoring = False
    
    def register_object(self, obj):
        """Register object for memory tracking"""
        self._weak_refs.add(obj)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def cleanup_memory(self):
        """Force memory cleanup"""
        # Force garbage collection
        collected = gc.collect()
        
        # Get memory usage after cleanup
        usage = self.get_memory_usage()
        
        self.log_info(f"Memory cleanup: collected {collected} objects, "
                     f"current usage: {usage['rss_mb']:.1f}MB")
        
        return usage
    
    def _monitor_loop(self, interval: int):
        """Memory monitoring loop"""
        while self._monitoring:
            try:
                usage = self.get_memory_usage()
                
                if usage['rss_mb'] > self.memory_limit_mb:
                    self.log_warning(f"Memory usage ({usage['rss_mb']:.1f}MB) "
                                   f"exceeds limit ({self.memory_limit_mb}MB)")
                    self.cleanup_memory()
                
                time.sleep(interval)
                
            except Exception as e:
                self.log_error(f"Error in memory monitoring: {e}")


class PerformanceProfiler(LoggerMixin):
    """Performance profiling and metrics collection"""
    
    def __init__(self):
        super().__init__()
        self._metrics = defaultdict(list)
        self._active_operations = {}
        self._lock = threading.RLock()
    
    def start_operation(self, operation_name: str) -> str:
        """Start timing an operation"""
        operation_id = f"{operation_name}_{time.time()}"
        
        with self._lock:
            self._active_operations[operation_id] = {
                'name': operation_name,
                'start_time': time.time(),
                'metrics': PerformanceMetrics()
            }
        
        return operation_id
    
    def end_operation(self, operation_id: str):
        """End timing an operation"""
        with self._lock:
            if operation_id not in self._active_operations:
                return
            
            operation = self._active_operations.pop(operation_id)
            operation['metrics'].finish()
            
            self._metrics[operation['name']].append(operation['metrics'])
            
            # Keep only last 100 metrics per operation
            if len(self._metrics[operation['name']]) > 100:
                self._metrics[operation['name']] = self._metrics[operation['name']][-100:]
    
    def get_metrics(self, operation_name: str = None) -> Dict[str, Any]:
        """Get performance metrics"""
        with self._lock:
            if operation_name:
                metrics_list = self._metrics.get(operation_name, [])
            else:
                metrics_list = []
                for op_metrics in self._metrics.values():
                    metrics_list.extend(op_metrics)
            
            if not metrics_list:
                return {}
            
            durations = [m.duration for m in metrics_list if m.duration]
            memory_usage = [m.memory_usage.get('rss', 0) for m in metrics_list]
            
            return {
                'count': len(metrics_list),
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'min_duration': min(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'avg_memory_mb': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'total_cache_hits': sum(m.cache_hits for m in metrics_list),
                'total_cache_misses': sum(m.cache_misses for m in metrics_list),
                'total_requests': sum(m.requests_made for m in metrics_list),
                'total_errors': sum(m.errors_count for m in metrics_list)
            }
    
    def profile_function(self, func_name: str = None):
        """Decorator to profile function performance"""
        def decorator(func):
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                operation_id = self.start_operation(name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_operation(operation_id)
            
            return wrapper
        return decorator


# Global instances
cache = AdvancedCache()
memory_manager = MemoryManager()
profiler = PerformanceProfiler()


def async_batch_processor(batch_size: int = 10, max_workers: int = 5):
    """Decorator for batch processing with async support"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(items: List[Any], *args, **kwargs):
            results = []
            
            # Process in batches
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                # Create tasks for batch
                tasks = []
                for item in batch:
                    if asyncio.iscoroutinefunction(func):
                        task = func(item, *args, **kwargs)
                    else:
                        task = asyncio.get_event_loop().run_in_executor(
                            None, func, item, *args, **kwargs
                        )
                    tasks.append(task)
                
                # Wait for batch completion
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(batch_results)
            
            return results
        
        return wrapper
    return decorator


@error_handler.handle_with_retry(max_retries=3)
def optimized_requests(urls: List[str], max_workers: int = 5) -> List[Dict[str, Any]]:
    """Optimized concurrent requests with caching and error handling"""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all requests
        future_to_url = {}
        for url in urls:
            # Check cache first
            cached_result = cache.get(url)
            if cached_result:
                results.append(cached_result)
                continue
            
            future = executor.submit(_fetch_url, url)
            future_to_url[future] = url
        
        # Collect results
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                cache.set(url, result)
                results.append(result)
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                results.append({'url': url, 'error': str(e)})
    
    return results


def _fetch_url(url: str) -> Dict[str, Any]:
    """Fetch single URL (helper function)"""
    import requests
    
    try:
        response = requests.get(url, timeout=30)
        return {
            'url': url,
            'status_code': response.status_code,
            'content': response.text,
            'headers': dict(response.headers)
        }
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {e}") 
"""
Cache utilities for the web scraper.
"""

import hashlib
import datetime
import os
import json
from config.settings import CACHE_DIRECTORY

# In-memory cache for quick access
cache = {}


def get_cache_key(url, depth, max_pages, domain_restriction):
    """Generate a unique cache key based on crawl parameters"""
    key_string = f"{url}_{depth}_{max_pages}_{domain_restriction}"
    return hashlib.md5(key_string.encode()).hexdigest()


def cache_crawl_results(key, results):
    """Store crawl results in cache"""
    cache[key] = results
    cache[f"{key}_timestamp"] = datetime.datetime.now()
    
    # Also save to disk for persistence
    _save_to_disk(key, results)


def get_cached_results(key):
    """Retrieve crawl results from cache if available and not expired"""
    # First check in-memory cache
    if key in cache:
        timestamp = cache.get(f"{key}_timestamp")
        # Check if cache is less than 24 hours old
        if timestamp and (datetime.datetime.now() - timestamp).total_seconds() < 86400:
            return cache[key]
    
    # If not in memory, check disk cache
    return _load_from_disk(key)


def _save_to_disk(key, results):
    """Save cache results to disk"""
    try:
        if not os.path.exists(CACHE_DIRECTORY):
            os.makedirs(CACHE_DIRECTORY)
        
        cache_file = os.path.join(CACHE_DIRECTORY, f"{key}.json")
        cache_data = {
            'results': results,
            'timestamp': datetime.datetime.now().isoformat(),
            'key': key
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache to disk: {e}")


def _load_from_disk(key):
    """Load cache results from disk"""
    try:
        cache_file = os.path.join(CACHE_DIRECTORY, f"{key}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is not expired (24 hours)
            timestamp = datetime.datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.datetime.now() - timestamp).total_seconds() < 86400:
                # Update in-memory cache
                cache[key] = cache_data['results']
                cache[f"{key}_timestamp"] = timestamp
                return cache_data['results']
    except Exception as e:
        print(f"Warning: Could not load cache from disk: {e}")
    
    return None


def clear_cache():
    """Clear all cached data"""
    global cache
    cache.clear()
    
    # Also clear disk cache
    try:
        if os.path.exists(CACHE_DIRECTORY):
            for filename in os.listdir(CACHE_DIRECTORY):
                if filename.endswith('.json'):
                    os.remove(os.path.join(CACHE_DIRECTORY, filename))
    except Exception as e:
        print(f"Warning: Could not clear disk cache: {e}")


def get_cache_stats():
    """Get cache statistics"""
    memory_count = len([k for k in cache.keys() if not k.endswith('_timestamp')]) // 2
    
    disk_count = 0
    if os.path.exists(CACHE_DIRECTORY):
        disk_count = len([f for f in os.listdir(CACHE_DIRECTORY) if f.endswith('.json')])
    
    return {
        'memory_entries': memory_count,
        'disk_entries': disk_count,
        'cache_directory': CACHE_DIRECTORY
    } 
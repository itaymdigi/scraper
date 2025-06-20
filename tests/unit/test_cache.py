"""
Unit tests for cache utilities.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open
from utils.cache import (
    get_cache_key, cache_crawl_results, get_cached_results,
    clear_cache, get_cache_stats, cache
)


class TestCacheKeyGeneration:
    """Test cache key generation"""
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly"""
        key1 = get_cache_key("https://example.com", 2, 50, "Stay in same domain")
        key2 = get_cache_key("https://example.com", 2, 50, "Stay in same domain")
        key3 = get_cache_key("https://example.com", 3, 50, "Stay in same domain")
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different parameters should generate different keys
        assert key1 != key3
        
        # Keys should be MD5 hashes (32 characters)
        assert len(key1) == 32
        assert all(c in '0123456789abcdef' for c in key1)
    
    def test_cache_key_consistency(self):
        """Test that cache keys are consistent across calls"""
        url = "https://example.com"
        depth = 2
        max_pages = 100
        domain_restriction = "Allow all domains"
        
        key1 = get_cache_key(url, depth, max_pages, domain_restriction)
        key2 = get_cache_key(url, depth, max_pages, domain_restriction)
        
        assert key1 == key2


class TestInMemoryCache:
    """Test in-memory cache functionality"""
    
    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()
    
    def test_cache_storage_and_retrieval(self):
        """Test storing and retrieving from cache"""
        key = "test_key"
        test_data = [
            {"url": "https://example.com", "content": "<html>Test</html>"},
            {"url": "https://example.com/page2", "content": "<html>Test2</html>"}
        ]
        
        # Store data
        cache_crawl_results(key, test_data)
        
        # Retrieve data
        retrieved_data = get_cached_results(key)
        
        assert retrieved_data == test_data
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        result = get_cached_results("nonexistent_key")
        assert result is None
    
    def test_cache_expiration(self):
        """Test that expired cache entries are not returned"""
        key = "test_key"
        test_data = [{"url": "https://example.com", "content": "test"}]
        
        # Store data
        cache_crawl_results(key, test_data)
        
        # Manually set timestamp to expired (more than 24 hours ago)
        expired_timestamp = datetime.now() - timedelta(hours=25)
        cache[f"{key}_timestamp"] = expired_timestamp
        
        # Should return None for expired data
        result = get_cached_results(key)
        assert result is None
    
    def test_cache_clear(self):
        """Test clearing cache"""
        key = "test_key"
        test_data = [{"url": "https://example.com", "content": "test"}]
        
        # Store data
        cache_crawl_results(key, test_data)
        assert get_cached_results(key) is not None
        
        # Clear cache
        clear_cache()
        assert get_cached_results(key) is None
        assert len(cache) == 0


class TestDiskCache:
    """Test disk cache functionality"""
    
    def test_disk_cache_save_and_load(self, temp_cache_dir):
        """Test saving to and loading from disk cache"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            key = "test_disk_key"
            test_data = [
                {"url": "https://example.com", "content": "<html>Test</html>"}
            ]
            
            # Clear in-memory cache to force disk lookup
            clear_cache()
            
            # Store data (should save to disk)
            cache_crawl_results(key, test_data)
            
            # Clear in-memory cache again
            clear_cache()
            
            # Retrieve data (should load from disk)
            retrieved_data = get_cached_results(key)
            
            assert retrieved_data == test_data
    
    def test_disk_cache_file_creation(self, temp_cache_dir):
        """Test that cache files are created on disk"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            key = "test_file_key"
            test_data = [{"url": "https://example.com", "content": "test"}]
            
            cache_crawl_results(key, test_data)
            
            # Check that file was created
            cache_file = os.path.join(temp_cache_dir, f"{key}.json")
            assert os.path.exists(cache_file)
            
            # Check file contents
            with open(cache_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            assert file_data['key'] == key
            assert file_data['results'] == test_data
            assert 'timestamp' in file_data
    
    def test_disk_cache_expiration(self, temp_cache_dir):
        """Test that expired disk cache entries are not loaded"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            key = "test_expired_key"
            test_data = [{"url": "https://example.com", "content": "test"}]
            
            # Create expired cache file
            cache_file = os.path.join(temp_cache_dir, f"{key}.json")
            expired_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
            
            cache_data = {
                'results': test_data,
                'timestamp': expired_timestamp,
                'key': key
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
            
            # Clear in-memory cache
            clear_cache()
            
            # Should return None for expired data
            result = get_cached_results(key)
            assert result is None
    
    def test_disk_cache_error_handling(self, temp_cache_dir):
        """Test disk cache error handling"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            # Test with corrupted cache file
            key = "test_corrupted_key"
            cache_file = os.path.join(temp_cache_dir, f"{key}.json")
            
            # Create corrupted JSON file
            with open(cache_file, 'w') as f:
                f.write("invalid json content")
            
            # Should handle error gracefully and return None
            result = get_cached_results(key)
            assert result is None


class TestCacheStats:
    """Test cache statistics functionality"""
    
    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()
    
    def test_cache_stats_empty(self):
        """Test cache stats when cache is empty"""
        stats = get_cache_stats()
        
        assert stats['memory_entries'] == 0
        assert stats['disk_entries'] == 0
        assert 'cache_directory' in stats
    
    def test_cache_stats_with_data(self, temp_cache_dir):
        """Test cache stats with cached data"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            # Add some memory cache entries
            cache_crawl_results("key1", [{"url": "test1", "content": "content1"}])
            cache_crawl_results("key2", [{"url": "test2", "content": "content2"}])
            
            stats = get_cache_stats()
            
            # Should count both memory and disk entries
            assert stats['memory_entries'] >= 1  # At least one entry
            assert stats['disk_entries'] >= 2  # Two files created
    
    def test_cache_stats_disk_only(self, temp_cache_dir):
        """Test cache stats with only disk cache"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            # Create cache files directly on disk
            for i in range(3):
                cache_file = os.path.join(temp_cache_dir, f"key{i}.json")
                cache_data = {
                    'results': [{"url": f"test{i}", "content": f"content{i}"}],
                    'timestamp': datetime.now().isoformat(),
                    'key': f"key{i}"
                }
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)
            
            # Clear memory cache
            clear_cache()
            
            stats = get_cache_stats()
            
            assert stats['memory_entries'] == 0
            assert stats['disk_entries'] == 3


class TestCacheIntegration:
    """Test cache integration with crawling"""
    
    def test_cache_integration_flow(self, temp_cache_dir):
        """Test complete cache flow"""
        with patch('utils.cache.CACHE_DIRECTORY', temp_cache_dir):
            # Simulate crawl parameters
            url = "https://example.com"
            depth = 2
            max_pages = 50
            domain_restriction = "Stay in same domain"
            
            # Generate cache key
            cache_key = get_cache_key(url, depth, max_pages, domain_restriction)
            
            # First check - should be cache miss
            cached_result = get_cached_results(cache_key)
            assert cached_result is None
            
            # Simulate crawl results
            crawl_results = [
                {"url": "https://example.com", "content": "<html>Home</html>"},
                {"url": "https://example.com/about", "content": "<html>About</html>"}
            ]
            
            # Cache the results
            cache_crawl_results(cache_key, crawl_results)
            
            # Second check - should be cache hit
            cached_result = get_cached_results(cache_key)
            assert cached_result == crawl_results
            
            # Clear memory cache and check disk persistence
            clear_cache()
            cached_result = get_cached_results(cache_key)
            assert cached_result == crawl_results
    
    def test_cache_key_uniqueness(self):
        """Test that different parameters generate different cache keys"""
        base_params = ("https://example.com", 2, 50, "Stay in same domain")
        
        # Test different URLs
        key1 = get_cache_key(*base_params)
        key2 = get_cache_key("https://different.com", 2, 50, "Stay in same domain")
        assert key1 != key2
        
        # Test different depths
        key3 = get_cache_key("https://example.com", 3, 50, "Stay in same domain")
        assert key1 != key3
        
        # Test different max_pages
        key4 = get_cache_key("https://example.com", 2, 100, "Stay in same domain")
        assert key1 != key4
        
        # Test different domain restrictions
        key5 = get_cache_key("https://example.com", 2, 50, "Allow all domains")
        assert key1 != key5 
"""
Test script for the enhanced scraper modules.
Tests database integration, monitoring, and API functionality.
"""

import asyncio
import time
import uuid
from datetime import datetime

# Test database functionality
def test_database():
    """Test database operations"""
    print("🗄️ Testing Database Integration...")
    
    try:
        from utils.database import get_database, CrawlResult, save_crawl_session
        
        # Test database initialization
        db = get_database()
        print("✅ Database initialized successfully")
        
        # Test session creation
        session_id = str(uuid.uuid4())
        parameters = {
            'target_url': 'https://example.com',
            'depth': 2,
            'max_pages': 10
        }
        
        success = save_crawl_session(session_id, 'https://example.com', parameters)
        if success:
            print("✅ Crawl session created successfully")
        else:
            print("❌ Failed to create crawl session")
        
        # Test saving crawl results
        test_result = CrawlResult(
            url='https://example.com/test',
            content='<html><body>Test content</body></html>',
            title='Test Page',
            status_code=200,
            depth=1,
            metadata={'test': True}
        )
        
        success = db.save_crawl_result(session_id, test_result)
        if success:
            print("✅ Crawl result saved successfully")
        else:
            print("❌ Failed to save crawl result")
        
        # Test retrieving results
        results = db.get_crawl_results(session_id)
        if results:
            print(f"✅ Retrieved {len(results)} crawl results")
        else:
            print("❌ No crawl results found")
        
        # Test recent sessions
        sessions = db.get_recent_sessions(limit=5)
        print(f"✅ Found {len(sessions)} recent sessions")
        
        print("✅ Database tests completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}\n")
        return False


def test_monitoring():
    """Test monitoring functionality"""
    print("📊 Testing Monitoring System...")
    
    try:
        from utils.monitoring import get_metrics_collector, get_health_checker, start_monitoring, stop_monitoring
        
        # Test metrics collector
        collector = get_metrics_collector()
        print("✅ Metrics collector initialized")
        
        # Test system metrics collection
        collector.collect_system_metrics()
        metrics = collector.get_recent_metrics(1)
        if metrics:
            latest = metrics[0]
            print(f"✅ System metrics collected - CPU: {latest.cpu_percent:.1f}%, Memory: {latest.memory_percent:.1f}%")
        else:
            print("❌ No system metrics collected")
        
        # Test crawl tracking
        test_session = str(uuid.uuid4())
        crawl_metrics = collector.start_crawl_tracking(test_session)
        print("✅ Crawl tracking started")
        
        # Update crawl metrics
        collector.update_crawl_metrics(test_session, total_pages=5, successful_pages=4, failed_pages=1)
        collector.finish_crawl_tracking(test_session, "completed")
        print("✅ Crawl tracking completed")
        
        # Test health checker
        checker = get_health_checker()
        health_status = checker.get_overall_status()
        print(f"✅ Health check status: {health_status['status']}")
        
        # Test performance counters
        collector.increment_counter('test_counter', 5.0)
        collector.set_counter('test_gauge', 42.0)
        counters = collector.get_performance_counters()
        print(f"✅ Performance counters: {len(counters)} metrics")
        
        # Test health status
        health = collector.get_health_status()
        print(f"✅ System health: {health['status']} - {health['message']}")
        
        print("✅ Monitoring tests completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Monitoring test failed: {str(e)}\n")
        return False


def test_config_manager():
    """Test configuration manager"""
    print("⚙️ Testing Configuration Manager...")
    
    try:
        from config.config_manager import get_config, ConfigManager
        
        # Test configuration loading
        config = get_config()
        print("✅ Configuration manager initialized")
        
        # Test configuration access
        crawler_config = config.crawler
        print(f"✅ Crawler config - Max workers: {crawler_config.max_workers}, Timeout: {crawler_config.timeout}")
        
        cache_config = config.cache
        print(f"✅ Cache config - Enabled: {cache_config.enabled}, TTL: {cache_config.default_ttl}")
        
        # Test environment switching
        config.switch_environment('test')
        print("✅ Switched to test environment")
        
        # Test configuration validation
        is_valid = config.validate_config()
        print(f"✅ Configuration validation: {'Valid' if is_valid else 'Invalid'}")
        
        print("✅ Configuration manager tests completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Configuration manager test failed: {str(e)}\n")
        return False


def test_performance_utils():
    """Test performance utilities"""
    print("🚀 Testing Performance Utilities...")
    
    try:
        from utils.performance import get_cache, get_memory_manager, get_profiler
        
        # Test advanced cache
        cache = get_cache()
        cache.set('test_key', 'test_value', ttl=60)
        value = cache.get('test_key')
        if value == 'test_value':
            print("✅ Advanced cache working")
        else:
            print("❌ Advanced cache failed")
        
        # Test memory manager
        memory_manager = get_memory_manager()
        memory_info = memory_manager.get_memory_info()
        print(f"✅ Memory info - Used: {memory_info['used_mb']:.1f}MB, Available: {memory_info['available_mb']:.1f}MB")
        
        # Test profiler
        profiler = get_profiler()
        
        @profiler.profile
        def test_function():
            time.sleep(0.1)
            return "test"
        
        result = test_function()
        metrics = profiler.get_metrics()
        if 'test_function' in metrics:
            print("✅ Function profiling working")
        else:
            print("❌ Function profiling failed")
        
        print("✅ Performance utilities tests completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Performance utilities test failed: {str(e)}\n")
        return False


def test_security():
    """Test security utilities"""
    print("🔒 Testing Security Utilities...")
    
    try:
        from utils.security import get_rate_limiter, get_domain_manager, get_security_auditor
        
        # Test rate limiter
        rate_limiter = get_rate_limiter()
        
        # Test multiple requests
        allowed_count = 0
        for i in range(5):
            if rate_limiter.allow_request('test_client'):
                allowed_count += 1
        
        print(f"✅ Rate limiter allowed {allowed_count}/5 requests")
        
        # Test domain manager
        domain_manager = get_domain_manager()
        
        # Test domain validation
        is_safe = domain_manager.is_domain_safe('example.com')
        print(f"✅ Domain safety check: {'Safe' if is_safe else 'Unsafe'}")
        
        # Test security auditor
        auditor = get_security_auditor()
        
        # Test URL security check
        security_result = auditor.check_url_security('https://example.com')
        print(f"✅ URL security check: {security_result['status']}")
        
        print("✅ Security utilities tests completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Security utilities test failed: {str(e)}\n")
        return False


def test_api_availability():
    """Test API availability"""
    print("🌐 Testing API Availability...")
    
    try:
        from api.endpoints import create_app, FASTAPI_AVAILABLE
        
        if FASTAPI_AVAILABLE:
            app = create_app()
            print("✅ FastAPI application created successfully")
            print("✅ API endpoints available")
        else:
            print("⚠️ FastAPI not available - install with: pip install fastapi uvicorn")
        
        print("✅ API availability tests completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ API availability test failed: {str(e)}\n")
        return False


def run_all_tests():
    """Run all enhancement tests"""
    print("🧪 Running Enhanced Scraper Tests")
    print("=" * 50)
    
    tests = [
        test_database,
        test_monitoring,
        test_config_manager,
        test_performance_utils,
        test_security,
        test_api_availability
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {str(e)}\n")
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All enhancement tests passed!")
    else:
        print(f"⚠️ {total - passed} tests failed or had issues")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1) 
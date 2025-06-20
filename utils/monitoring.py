"""
Monitoring and metrics module for the web scraper.
Provides comprehensive system monitoring, performance tracking, and health metrics.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
from pathlib import Path

from utils.logger import get_logger
from utils.error_handler import handle_errors, ScraperException
from utils.database import get_database

logger = get_logger("monitoring")


class MonitoringException(ScraperException):
    """Monitoring-specific exception"""
    pass


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    disk_free_gb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    active_threads: int = 0
    open_files: int = 0


@dataclass
class CrawlMetrics:
    """Crawl operation metrics"""
    session_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    total_bytes: int = 0
    avg_response_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    status: str = "running"


@dataclass
class PerformanceAlert:
    """Performance alert data"""
    alert_type: str = ""
    message: str = ""
    severity: str = "info"  # info, warning, error, critical
    timestamp: datetime = field(default_factory=datetime.now)
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0


class MetricsCollector:
    """Collects and stores various metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.system_metrics: deque = deque(maxlen=max_history)
        self.crawl_metrics: Dict[str, CrawlMetrics] = {}
        self.performance_counters: Dict[str, float] = defaultdict(float)
        self.alerts: deque = deque(maxlen=100)
        self._lock = threading.Lock()
        self._collectors: List[Callable] = []
        self._running = False
        self._thread = None
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time': 10.0,
            'error_rate': 0.1
        }
    
    def add_collector(self, collector: Callable):
        """Add a custom metrics collector function"""
        self._collectors.append(collector)
    
    def start_collection(self, interval: float = 30.0):
        """Start automatic metrics collection"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._collection_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()
        logger.info("Started metrics collection")
    
    def stop_collection(self):
        """Stop automatic metrics collection"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Stopped metrics collection")
    
    def _collection_loop(self, interval: float):
        """Main collection loop"""
        while self._running:
            try:
                self.collect_system_metrics()
                
                # Run custom collectors
                for collector in self._collectors:
                    try:
                        collector()
                    except Exception as e:
                        logger.error(f"Custom collector failed: {str(e)}")
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Metrics collection failed: {str(e)}")
                time.sleep(interval)
    
    @handle_errors(exceptions=(Exception,), default_return=None)
    def collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                active_threads=process.num_threads(),
                open_files=len(process.open_files())
            )
            
            with self._lock:
                self.system_metrics.append(metrics)
            
            # Check thresholds and generate alerts
            self._check_system_thresholds(metrics)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {str(e)}")
    
    def _check_system_thresholds(self, metrics: SystemMetrics):
        """Check system metrics against thresholds"""
        checks = [
            ('cpu_percent', metrics.cpu_percent, 'CPU usage'),
            ('memory_percent', metrics.memory_percent, 'Memory usage'),
            ('disk_usage_percent', metrics.disk_usage_percent, 'Disk usage')
        ]
        
        for metric_name, value, description in checks:
            threshold = self.thresholds.get(metric_name, 100.0)
            if value > threshold:
                severity = 'critical' if value > threshold * 1.1 else 'warning'
                alert = PerformanceAlert(
                    alert_type='system_threshold',
                    message=f"{description} is {value:.1f}% (threshold: {threshold:.1f}%)",
                    severity=severity,
                    metric_name=metric_name,
                    metric_value=value,
                    threshold=threshold
                )
                self.add_alert(alert)
    
    def start_crawl_tracking(self, session_id: str) -> CrawlMetrics:
        """Start tracking a crawl operation"""
        metrics = CrawlMetrics(session_id=session_id)
        with self._lock:
            self.crawl_metrics[session_id] = metrics
        return metrics
    
    def update_crawl_metrics(self, session_id: str, **updates):
        """Update crawl metrics"""
        with self._lock:
            if session_id in self.crawl_metrics:
                metrics = self.crawl_metrics[session_id]
                for key, value in updates.items():
                    if hasattr(metrics, key):
                        setattr(metrics, key, value)
    
    def finish_crawl_tracking(self, session_id: str, status: str = "completed"):
        """Finish tracking a crawl operation"""
        with self._lock:
            if session_id in self.crawl_metrics:
                metrics = self.crawl_metrics[session_id]
                metrics.end_time = datetime.now()
                metrics.status = status
                
                # Calculate error rate and check thresholds
                if metrics.total_pages > 0:
                    error_rate = metrics.failed_pages / metrics.total_pages
                    if error_rate > self.thresholds.get('error_rate', 0.1):
                        alert = PerformanceAlert(
                            alert_type='crawl_error_rate',
                            message=f"High error rate in crawl {session_id}: {error_rate:.2%}",
                            severity='warning',
                            metric_name='error_rate',
                            metric_value=error_rate,
                            threshold=self.thresholds['error_rate']
                        )
                        self.add_alert(alert)
    
    def increment_counter(self, name: str, value: float = 1.0):
        """Increment a performance counter"""
        with self._lock:
            self.performance_counters[name] += value
    
    def set_counter(self, name: str, value: float):
        """Set a performance counter value"""
        with self._lock:
            self.performance_counters[name] = value
    
    def add_alert(self, alert: PerformanceAlert):
        """Add a performance alert"""
        with self._lock:
            self.alerts.append(alert)
        
        # Log the alert
        log_level = {
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }.get(alert.severity, logger.info)
        
        log_level(f"Performance Alert [{alert.severity.upper()}]: {alert.message}")
    
    def get_recent_metrics(self, limit: int = 100) -> List[SystemMetrics]:
        """Get recent system metrics"""
        with self._lock:
            return list(self.system_metrics)[-limit:]
    
    def get_crawl_metrics(self, session_id: str = None) -> Dict[str, CrawlMetrics]:
        """Get crawl metrics"""
        with self._lock:
            if session_id:
                metrics = self.crawl_metrics.get(session_id)
                return {session_id: metrics} if metrics else {}
            return dict(self.crawl_metrics)
    
    def get_performance_counters(self) -> Dict[str, float]:
        """Get performance counters"""
        with self._lock:
            return dict(self.performance_counters)
    
    def get_recent_alerts(self, limit: int = 50) -> List[PerformanceAlert]:
        """Get recent alerts"""
        with self._lock:
            return list(self.alerts)[-limit:]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        recent_metrics = self.get_recent_metrics(1)
        if not recent_metrics:
            return {'status': 'unknown', 'message': 'No metrics available'}
        
        latest = recent_metrics[0]
        recent_alerts = self.get_recent_alerts(10)
        
        # Determine health status
        critical_alerts = [a for a in recent_alerts if a.severity == 'critical']
        warning_alerts = [a for a in recent_alerts if a.severity == 'warning']
        
        if critical_alerts:
            status = 'critical'
            message = f"{len(critical_alerts)} critical issues detected"
        elif warning_alerts:
            status = 'warning'
            message = f"{len(warning_alerts)} warnings detected"
        elif (latest.cpu_percent > 70 or 
              latest.memory_percent > 70 or 
              latest.disk_usage_percent > 80):
            status = 'degraded'
            message = "System resources under pressure"
        else:
            status = 'healthy'
            message = "All systems operational"
        
        return {
            'status': status,
            'message': message,
            'timestamp': datetime.now(),
            'metrics': {
                'cpu_percent': latest.cpu_percent,
                'memory_percent': latest.memory_percent,
                'disk_usage_percent': latest.disk_usage_percent,
                'active_threads': latest.active_threads
            },
            'alerts': {
                'critical': len(critical_alerts),
                'warning': len(warning_alerts),
                'total': len(recent_alerts)
            }
        }


class HealthChecker:
    """Health check system for various components"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func
    
    def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check"""
        if name not in self.checks:
            return {
                'status': 'unknown',
                'message': f'Check {name} not found',
                'timestamp': datetime.now()
            }
        
        try:
            result = self.checks[name]()
            if not isinstance(result, dict):
                result = {'status': 'ok', 'data': result}
            
            result['timestamp'] = datetime.now()
            self.last_results[name] = result
            return result
            
        except Exception as e:
            result = {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }
            self.last_results[name] = result
            return result
    
    def run_all_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered health checks"""
        results = {}
        for name in self.checks:
            results[name] = self.run_check(name)
        return results
    
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        results = self.run_all_checks()
        
        if not results:
            return {'status': 'unknown', 'message': 'No health checks configured'}
        
        failed_checks = [name for name, result in results.items() 
                        if result.get('status') == 'error']
        
        if failed_checks:
            return {
                'status': 'unhealthy',
                'message': f'Failed checks: {", ".join(failed_checks)}',
                'failed_checks': failed_checks,
                'total_checks': len(results)
            }
        else:
            return {
                'status': 'healthy',
                'message': 'All health checks passed',
                'total_checks': len(results)
            }


# Global instances
_metrics_collector = None
_health_checker = None
_instances_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    with _instances_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    with _instances_lock:
        if _health_checker is None:
            _health_checker = HealthChecker()
            _register_default_health_checks(_health_checker)
        return _health_checker


def _register_default_health_checks(checker: HealthChecker):
    """Register default health checks"""
    
    def check_database():
        """Check database connectivity"""
        try:
            db = get_database()
            # Try a simple query
            sessions = db.get_recent_sessions(limit=1)
            return {'status': 'ok', 'message': 'Database accessible'}
        except Exception as e:
            return {'status': 'error', 'message': f'Database error: {str(e)}'}
    
    def check_disk_space():
        """Check available disk space"""
        try:
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024 ** 3)
            if free_gb < 1.0:  # Less than 1GB free
                return {'status': 'error', 'message': f'Low disk space: {free_gb:.1f}GB free'}
            elif free_gb < 5.0:  # Less than 5GB free
                return {'status': 'warning', 'message': f'Disk space low: {free_gb:.1f}GB free'}
            else:
                return {'status': 'ok', 'message': f'Disk space OK: {free_gb:.1f}GB free'}
        except Exception as e:
            return {'status': 'error', 'message': f'Disk check error: {str(e)}'}
    
    def check_memory():
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return {'status': 'error', 'message': f'High memory usage: {memory.percent:.1f}%'}
            elif memory.percent > 80:
                return {'status': 'warning', 'message': f'Memory usage elevated: {memory.percent:.1f}%'}
            else:
                return {'status': 'ok', 'message': f'Memory usage normal: {memory.percent:.1f}%'}
        except Exception as e:
            return {'status': 'error', 'message': f'Memory check error: {str(e)}'}
    
    checker.register_check('database', check_database)
    checker.register_check('disk_space', check_disk_space)
    checker.register_check('memory', check_memory)


# Convenience functions
def start_monitoring(interval: float = 30.0):
    """Start system monitoring"""
    collector = get_metrics_collector()
    collector.start_collection(interval)


def stop_monitoring():
    """Stop system monitoring"""
    collector = get_metrics_collector()
    collector.stop_collection()


def track_crawl(session_id: str) -> CrawlMetrics:
    """Start tracking a crawl operation"""
    collector = get_metrics_collector()
    return collector.start_crawl_tracking(session_id)


def get_system_health() -> Dict[str, Any]:
    """Get current system health status"""
    collector = get_metrics_collector()
    checker = get_health_checker()
    
    return {
        'metrics': collector.get_health_status(),
        'health_checks': checker.get_overall_status(),
        'timestamp': datetime.now()
    } 
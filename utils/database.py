"""
Database integration module for the web scraper.
Provides SQLite support for storing crawl results, analysis data, and metadata.
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from contextlib import contextmanager

from utils.logger import get_logger
from utils.error_handler import handle_errors, ScraperException

logger = get_logger("database")


class DatabaseException(ScraperException):
    """Database-specific exception"""
    pass


@dataclass
class CrawlResult:
    """Data class for crawl results"""
    id: Optional[int] = None
    url: str = ""
    content: str = ""
    title: str = ""
    status_code: int = 200
    crawl_time: Optional[datetime] = None
    depth: int = 1
    parent_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.crawl_time is None:
            self.crawl_time = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisResult:
    """Data class for analysis results"""
    id: Optional[int] = None
    crawl_session_id: str = ""
    analysis_type: str = ""
    results: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.results is None:
            self.results = {}


class SQLiteDatabase:
    """SQLite database manager for local storage"""
    
    def __init__(self, db_path: str = "data/scraper.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseException(f"Database operation failed: {str(e)}")
        finally:
            cursor.close()
    
    def _init_database(self):
        """Initialize database tables"""
        with self.get_cursor() as cursor:
            # Crawl sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    target_url TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    status TEXT DEFAULT 'running',
                    total_pages INTEGER DEFAULT 0,
                    parameters TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crawl results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    content TEXT,
                    title TEXT,
                    status_code INTEGER DEFAULT 200,
                    crawl_time DATETIME NOT NULL,
                    depth INTEGER DEFAULT 1,
                    parent_url TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES crawl_sessions (session_id)
                )
            """)
            
            # Analysis results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    results TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES crawl_sessions (session_id)
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES crawl_sessions (session_id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_crawl_results_session ON crawl_results (session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_crawl_results_url ON crawl_results (url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_results_session ON analysis_results (session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_session ON performance_metrics (session_id)")
    
    @handle_errors(exceptions=(DatabaseException,), default_return=None)
    def create_crawl_session(self, session_id: str, target_url: str, parameters: Dict[str, Any]) -> bool:
        """Create a new crawl session"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO crawl_sessions (session_id, target_url, start_time, parameters)
                VALUES (?, ?, ?, ?)
            """, (session_id, target_url, datetime.now(), json.dumps(parameters)))
            logger.info(f"Created crawl session: {session_id}")
            return True
    
    @handle_errors(exceptions=(DatabaseException,), default_return=False)
    def update_crawl_session(self, session_id: str, status: str = None, total_pages: int = None) -> bool:
        """Update crawl session status"""
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
            if status == 'completed':
                updates.append("end_time = ?")
                params.append(datetime.now())
        
        if total_pages is not None:
            updates.append("total_pages = ?")
            params.append(total_pages)
        
        if not updates:
            return True
        
        params.append(session_id)
        
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                UPDATE crawl_sessions 
                SET {', '.join(updates)}
                WHERE session_id = ?
            """, params)
            return cursor.rowcount > 0
    
    @handle_errors(exceptions=(DatabaseException,), default_return=False)
    def save_crawl_result(self, session_id: str, result: CrawlResult) -> bool:
        """Save a crawl result to the database"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO crawl_results 
                (session_id, url, content, title, status_code, crawl_time, depth, parent_url, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, result.url, result.content, result.title,
                result.status_code, result.crawl_time, result.depth,
                result.parent_url, json.dumps(result.metadata)
            ))
            return True
    
    @handle_errors(exceptions=(DatabaseException,), default_return=[])
    def get_crawl_results(self, session_id: str, limit: int = None) -> List[CrawlResult]:
        """Get crawl results for a session"""
        with self.get_cursor() as cursor:
            query = """
                SELECT * FROM crawl_results 
                WHERE session_id = ? 
                ORDER BY crawl_time DESC
            """
            params = [session_id]
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                result = CrawlResult(
                    id=row['id'],
                    url=row['url'],
                    content=row['content'],
                    title=row['title'],
                    status_code=row['status_code'],
                    crawl_time=datetime.fromisoformat(row['crawl_time']),
                    depth=row['depth'],
                    parent_url=row['parent_url'],
                    metadata=metadata
                )
                results.append(result)
            
            return results
    
    @handle_errors(exceptions=(DatabaseException,), default_return=False)
    def save_analysis_result(self, session_id: str, analysis: AnalysisResult) -> bool:
        """Save analysis results"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO analysis_results (session_id, analysis_type, results)
                VALUES (?, ?, ?)
            """, (session_id, analysis.analysis_type, json.dumps(analysis.results)))
            return True
    
    @handle_errors(exceptions=(DatabaseException,), default_return={})
    def get_analysis_results(self, session_id: str, analysis_type: str = None) -> Dict[str, Any]:
        """Get analysis results for a session"""
        with self.get_cursor() as cursor:
            if analysis_type:
                cursor.execute("""
                    SELECT * FROM analysis_results 
                    WHERE session_id = ? AND analysis_type = ?
                    ORDER BY created_at DESC
                """, (session_id, analysis_type))
            else:
                cursor.execute("""
                    SELECT * FROM analysis_results 
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                """, (session_id,))
            
            rows = cursor.fetchall()
            results = {}
            
            for row in rows:
                results[row['analysis_type']] = {
                    'id': row['id'],
                    'results': json.loads(row['results']),
                    'created_at': row['created_at']
                }
            
            return results
    
    @handle_errors(exceptions=(DatabaseException,), default_return=[])
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent crawl sessions"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM crawl_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            sessions = []
            
            for row in rows:
                session = {
                    'session_id': row['session_id'],
                    'target_url': row['target_url'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'status': row['status'],
                    'total_pages': row['total_pages'],
                    'parameters': json.loads(row['parameters']) if row['parameters'] else {}
                }
                sessions.append(session)
            
            return sessions
    
    @handle_errors(exceptions=(DatabaseException,), default_return=False)
    def save_performance_metric(self, session_id: str, metric_name: str, 
                               metric_value: float, metadata: Dict[str, Any] = None) -> bool:
        """Save performance metrics"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO performance_metrics (session_id, metric_name, metric_value, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, metric_name, metric_value, json.dumps(metadata or {})))
            return True
    
    @handle_errors(exceptions=(DatabaseException,), default_return=False)
    def cleanup_old_data(self, days_old: int = 30) -> bool:
        """Clean up old crawl data"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with self.get_cursor() as cursor:
            # Get old session IDs
            cursor.execute("""
                SELECT session_id FROM crawl_sessions 
                WHERE start_time < ?
            """, (cutoff_date,))
            
            old_sessions = [row['session_id'] for row in cursor.fetchall()]
            
            if old_sessions:
                placeholders = ','.join(['?' for _ in old_sessions])
                
                # Delete related data
                cursor.execute(f"DELETE FROM performance_metrics WHERE session_id IN ({placeholders})", old_sessions)
                cursor.execute(f"DELETE FROM analysis_results WHERE session_id IN ({placeholders})", old_sessions)
                cursor.execute(f"DELETE FROM crawl_results WHERE session_id IN ({placeholders})", old_sessions)
                cursor.execute(f"DELETE FROM crawl_sessions WHERE session_id IN ({placeholders})", old_sessions)
                
                logger.info(f"Cleaned up {len(old_sessions)} old crawl sessions")
            
            return True
    
    def close(self):
        """Close database connections"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()


# Global database instance
_db_instance = None
_db_lock = threading.Lock()


def get_database(db_type: str = "sqlite", **kwargs) -> SQLiteDatabase:
    """Get database instance (singleton pattern)"""
    global _db_instance
    
    with _db_lock:
        if _db_instance is None:
            if db_type.lower() == "sqlite":
                db_path = kwargs.get("db_path", "data/scraper.db")
                _db_instance = SQLiteDatabase(db_path)
            else:
                raise DatabaseException(f"Unsupported database type: {db_type}")
        
        return _db_instance


# Convenience functions
def save_crawl_session(session_id: str, target_url: str, parameters: Dict[str, Any]) -> bool:
    """Save crawl session to database"""
    db = get_database()
    return db.create_crawl_session(session_id, target_url, parameters)


def save_crawl_results(session_id: str, results: List[CrawlResult]) -> bool:
    """Save multiple crawl results"""
    db = get_database()
    success_count = 0
    
    for result in results:
        if db.save_crawl_result(session_id, result):
            success_count += 1
    
    # Update session with total pages
    db.update_crawl_session(session_id, total_pages=len(results))
    
    logger.info(f"Saved {success_count}/{len(results)} crawl results for session {session_id}")
    return success_count == len(results)


def get_session_results(session_id: str) -> List[CrawlResult]:
    """Get all results for a crawl session"""
    db = get_database()
    return db.get_crawl_results(session_id)


def save_analysis(session_id: str, analysis_type: str, results: Dict[str, Any]) -> bool:
    """Save analysis results"""
    db = get_database()
    analysis = AnalysisResult(
        crawl_session_id=session_id,
        analysis_type=analysis_type,
        results=results
    )
    return db.save_analysis_result(session_id, analysis) 
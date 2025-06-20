"""
API endpoints for the web scraper.
Provides REST API access to scraper functionality using FastAPI.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Path as PathParam
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field, validator
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from core.crawler import perform_crawl
from analysis.technical_report import generate_technical_report
from utils.database import get_database, save_crawl_session, CrawlResult, AnalysisResult
from utils.logger import get_logger
from utils.error_handler import handle_errors, ScraperException
from utils.validators import URLValidator, ParameterValidator
from config.config_manager import get_config

logger = get_logger("api")


class APIException(ScraperException):
    """API-specific exception"""
    pass


# Pydantic models for request/response validation
class CrawlRequest(BaseModel):
    """Request model for crawl operations"""
    target_url: str = Field(..., description="URL to crawl")
    depth: int = Field(1, ge=1, le=10, description="Crawl depth")
    max_pages: int = Field(20, ge=1, le=1000, description="Maximum pages to crawl")
    timeout: int = Field(10, ge=5, le=300, description="Request timeout in seconds")
    domain_restriction: str = Field("Stay in same domain", description="Domain restriction policy")
    custom_domains: Optional[str] = Field(None, description="Custom domains list")
    user_agent: Optional[str] = Field(None, description="User agent string")
    max_workers: int = Field(5, ge=1, le=50, description="Number of concurrent workers")
    respect_robots: bool = Field(True, description="Respect robots.txt")
    use_cache: bool = Field(True, description="Use caching")
    
    @validator('target_url')
    def validate_url(cls, v):
        """Validate URL format"""
        validator = URLValidator()
        result = validator.validate_url(v)
        if not result.is_valid:
            raise ValueError(f"Invalid URL: {'; '.join(result.errors)}")
        return result.value


class CrawlResponse(BaseModel):
    """Response model for crawl operations"""
    session_id: str
    status: str
    message: str
    total_pages: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None


class CrawlResultResponse(BaseModel):
    """Response model for crawl results"""
    id: Optional[int]
    url: str
    title: str
    status_code: int
    crawl_time: datetime
    depth: int
    parent_url: Optional[str]
    content_length: int
    metadata: Dict[str, Any]


class AnalysisRequest(BaseModel):
    """Request model for analysis operations"""
    session_id: str = Field(..., description="Crawl session ID")
    analysis_types: List[str] = Field(default=["technical"], description="Types of analysis to perform")
    include_content: bool = Field(False, description="Include page content in analysis")


class AnalysisResponse(BaseModel):
    """Response model for analysis operations"""
    session_id: str
    analysis_types: List[str]
    results: Dict[str, Any]
    created_at: datetime


class SessionInfo(BaseModel):
    """Response model for session information"""
    session_id: str
    target_url: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    total_pages: int
    parameters: Dict[str, Any]


# Global FastAPI app instance
app = None
crawl_tasks = {}  # Store background crawl tasks


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    if not FASTAPI_AVAILABLE:
        raise APIException("FastAPI not available. Install with: pip install fastapi uvicorn")
    
    app = FastAPI(
        title="Web Scraper API",
        description="Advanced web scraper with analysis capabilities",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


def get_app() -> FastAPI:
    """Get or create FastAPI app instance"""
    global app
    if app is None:
        app = create_app()
    return app


# Background task functions
async def perform_crawl_task(session_id: str, crawl_params: Dict[str, Any]):
    """Background task for crawling"""
    try:
        logger.info(f"Starting crawl task for session: {session_id}")
        
        # Perform the crawl
        results = perform_crawl(**crawl_params)
        
        # Convert results to CrawlResult objects and save to database
        db = get_database()
        crawl_results = []
        
        for result in results:
            crawl_result = CrawlResult(
                url=result.get('url', ''),
                content=result.get('content', ''),
                title=result.get('title', ''),
                status_code=result.get('status_code', 200),
                crawl_time=datetime.now(),
                depth=result.get('depth', 1),
                parent_url=result.get('parent_url'),
                metadata=result.get('metadata', {})
            )
            crawl_results.append(crawl_result)
            db.save_crawl_result(session_id, crawl_result)
        
        # Update session status
        db.update_crawl_session(session_id, status='completed', total_pages=len(results))
        
        # Update task status
        if session_id in crawl_tasks:
            crawl_tasks[session_id]['status'] = 'completed'
            crawl_tasks[session_id]['end_time'] = datetime.now()
            crawl_tasks[session_id]['total_pages'] = len(results)
        
        logger.info(f"Completed crawl task for session: {session_id} ({len(results)} pages)")
        
    except Exception as e:
        logger.error(f"Crawl task failed for session {session_id}: {str(e)}")
        
        # Update session status
        db = get_database()
        db.update_crawl_session(session_id, status='failed')
        
        # Update task status
        if session_id in crawl_tasks:
            crawl_tasks[session_id]['status'] = 'failed'
            crawl_tasks[session_id]['error'] = str(e)


# API Routes
@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start a new crawl operation"""
    session_id = str(uuid.uuid4())
    
    # Save crawl session to database
    crawl_params = request.dict()
    save_crawl_session(session_id, request.target_url, crawl_params)
    
    # Store task info
    crawl_tasks[session_id] = {
        'status': 'running',
        'start_time': datetime.now(),
        'target_url': request.target_url,
        'parameters': crawl_params
    }
    
    # Start background crawl task
    background_tasks.add_task(perform_crawl_task, session_id, crawl_params)
    
    return CrawlResponse(
        session_id=session_id,
        status="started",
        message="Crawl operation started",
        start_time=datetime.now()
    )


@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def get_crawl_status(session_id: str = PathParam(..., description="Crawl session ID")):
    """Get crawl operation status"""
    db = get_database()
    
    # Try to get from database first
    sessions = db.get_recent_sessions(limit=100)
    session_info = next((s for s in sessions if s['session_id'] == session_id), None)
    
    if not session_info:
        # Check in-memory tasks
        if session_id in crawl_tasks:
            task_info = crawl_tasks[session_id]
            return CrawlResponse(
                session_id=session_id,
                status=task_info['status'],
                message=f"Crawl {task_info['status']}",
                start_time=task_info['start_time'],
                end_time=task_info.get('end_time'),
                total_pages=task_info.get('total_pages')
            )
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    
    return CrawlResponse(
        session_id=session_id,
        status=session_info['status'],
        message=f"Crawl {session_info['status']}",
        start_time=datetime.fromisoformat(session_info['start_time']),
        end_time=datetime.fromisoformat(session_info['end_time']) if session_info['end_time'] else None,
        total_pages=session_info['total_pages']
    )


@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def get_crawl_results(
    session_id: str = PathParam(..., description="Crawl session ID"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results"),
    include_content: bool = Query(False, description="Include page content")
):
    """Get crawl results for a session"""
    db = get_database()
    results = db.get_crawl_results(session_id, limit)
    
    if not results:
        raise HTTPException(status_code=404, detail="No results found for session")
    
    # Convert to response format
    response_results = []
    for result in results:
        result_dict = {
            'id': result.id,
            'url': result.url,
            'title': result.title,
            'status_code': result.status_code,
            'crawl_time': result.crawl_time,
            'depth': result.depth,
            'parent_url': result.parent_url,
            'content_length': len(result.content) if result.content else 0,
            'metadata': result.metadata
        }
        
        if include_content:
            result_dict['content'] = result.content
        
        response_results.append(result_dict)
    
    return {
        'session_id': session_id,
        'total_results': len(response_results),
        'results': response_results
    }


@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start analysis of crawl results"""
    db = get_database()
    
    # Check if session exists
    results = db.get_crawl_results(request.session_id, limit=1)
    if not results:
        raise HTTPException(status_code=404, detail="Session not found or no results available")
    
    # Get all results for analysis
    all_results = db.get_crawl_results(request.session_id)
    
    # Perform analysis
    analysis_results = {}
    
    if "technical" in request.analysis_types:
        try:
            # Convert database results to expected format
            crawl_data = []
            for result in all_results:
                crawl_data.append({
                    'url': result.url,
                    'content': result.content if request.include_content else '',
                    'title': result.title,
                    'status_code': result.status_code
                })
            
            technical_report = generate_technical_report(crawl_data)
            analysis_results['technical'] = technical_report
            
        except Exception as e:
            logger.error(f"Technical analysis failed: {str(e)}")
            analysis_results['technical'] = {'error': str(e)}
    
    # Save analysis results
    for analysis_type, results_data in analysis_results.items():
        analysis = AnalysisResult(
            crawl_session_id=request.session_id,
            analysis_type=analysis_type,
            results=results_data
        )
        db.save_analysis_result(request.session_id, analysis)
    
    return AnalysisResponse(
        session_id=request.session_id,
        analysis_types=request.analysis_types,
        results=analysis_results,
        created_at=datetime.now()
    )


@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def get_analysis_results(
    session_id: str = PathParam(..., description="Crawl session ID"),
    analysis_type: Optional[str] = Query(None, description="Specific analysis type")
):
    """Get analysis results for a session"""
    db = get_database()
    results = db.get_analysis_results(session_id, analysis_type)
    
    if not results:
        raise HTTPException(status_code=404, detail="No analysis results found")
    
    return {
        'session_id': session_id,
        'results': results
    }


@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def list_sessions(limit: int = Query(10, ge=1, le=100, description="Number of sessions to return")):
    """List recent crawl sessions"""
    db = get_database()
    sessions = db.get_recent_sessions(limit)
    
    return {
        'total_sessions': len(sessions),
        'sessions': sessions
    }


@handle_errors(exceptions=(APIException, Exception), default_return=JSONResponse(
    status_code=500, content={"error": "Internal server error"}
))
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now(),
        'version': '1.0.0'
    }


# Register routes
def register_routes(app: FastAPI):
    """Register all API routes"""
    app.post("/api/v1/crawl", response_model=CrawlResponse)(start_crawl)
    app.get("/api/v1/crawl/{session_id}/status", response_model=CrawlResponse)(get_crawl_status)
    app.get("/api/v1/crawl/{session_id}/results")(get_crawl_results)
    app.post("/api/v1/analysis", response_model=AnalysisResponse)(start_analysis)
    app.get("/api/v1/analysis/{session_id}")(get_analysis_results)
    app.get("/api/v1/sessions")(list_sessions)
    app.get("/api/v1/health")(health_check)


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start the FastAPI server"""
    if not FASTAPI_AVAILABLE:
        raise APIException("FastAPI not available. Install with: pip install fastapi uvicorn")
    
    app = get_app()
    register_routes(app)
    
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)


# Initialize app if imported
if FASTAPI_AVAILABLE:
    app = get_app()
    register_routes(app) 
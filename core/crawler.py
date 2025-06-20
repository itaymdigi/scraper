"""
Core crawling functionality for the web scraper.
"""

import asyncio
import aiohttp
import streamlit as st
import time
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import urllib.robotparser
import nest_asyncio

from config.settings import DEFAULT_USER_AGENT
from utils.cache import get_cache_key, cache_crawl_results, get_cached_results
from utils.error_handler import CrawlException, global_error_handler, handle_errors
from utils.logger import get_logger, scraper_logger
from utils.validators import URLValidator, ParameterValidator

# Apply nest_asyncio to make asyncio work with Streamlit
nest_asyncio.apply()

# Get logger for this module
logger = get_logger("crawler")


@handle_errors(exceptions=(CrawlException, Exception), default_return=[])
def perform_crawl(target_url: str, depth: int = 1, max_pages: int = 20, timeout: int = 10, 
                domain_restriction: str = "Stay in same domain", custom_domains: str = "", 
                user_agent: str = DEFAULT_USER_AGENT, max_workers: int = 5, 
                respect_robots: bool = True, use_cache: bool = True):
    """
    Synchronous wrapper for async crawl function with validation and error handling
    
    Args:
        target_url: URL to start crawling from
        depth: How deep to crawl (1-10)
        max_pages: Maximum number of pages to crawl (1-1000)
        timeout: Request timeout in seconds (5-300)
        domain_restriction: Domain restriction policy
        custom_domains: Custom domains list for restriction
        user_agent: User agent string
        max_workers: Number of concurrent workers (1-50)
        respect_robots: Whether to respect robots.txt
        use_cache: Whether to use caching
        
    Returns:
        List of crawled pages with URL and content
        
    Raises:
        CrawlException: If crawling fails due to validation or other errors
    """
    # Validate crawl parameters
    validation_result = ParameterValidator.validate_crawl_params(
        target_url, depth, max_pages, timeout, max_workers, user_agent
    )
    
    if not validation_result.is_valid:
        error_msg = f"Invalid crawl parameters: {'; '.join(validation_result.errors)}"
        logger.error(error_msg)
        raise CrawlException(error_msg, {"validation_errors": validation_result.errors})
    
    # Log warnings if any
    for warning in validation_result.warnings:
        logger.warning(f"Crawl parameter warning: {warning}")
    
    # Use validated parameters
    validated_params = validation_result.value
    
    # Log crawl start
    scraper_logger.log_crawl_start(validated_params['url'], depth, max_pages)
    start_time = time.time()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            perform_crawl_async(
                validated_params['url'], depth, max_pages, timeout, 
                domain_restriction, custom_domains, validated_params['user_agent'], 
                max_workers, respect_robots, use_cache
            )
        )
        
        # Log crawl completion
        duration = time.time() - start_time
        scraper_logger.log_crawl_complete(validated_params['url'], len(result), duration)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Crawl failed after {duration:.2f}s: {str(e)}")
        raise CrawlException(f"Crawling failed: {str(e)}", {
            "url": target_url,
            "duration": duration,
            "original_error": str(e)
        })


async def perform_crawl_async(target_url: str, depth: int = 1, max_pages: int = 20, timeout: int = 10, 
                            domain_restriction: str = "Stay in same domain", custom_domains: str = "", 
                            user_agent: str = DEFAULT_USER_AGENT, max_workers: int = 5, 
                            respect_robots: bool = True, use_cache: bool = True):
    """Crawl a website asynchronously and return a list of dicts with url and content."""
    
    # Check cache first if caching is enabled
    if use_cache:
        cache_key = get_cache_key(target_url, depth, max_pages, domain_restriction)
        cached_results = get_cached_results(cache_key)
        if cached_results:
            return cached_results
    
    results = []
    try:
        # Parse custom domains if provided
        allowed_domains = set()
        if domain_restriction == "Custom domain list" and custom_domains:
            allowed_domains = set(domain.strip() for domain in custom_domains.split('\n') if domain.strip())
        
        # Use aiohttp session for async requests
        connector = aiohttp.TCPConnector(limit=max_workers)
        async with aiohttp.ClientSession(connector=connector, headers={'User-Agent': user_agent}) as session:
        
            # Set up robots.txt parser if needed
            robots_cache = {}
        
            def can_fetch(url):
                """Check if robots.txt allows scraping this URL"""
                if not respect_robots:
                    return True
                    
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                # Check cache first
                if base_url in robots_cache:
                    rp = robots_cache[base_url]
                else:
                    # Initialize parser
                    rp = urllib.robotparser.RobotFileParser()
                    rp.set_url(f"{base_url}/robots.txt")
                    try:
                        rp.read()
                        robots_cache[base_url] = rp
                    except Exception:
                        # If we can't read robots.txt, assume we can fetch
                        return True
                
                return rp.can_fetch(user_agent, url)
        
            visited = set()
            
            # Progress bar for crawling
            progress_bar = st.progress(0)
            status_text = st.empty()
        
            # For storing errors to display later
            errors = []
        
            async def fetch_url(url_info):
                """Helper function to fetch a single URL asynchronously"""
                url, depth_level = url_info
                try:
                    # Check robots.txt first
                    if not can_fetch(url):
                        return {"url": url, "status": "error", "error": "Blocked by robots.txt"}
                    
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                            if response.status == 200:
                                content = await response.text()
                                links = []
                                
                                if depth_level < depth:
                                    soup = BeautifulSoup(content, 'html.parser')
                                    base_url = urlparse(url)
                                    base_domain = f"{base_url.scheme}://{base_url.netloc}"
                                    
                                    for link in soup.find_all('a', href=True):
                                        href = link['href'].strip()
                                        # Skip fragments, javascript, mailto, tel
                                        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                                            continue
                                        # Make relative URLs absolute
                                        if not href.startswith(('http://', 'https://')):
                                            href = urljoin(base_domain, href)
                                        # Validate URL
                                        parsed_href = urlparse(href)
                                        if not parsed_href.scheme or not parsed_href.netloc:
                                            continue
                                        target_domain = parsed_href.netloc
                                        
                                        # Apply domain restriction based on user selection
                                        should_visit = False
                                        if domain_restriction == "Stay in same domain":
                                            should_visit = (target_domain == base_url.netloc)
                                        elif domain_restriction == "Allow all domains":
                                            should_visit = True
                                        elif domain_restriction == "Custom domain list":
                                            should_visit = any(domain in target_domain for domain in allowed_domains)
                                        
                                        if should_visit and href not in visited:
                                            links.append((href, depth_level + 1))
                                            
                                return {
                                    "url": url,
                                    "content": content,
                                    "status": "success",
                                    "links": links
                                }
                            else:
                                return {"url": url, "status": "error", "error": f"HTTP {response.status}"}
                    except asyncio.TimeoutError:
                        return {"url": url, "status": "error", "error": "Request timed out"}
                except Exception as e:
                    return {"url": url, "status": "error", "error": str(e)}
        
            # Initial URL
            visited.add(target_url)
            current_batch = [(target_url, 0)]
        
            # Process URLs in batches with async execution
            while current_batch and len(visited) < max_pages:
                status_text.text(f"Crawling batch of {len(current_batch)} URLs...")
            
                # Use asyncio for parallel processing
                tasks = [fetch_url(url_info) for url_info in current_batch]
                batch_results = await asyncio.gather(*tasks)
            
                next_batch = []
                for data in batch_results:
                    if data["status"] == "success":
                        results.append({"url": data["url"], "content": data["content"]})
                        next_batch.extend(data["links"])
                    else:
                        errors.append(f"Error on {data['url']}: {data.get('error', 'Unknown error')}")
            
                # Update progress
                progress_bar.progress(min(len(visited) / max_pages, 1.0))
            
                # Filter out URLs we've already visited
                current_batch = []
                for url, depth in next_batch:
                    if url not in visited and len(visited) < max_pages:
                        visited.add(url)
                        current_batch.append((url, depth))
        
            # Store results in cache if caching is enabled
            if use_cache:
                cache_key = get_cache_key(target_url, depth, max_pages, domain_restriction)
                cache_crawl_results(cache_key, results)
                
            # Return the results
            return results
    except Exception as e:
        print(f"Error during crawl: {e}")
    
    return results


def html_to_text(html: str) -> str:
    """Convert HTML to plain readable text using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove scripts/styles
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def check_url_health(url):
    """Check if a URL is accessible and return status information."""
    try:
        import requests
        response = requests.head(url, timeout=10, allow_redirects=True)
        return {
            'status_code': response.status_code,
            'accessible': response.status_code == 200,
            'headers': dict(response.headers),
            'final_url': response.url
        }
    except requests.exceptions.RequestException as e:
        return {
            'status_code': None,
            'accessible': False,
            'error': str(e),
            'final_url': url
        } 
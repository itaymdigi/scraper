import streamlit as st
import os
import sys

# Configure Streamlit settings to prevent common errors
st.set_page_config(
    page_title="NeoScraper AI",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/neoscraper',
        'Report a bug': 'https://github.com/yourusername/neoscraper/issues',
        'About': 'NeoScraper AI - Advanced web scraping with AI analysis'
    }
)

# Set environment variables to prevent Streamlit errors
os.environ.setdefault('STREAMLIT_SERVER_ENABLE_CORS', 'false')
os.environ.setdefault('STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION', 'true')
os.environ.setdefault('STREAMLIT_BROWSER_GATHER_USAGE_STATS', 'false')

# Import crawl4ai and requests for scraping and API calls
import crawl4ai
import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement
from typing import Union, Optional, List, Dict, Any, cast
import json
import base64
import datetime
import io
import csv
import time
from urllib.parse import urlparse, urljoin
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from collections import Counter
import platform
import psutil
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import seaborn as sns
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import hashlib
import urllib.robotparser
import nest_asyncio

# Import WhatsApp integration
try:
    from utils.whatsapp_integration import get_whatsapp_client, configure_whatsapp
    WHATSAPP_AVAILABLE = True
except ImportError:
    WHATSAPP_AVAILABLE = False
    st.warning("⚠️ WhatsApp integration not available. Install required dependencies.")

# Apply nest_asyncio to make asyncio work with Streamlit
nest_asyncio.apply()

# --- BeautifulSoup Helper Functions ---

def safe_get_attribute(element: Any, attr: str, default: str = "") -> str:
    """Safely get an attribute from a BeautifulSoup element."""
    if isinstance(element, Tag):
        value = element.get(attr, default)
        if isinstance(value, list):
            return ' '.join(str(v) for v in value)
        return str(value) if value is not None else default
    return default

def as_tag(element: Any) -> Optional[Tag]:
    """Safely cast an element to Tag if it is one, otherwise return None."""
    return element if isinstance(element, Tag) else None

def safe_get_text(element: Union[Tag, NavigableString, None]) -> str:
    """Safely get text content from a BeautifulSoup element."""
    if isinstance(element, Tag):
        return element.get_text(strip=True)
    elif isinstance(element, NavigableString):
        return str(element).strip()
    return ""

def safe_has_attr(element: Union[Tag, NavigableString, None], attr: str) -> bool:
    """Safely check if a BeautifulSoup element has an attribute."""
    if isinstance(element, Tag):
        return element.has_attr(attr)
    return False

def safe_find_all(element: Union[Tag, NavigableString, None], *args, **kwargs):
    """Safely find all elements in a BeautifulSoup element."""
    if isinstance(element, Tag):
        return element.find_all(*args, **kwargs)
    return []

def safe_get_name(element: Union[Tag, NavigableString, None]) -> str:
    """Safely get the tag name from a BeautifulSoup element."""
    if isinstance(element, Tag):
        return element.name or ""
    return ""

def safe_get_string(element: Union[Tag, NavigableString, None]) -> str:
    """Safely get the string content from a BeautifulSoup element."""
    if isinstance(element, Tag):
        return element.string or ""
    elif isinstance(element, NavigableString):
        return str(element)
    return ""

# Define a synchronous wrapper for the async function
def perform_crawl(target_url: str, depth: int = 1, max_pages: int = 20, timeout: int = 10, 
                domain_restriction: str = "Stay in same domain", custom_domains: str = "", 
                user_agent: str = "Mozilla/5.0", max_workers: int = 5, respect_robots: bool = True, use_cache: bool = True):
    """Synchronous wrapper for async crawl function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(perform_crawl_async(target_url, depth, max_pages, timeout, domain_restriction, custom_domains, user_agent, max_workers, respect_robots, use_cache))

# --- Helper Functions ---

async def perform_crawl_async(target_url: str, depth: int = 1, max_pages: int = 20, timeout: int = 10, 
                domain_restriction: str = "Stay in same domain", custom_domains: str = "", 
                user_agent: str = "Mozilla/5.0", max_workers: int = 5, respect_robots: bool = True, use_cache: bool = True):
    """Crawl a website asynchronously and return a list of dicts with url and content."""
    
    # Check cache first if caching is enabled
    if use_cache:
        cache_key = get_cache_key(target_url, depth, max_pages, domain_restriction)
        cached_results = get_cached_results(cache_key)
        if cached_results:
            return cached_results
    
    results = []
    try:
        import requests
        from urllib.parse import urlparse, urljoin
        from bs4 import BeautifulSoup
        
        # Parse custom domains if provided
        allowed_domains = set()
        if domain_restriction == "Custom domain list" and custom_domains:
            allowed_domains = set(domain.strip() for domain in custom_domains.split('\n') if domain.strip())
        
        # Set up headers with user agent
        headers = {'User-Agent': user_agent}
        
        # Use aiohttp session for async requests
        connector = aiohttp.TCPConnector(limit=max_workers)
        async with aiohttp.ClientSession(connector=connector, headers={'User-Agent': user_agent}) as session:
        
            # Cache for storing already visited pages to avoid re-downloading
            page_cache = {}
        
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
            to_visit = [(target_url, 0)]
        
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
                                        href = link.get('href', '').strip()  # type: ignore
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

def generate_technical_report(html: str, url: str = "") -> dict:
    """Generate a comprehensive technical report for a web page that's detailed enough to rebuild the site."""
    report = {
        "url": url,
        "timestamp": datetime.datetime.now().isoformat(),
        "basic_info": {
            "title": "",
            "description": "",
            "language": "",
            "charset": "",
            "viewport": "",
            "favicon": ""
        },
        "structure": {
            "element_counts": {},
            "total_elements": 0,
            "depth_analysis": {},
            "semantic_structure": {}
        },
        "content": {
            "text_content_length": 0,
            "headings": {},
            "paragraphs": 0,
            "lists": {"ul": 0, "ol": 0},
            "tables": 0,
            "forms": []
        },
        "media": {
            "images": [],
            "videos": [],
            "audio": [],
            "iframes": [],
            "canvas": 0,
            "svg": 0
        },
        "links": {
            "internal": [],
            "external": [],
            "mailto": [],
            "tel": [],
            "anchor": [],
            "total_count": 0
        },
        "technology_stack": {
            "libraries": [],
            "frameworks": [],
            "cms": [],
            "analytics": [],
            "cdn_resources": [],
            "local_resources": []
        },
        "styling": {
            "css_files": [],
            "inline_styles": 0,
            "color_palette": [],
            "fonts": [],
            "css_frameworks": []
        },
        "scripts": {
            "external_scripts": [],
            "inline_scripts": 0,
            "script_types": {},
            "modules": []
        },
        "seo_analysis": {
            "meta_tags": {},
            "open_graph": {},
            "twitter_cards": {},
            "schema_markup": [],
            "alt_texts": {"missing": 0, "present": 0},
            "title_length": 0,
            "description_length": 0
        },
        "accessibility": {
            "aria_labels": 0,
            "aria_roles": [],
            "alt_attributes": 0,
            "heading_structure": [],
            "form_labels": 0,
            "skip_links": 0,
            "lang_attributes": 0
        },
        "performance": {
            "total_requests": 0,
            "image_optimization": {},
            "lazy_loading": 0,
            "preload_hints": [],
            "critical_resources": []
        },
        "security": {
            "csp_headers": [],
            "external_domains": [],
            "mixed_content": [],
            "security_headers": {}
        },
        "ui_components": {
            "buttons": [],
            "forms": [],
            "navigation": [],
            "modals": 0,
            "carousels": 0,
            "accordions": 0
        },
        "layout": {
            "grid_systems": [],
            "flexbox_usage": 0,
            "responsive_breakpoints": [],
            "container_types": {}
        },
        "errors": [],
        "warnings": [],
        "recommendations": []
    }
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # === BASIC INFO ANALYSIS ===
        try:
            # Title analysis
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
                report["basic_info"]["title"] = title
                report["seo_analysis"]["title_length"] = len(title)
                if len(title) < 30:
                    report["warnings"].append("Title is too short (< 30 characters)")
                elif len(title) > 60:
                    report["warnings"].append("Title is too long (> 60 characters)")
            else:
                report["errors"].append("Missing page title")
            
            # Meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag and safe_get_attribute(desc_tag, 'content'):
                desc = safe_get_attribute(desc_tag, 'content')
                report["basic_info"]["description"] = desc
                report["seo_analysis"]["description_length"] = len(desc)
                if len(desc) < 120:
                    report["warnings"].append("Meta description is too short (< 120 characters)")
                elif len(desc) > 160:
                    report["warnings"].append("Meta description is too long (> 160 characters)")
            else:
                report["errors"].append("Missing meta description")
            
            # Charset
            charset_tag = soup.find('meta', attrs={'charset': True})
            if charset_tag:
                report["basic_info"]["charset"] = safe_get_attribute(charset_tag, 'charset')
            
            # Viewport
            viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
            if viewport_tag:
                report["basic_info"]["viewport"] = safe_get_attribute(viewport_tag, 'content')
            else:
                report["warnings"].append("Missing viewport meta tag")
            
            # Favicon
            favicon_links = soup.find_all('link', rel=lambda x: x and 'icon' in x.lower() if x else False)
            if favicon_links:
                report["basic_info"]["favicon"] = [link.get('href') for link in favicon_links]
            
            # Language detection (enhanced)
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                report["basic_info"]["language"] = html_tag.get('lang')
                report["accessibility"]["lang_attributes"] += 1
            else:
                # Fallback detection
                text_sample = soup.get_text()[:1000]
                if any('\u0590' <= ch <= '\u05EA' for ch in text_sample):
                    report["basic_info"]["language"] = "he"
                elif any('\u0600' <= ch <= '\u06FF' for ch in text_sample):
                    report["basic_info"]["language"] = "ar"
                else:
                    report["basic_info"]["language"] = "en"
                report["warnings"].append("Missing lang attribute on html tag")
        
        except Exception as e:
            report["errors"].append(f"Basic info analysis error: {str(e)}")
        
        # === STRUCTURE ANALYSIS ===
        try:
            all_elements = soup.find_all()
            report["structure"]["total_elements"] = len(all_elements)
            
            # Element counts
            tags = [tag.name for tag in all_elements]
            tag_counts = Counter(tags)
            report["structure"]["element_counts"] = dict(tag_counts.most_common())
            
            # Depth analysis
            def get_element_depth(element, depth=0):
                depths = [depth]
                for child in element.find_all(recursive=False):
                    depths.extend(get_element_depth(child, depth + 1))
                return depths
            
            if soup.body:
                depths = get_element_depth(soup.body)
                report["structure"]["depth_analysis"] = {
                    "max_depth": max(depths) if depths else 0,
                    "avg_depth": sum(depths) / len(depths) if depths else 0,
                    "depth_distribution": dict(Counter(depths))
                }
            
            # Semantic structure
            semantic_tags = ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer']
            report["structure"]["semantic_structure"] = {
                tag: len(soup.find_all(tag)) for tag in semantic_tags
            }
            
        except Exception as e:
            report["errors"].append(f"Structure analysis error: {str(e)}")
        
        # === CONTENT ANALYSIS ===
        try:
            # Text content
            text_content = soup.get_text()
            report["content"]["text_content_length"] = len(text_content)
            
            # Headings analysis
            headings = {}
            for i in range(1, 7):
                h_tags = soup.find_all(f'h{i}')
                headings[f'h{i}'] = [h.get_text(strip=True) for h in h_tags]
            report["content"]["headings"] = headings
            report["accessibility"]["heading_structure"] = [
                f"h{i}" for i in range(1, 7) for _ in soup.find_all(f'h{i}')
            ]
            
            # Other content elements
            report["content"]["paragraphs"] = len(soup.find_all('p'))
            report["content"]["lists"]["ul"] = len(soup.find_all('ul'))
            report["content"]["lists"]["ol"] = len(soup.find_all('ol'))
            report["content"]["tables"] = len(soup.find_all('table'))
            
            # Forms analysis
            forms = soup.find_all('form')
            for form in forms:
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', 'get'),
                    "inputs": [],
                    "has_labels": False
                }
                inputs = form.find_all(['input', 'textarea', 'select'])
                for inp in inputs:
                    input_data = {
                        "type": inp.get('type', inp.name),
                        "name": inp.get('name', ''),
                        "id": inp.get('id', ''),
                        "required": inp.has_attr('required'),
                        "placeholder": inp.get('placeholder', '')
                    }
                    form_data["inputs"].append(input_data)
                
                # Check for labels
                labels = form.find_all('label')
                form_data["has_labels"] = len(labels) > 0
                report["accessibility"]["form_labels"] += len(labels)
                
                report["content"]["forms"].append(form_data)
            
        except Exception as e:
            report["errors"].append(f"Content analysis error: {str(e)}")
        
        # === MEDIA ANALYSIS ===
        try:
            # Images with detailed analysis
            imgs = soup.find_all('img')
            for img in imgs:
                img_data = {
                    "src": img.get('src', ''),
                    "alt": img.get('alt', ''),
                    "width": img.get('width', ''),
                    "height": img.get('height', ''),
                    "loading": img.get('loading', ''),
                    "srcset": img.get('srcset', ''),
                    "sizes": img.get('sizes', ''),
                    "is_lazy": img.get('loading') == 'lazy'
                }
                report["media"]["images"].append(img_data)
                
                if img.get('alt'):
                    report["seo_analysis"]["alt_texts"]["present"] += 1
                else:
                    report["seo_analysis"]["alt_texts"]["missing"] += 1
                    report["warnings"].append(f"Missing alt text for image: {img.get('src', 'unknown')}")
                
                if img.get('loading') == 'lazy':
                    report["performance"]["lazy_loading"] += 1
            
            # Videos
            videos = soup.find_all('video')
            for vid in videos:
                vid_data = {
                    "src": vid.get('src', ''),
                    "controls": vid.has_attr('controls'),
                    "autoplay": vid.has_attr('autoplay'),
                    "loop": vid.has_attr('loop'),
                    "muted": vid.has_attr('muted'),
                    "sources": []
                }
                sources = vid.find_all('source')
                for source in sources:
                    vid_data["sources"].append({
                        "src": source.get('src', ''),
                        "type": source.get('type', '')
                    })
                report["media"]["videos"].append(vid_data)
            
            # Audio
            audios = soup.find_all('audio')
            for aud in audios:
                aud_data = {
                    "src": aud.get('src', ''),
                    "controls": aud.has_attr('controls'),
                    "autoplay": aud.has_attr('autoplay'),
                    "loop": aud.has_attr('loop')
                }
                report["media"]["audio"].append(aud_data)
            
            # iframes
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                iframe_data = {
                    "src": iframe.get('src', ''),
                    "width": iframe.get('width', ''),
                    "height": iframe.get('height', ''),
                    "title": iframe.get('title', ''),
                    "loading": iframe.get('loading', '')
                }
                report["media"]["iframes"].append(iframe_data)
            
            # Canvas and SVG
            report["media"]["canvas"] = len(soup.find_all('canvas'))
            report["media"]["svg"] = len(soup.find_all('svg'))
            
        except Exception as e:
            report["errors"].append(f"Media analysis error: {str(e)}")
        
        # === LINKS ANALYSIS ===
        try:
            links = soup.find_all('a', href=True)
            report["links"]["total_count"] = len(links)
            
            base_domain = urlparse(url).netloc if url else ""
            
            for link in links:
                href = link['href'].strip()
                link_data = {
                    "url": href,
                    "text": link.get_text(strip=True),
                    "title": link.get('title', ''),
                    "target": link.get('target', ''),
                    "rel": link.get('rel', [])
                }
                
                if href.startswith('mailto:'):
                    report["links"]["mailto"].append(link_data)
                elif href.startswith('tel:'):
                    report["links"]["tel"].append(link_data)
                elif href.startswith('#'):
                    report["links"]["anchor"].append(link_data)
                elif href.startswith(('http://', 'https://')):
                    link_domain = urlparse(href).netloc
                    if link_domain == base_domain:
                        report["links"]["internal"].append(link_data)
                    else:
                        report["links"]["external"].append(link_data)
                        report["security"]["external_domains"].append(link_domain)
                else:
                    # Relative links are internal
                    report["links"]["internal"].append(link_data)
            
        except Exception as e:
            report["errors"].append(f"Links analysis error: {str(e)}")
        
        # === TECHNOLOGY STACK ANALYSIS (Enhanced) ===
        try:
            # Enhanced library detection with version extraction
            lib_patterns = {
                'jquery': r'jquery[.-]?(\d+\.\d+\.\d+)?',
                'react': r'react[.-]?(\d+\.\d+\.\d+)?',
                'vue': r'vue[.-]?(\d+\.\d+\.\d+)?',
                'angular': r'angular[.-]?(\d+\.\d+\.\d+)?',
                'bootstrap': r'bootstrap[.-]?(\d+\.\d+\.\d+)?',
                'tailwind': r'tailwind[.-]?(\d+\.\d+\.\d+)?',
                'svelte': r'svelte[.-]?(\d+\.\d+\.\d+)?',
                'wordpress': r'wp-|wordpress',
                'elementor': r'elementor',
                'nextjs': r'_next',
                'nuxtjs': r'_nuxt',
                'font-awesome': r'font[-]?awesome[.-]?(\d+\.\d+\.\d+)?',
                'lodash': r'lodash[.-]?(\d+\.\d+\.\d+)?',
                'moment': r'moment[.-]?(\d+\.\d+\.\d+)?',
                'axios': r'axios[.-]?(\d+\.\d+\.\d+)?',
                'd3': r'd3[.-]?(\d+\.\d+\.\d+)?',
                'three': r'three[.-]?(\d+\.\d+\.\d+)?'
            }
            
            cdn_patterns = [
                'cdnjs.cloudflare.com',
                'unpkg.com',
                'jsdelivr.net',
                'googleapis.com',
                'bootstrapcdn.com',
                'fontawesome.com'
            ]
            
            analytics_patterns = {
                'google-analytics': r'google-analytics|gtag|ga\.js',
                'google-tag-manager': r'googletagmanager',
                'facebook-pixel': r'fbevents\.js|facebook\.net',
                'hotjar': r'hotjar',
                'mixpanel': r'mixpanel',
                'segment': r'segment\.(io|com)'
            }
            
            # Analyze scripts
            scripts = soup.find_all('script')
            for script in scripts:
                src = script.get('src', '').lower()
                if src:
                    # Check if it's a CDN resource
                    is_cdn = any(cdn in src for cdn in cdn_patterns)
                    
                    script_data = {
                        "src": script.get('src'),
                        "type": script.get('type', 'text/javascript'),
                        "async": script.has_attr('async'),
                        "defer": script.has_attr('defer'),
                        "is_cdn": is_cdn,
                        "is_module": script.get('type') == 'module'
                    }
                    
                    if is_cdn:
                        report["technology_stack"]["cdn_resources"].append(script_data)
                    else:
                        report["technology_stack"]["local_resources"].append(script_data)
                    
                    # Library detection with version
                    for lib_name, pattern in lib_patterns.items():
                        match = re.search(pattern, src)
                        if match:
                            version = match.group(1) if match.groups() else "unknown"
                            lib_info = {"name": lib_name, "version": version, "source": src}
                            if lib_info not in report["technology_stack"]["libraries"]:
                                report["technology_stack"]["libraries"].append(lib_info)
                    
                    # Analytics detection
                    for analytics_name, pattern in analytics_patterns.items():
                        if re.search(pattern, src):
                            report["technology_stack"]["analytics"].append({
                                "name": analytics_name,
                                "source": src
                            })
                else:
                    # Inline script
                    report["scripts"]["inline_scripts"] += 1
                    script_content = script.string or ""
                    
                    # Check for common inline patterns
                    if "gtag" in script_content or "ga(" in script_content:
                        report["technology_stack"]["analytics"].append({
                            "name": "google-analytics-inline",
                            "source": "inline"
                        })
            
            # Analyze CSS files
            css_links = soup.find_all('link', rel='stylesheet')
            for link in css_links:
                href = link.get('href', '').lower()
                if href:
                    is_cdn = any(cdn in href for cdn in cdn_patterns)
                    
                    css_data = {
                        "href": link.get('href'),
                        "media": link.get('media', 'all'),
                        "is_cdn": is_cdn
                    }
                    report["styling"]["css_files"].append(css_data)
                    
                    # Framework detection
                    for lib_name, pattern in lib_patterns.items():
                        if re.search(pattern, href):
                            if lib_name not in [lib["name"] for lib in report["styling"]["css_frameworks"]]:
                                report["styling"]["css_frameworks"].append({
                                    "name": lib_name,
                                    "source": href
                                })
            
        except Exception as e:
            report["errors"].append(f"Technology stack analysis error: {str(e)}")
        
        # === STYLING ANALYSIS ===
        try:
            # Inline styles count
            elements_with_style = soup.find_all(attrs={"style": True})
            report["styling"]["inline_styles"] = len(elements_with_style)
            
            # Color extraction (enhanced)
            color_patterns = {
                'hex': r'#([0-9a-fA-F]{3,6})',
                'rgb': r'rgb\((\d+),\s*(\d+),\s*(\d+)\)',
                'rgba': r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\)',
                'hsl': r'hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)',
                'named': r'\b(red|blue|green|yellow|orange|purple|pink|brown|black|white|gray|grey)\b'
            }
            
            all_colors = []
            for pattern_name, pattern in color_patterns.items():
                matches = re.findall(pattern, html, re.IGNORECASE)
                if pattern_name == 'hex':
                    all_colors.extend([f"#{match}" for match in matches])
                elif pattern_name in ['rgb', 'rgba', 'hsl']:
                    all_colors.extend([f"{pattern_name}({','.join(map(str, match))})" for match in matches])
                else:
                    all_colors.extend(matches)
            
            color_counts = Counter(all_colors)
            report["styling"]["color_palette"] = [
                {"color": color, "count": count} 
                for color, count in color_counts.most_common(15)
            ]
            
            # Font detection
            font_patterns = [
                r'font-family:\s*["\']?([^;"\']+)["\']?',
                r'@import\s+url\(["\']?([^)"\']+)["\']?\)',
                r'fonts\.googleapis\.com/css\?family=([^&"\']+)'
            ]
            
            fonts = set()
            for pattern in font_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                fonts.update(matches)
            
            report["styling"]["fonts"] = list(fonts)
            
        except Exception as e:
            report["errors"].append(f"Styling analysis error: {str(e)}")
        
        # === SEO ANALYSIS ===
        try:
            # All meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                content = meta.get('content')
                if name and content:
                    report["seo_analysis"]["meta_tags"][name] = content
                    
                    # Open Graph detection
                    if name.startswith('og:'):
                        report["seo_analysis"]["open_graph"][name] = content
                    
                    # Twitter Cards detection
                    if name.startswith('twitter:'):
                        report["seo_analysis"]["twitter_cards"][name] = content
            
            # Schema markup detection
            schema_scripts = soup.find_all('script', type='application/ld+json')
            for script in schema_scripts:
                try:
                    schema_data = json.loads(script.string or '{}')
                    report["seo_analysis"]["schema_markup"].append(schema_data)
                except json.JSONDecodeError:
                    report["warnings"].append("Invalid JSON-LD schema markup found")
            
        except Exception as e:
            report["errors"].append(f"SEO analysis error: {str(e)}")
        
        # === ACCESSIBILITY ANALYSIS ===
        try:
            # ARIA attributes
            aria_elements = soup.find_all(attrs=lambda x: x and any(attr.startswith('aria-') for attr in x))
            report["accessibility"]["aria_labels"] = len(aria_elements)
            
            # Role attributes
            role_elements = soup.find_all(attrs={"role": True})
            report["accessibility"]["aria_roles"] = [elem.get('role') for elem in role_elements]
            
            # Alt attributes (already counted in media analysis)
            report["accessibility"]["alt_attributes"] = report["seo_analysis"]["alt_texts"]["present"]
            
            # Skip links
            skip_links = soup.find_all('a', href=lambda x: x and x.startswith('#'))
            skip_link_texts = [link.get_text(strip=True).lower() for link in skip_links]
            report["accessibility"]["skip_links"] = len([text for text in skip_link_texts if 'skip' in text])
            
        except Exception as e:
            report["errors"].append(f"Accessibility analysis error: {str(e)}")
        
        # === UI COMPONENTS ANALYSIS ===
        try:
            # Buttons (enhanced)
            buttons = soup.find_all(['button', 'input'])
            button_data = []
            for btn in buttons:
                if btn.name == 'input' and btn.get('type') not in ['button', 'submit', 'reset']:
                    continue
                
                btn_info = {
                    "type": btn.get('type', 'button'),
                    "text": btn.get_text(strip=True) or btn.get('value', ''),
                    "id": btn.get('id', ''),
                    "class": btn.get('class', []),
                    "disabled": btn.has_attr('disabled'),
                    "aria_label": btn.get('aria-label', '')
                }
                button_data.append(btn_info)
            
            # Also check for links with button role
            button_links = soup.find_all('a', attrs={'role': 'button'})
            for link in button_links:
                btn_info = {
                    "type": "link-button",
                    "text": link.get_text(strip=True),
                    "href": link.get('href', ''),
                    "class": link.get('class', []),
                    "aria_label": link.get('aria-label', '')
                }
                button_data.append(btn_info)
            
            report["ui_components"]["buttons"] = button_data
            
            # Navigation detection
            nav_elements = soup.find_all(['nav', 'ul', 'ol'])
            nav_data = []
            for nav in nav_elements:
                if nav.name == 'nav' or 'nav' in (nav.get('class') or []):
                    nav_info = {
                        "tag": nav.name,
                        "class": nav.get('class', []),
                        "id": nav.get('id', ''),
                        "links": len(nav.find_all('a'))
                    }
                    nav_data.append(nav_info)
            
            report["ui_components"]["navigation"] = nav_data
            
            # Modal detection (common patterns)
            modal_selectors = [
                '[class*="modal"]',
                '[class*="popup"]',
                '[class*="dialog"]',
                '[role="dialog"]'
            ]
            modals = 0
            for selector in modal_selectors:
                try:
                    modals += len(soup.select(selector))
                except:
                    pass
            report["ui_components"]["modals"] = modals
            
            # Carousel detection
            carousel_selectors = [
                '[class*="carousel"]',
                '[class*="slider"]',
                '[class*="swiper"]'
            ]
            carousels = 0
            for selector in carousel_selectors:
                try:
                    carousels += len(soup.select(selector))
                except:
                    pass
            report["ui_components"]["carousels"] = carousels
            
        except Exception as e:
            report["errors"].append(f"UI components analysis error: {str(e)}")
        
        # === PERFORMANCE ANALYSIS ===
        try:
            # Count total external requests
            external_resources = (
                len(report["styling"]["css_files"]) +
                len(report["technology_stack"]["cdn_resources"]) +
                len(report["technology_stack"]["local_resources"]) +
                len([img for img in report["media"]["images"] if img["src"].startswith(('http', '//'))])
            )
            report["performance"]["total_requests"] = external_resources
            
            # Image optimization analysis
            total_images = len(report["media"]["images"])
            images_with_alt = report["seo_analysis"]["alt_texts"]["present"]
            lazy_images = report["performance"]["lazy_loading"]
            responsive_images = len([img for img in report["media"]["images"] if img["srcset"]])
            
            report["performance"]["image_optimization"] = {
                "total_images": total_images,
                "with_alt_text": images_with_alt,
                "lazy_loaded": lazy_images,
                "responsive": responsive_images,
                "optimization_score": (images_with_alt + lazy_images + responsive_images) / (total_images * 3) if total_images > 0 else 0
            }
            
            # Preload hints
            preload_links = soup.find_all('link', rel='preload')
            for link in preload_links:
                report["performance"]["preload_hints"].append({
                    "href": link.get('href', ''),
                    "as": link.get('as', ''),
                    "type": link.get('type', '')
                })
            
        except Exception as e:
            report["errors"].append(f"Performance analysis error: {str(e)}")
        
        # === RECOMMENDATIONS ===
        try:
            # Generate recommendations based on analysis
            if report["seo_analysis"]["alt_texts"]["missing"] > 0:
                report["recommendations"].append(f"Add alt text to {report['seo_analysis']['alt_texts']['missing']} images for better SEO and accessibility")
            
            if not report["basic_info"]["viewport"]:
                report["recommendations"].append("Add viewport meta tag for mobile responsiveness")
            
            if report["performance"]["lazy_loading"] == 0 and len(report["media"]["images"]) > 5:
                report["recommendations"].append("Consider implementing lazy loading for images to improve performance")
            
            if len(report["styling"]["css_files"]) > 5:
                report["recommendations"].append("Consider combining CSS files to reduce HTTP requests")
            
            if report["accessibility"]["aria_labels"] == 0:
                report["recommendations"].append("Add ARIA labels for better accessibility")
            
            if not report["seo_analysis"]["open_graph"]:
                report["recommendations"].append("Add Open Graph meta tags for better social media sharing")
            
        except Exception as e:
            report["errors"].append(f"Recommendations generation error: {str(e)}")
        
    except Exception as e:
        report["errors"].append(f"Critical analysis error: {str(e)}")
    
    return report

# --- DeepSeek API Function ---
# Global variable for the API key that will be set properly later
DEEPSEEK_API_KEY = ""
def deepseek_chat(messages, system_prompt="You are a helpful AI assistant.", temperature=0.7, max_tokens=None, retry_count=3):
    """Call the DeepSeek API for chat completion with retry logic."""
    """Call the DeepSeek API for chat completion. This function is thread-safe."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API key is required but not provided")
        
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            *messages
        ],
        "temperature": temperature
    }
    
    # Add max_tokens if specified
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    # Add retry logic for API resilience
    for attempt in range(retry_count):
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                },
                json=payload,
                timeout=30  # Add timeout for better error handling
            )
            
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            if attempt < retry_count - 1:
                # Exponential backoff: wait 2^attempt seconds before retrying
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise ValueError(f"Failed to call DeepSeek API after {retry_count} attempts: {e}")

# --- Cache Implementation ---
# Create a disk-based cache for storing crawl results
import diskcache
import os
import hashlib

# Create cache directory if it doesn't exist
if not os.path.exists("cache"):
    os.makedirs("cache")

# Initialize disk cache
cache = diskcache.Cache("cache")

def get_cache_key(url, depth, max_pages, domain_restriction):
    """Generate a unique cache key based on crawl parameters"""
    key_string = f"{url}_{depth}_{max_pages}_{domain_restriction}"
    return hashlib.md5(key_string.encode()).hexdigest()

def cache_crawl_results(key, results):
    """Store crawl results in cache"""
    cache[key] = results
    cache[f"{key}_timestamp"] = datetime.datetime.now()

def get_cached_results(key):
    """Retrieve crawl results from cache if available and not expired"""
    if key in cache:
        timestamp = cache.get(f"{key}_timestamp")
        # Check if cache is less than 24 hours old
        if timestamp and (datetime.datetime.now() - timestamp).total_seconds() < 86400:
            return cache[key]
    return None

# --- Sentiment Analysis ---
from textblob import TextBlob

def analyze_sentiment(text):
    """Analyze sentiment of text using TextBlob"""
    analysis = TextBlob(text)
    # Return polarity (-1 to 1) and subjectivity (0 to 1)
    return {
        "polarity": analysis.sentiment.polarity,
        "subjectivity": analysis.sentiment.subjectivity,
        "sentiment": "positive" if analysis.sentiment.polarity > 0.1 else 
                   "negative" if analysis.sentiment.polarity < -0.1 else "neutral"
    }

# --- URL Health Monitoring ---
def check_url_health(url):
    """Check if a URL is healthy and responsive"""
    try:
        start_time = time.time()
        response = requests.head(url, timeout=5)
        response_time = time.time() - start_time
        return {
            "status_code": response.status_code,
            "response_time": response_time,
            "is_healthy": 200 <= response.status_code < 400,
            "headers": dict(response.headers)
        }
    except Exception as e:
        return {
            "status_code": 0,
            "response_time": 0,
            "is_healthy": False,
            "error": str(e)
        }

# --- Technical Report Visualization Functions ---
def create_element_distribution_chart(element_counts):
    """Create a pie chart for HTML element distribution"""
    if not element_counts:
        return None
    
    # Get top 10 elements for better visualization
    top_elements = dict(list(element_counts.items())[:10])
    
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = cm.Set3(np.linspace(0, 1, len(top_elements)))
    
    wedges, texts, autotexts = ax.pie(
        list(top_elements.values()), 
        labels=list(top_elements.keys()),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    
    ax.set_title('HTML Element Distribution', fontsize=16, fontweight='bold')
    
    # Enhance text readability
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    plt.tight_layout()
    return fig

def create_color_palette_visualization(color_palette):
    """Create a visual representation of the color palette"""
    if not color_palette:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = []
    counts = []
    labels = []
    
    def is_valid_color(color_str):
        """Check if a color string is valid for matplotlib"""
        try:
            # Try to convert the color - if it fails, it's invalid
            mcolors.to_rgba(color_str)
            return True
        except (ValueError, TypeError):
            return False
    
    def sanitize_color(color_str):
        """Sanitize color string for matplotlib"""
        if not color_str or not isinstance(color_str, str):
            return '#808080'  # Default gray
        
        color_str = color_str.strip()
        
        # If it's already a valid color, return it
        if is_valid_color(color_str):
            return color_str
        
        # Try to fix common issues
        if color_str.startswith('rgb(') and color_str.endswith(')'):
            # Extract RGB values and convert to hex
            try:
                rgb_str = color_str[4:-1]  # Remove 'rgb(' and ')'
                rgb_values = [int(x.strip()) for x in rgb_str.split(',')]
                if len(rgb_values) == 3 and all(0 <= v <= 255 for v in rgb_values):
                    return f'#{rgb_values[0]:02x}{rgb_values[1]:02x}{rgb_values[2]:02x}'
            except (ValueError, IndexError):
                pass
        
        # If color doesn't start with #, try adding it
        if not color_str.startswith('#') and len(color_str) in [3, 6]:
            test_color = f'#{color_str}'
            if is_valid_color(test_color):
                return test_color
        
        # Return default gray if all else fails
        return '#808080'
    
    for item in color_palette[:10]:  # Show top 10 colors
        original_color = item['color']
        count = item['count']
        
        # Sanitize the color for matplotlib
        safe_color = sanitize_color(original_color)
        
        colors.append(safe_color)
        counts.append(count)
        labels.append(f"{original_color}\n({count} uses)")
    
    # Create horizontal bar chart with sanitized colors
    bars = ax.barh(range(len(colors)), counts, color=colors)
    
    ax.set_yticks(range(len(colors)))
    ax.set_yticklabels(labels)
    ax.set_xlabel('Usage Count')
    ax.set_title('Color Palette Usage', fontsize=16, fontweight='bold')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                str(counts[i]), ha='left', va='center')
    
    plt.tight_layout()
    return fig

def create_technology_stack_chart(tech_stack):
    """Create a visualization for technology stack"""
    if not tech_stack.get('libraries') and not tech_stack.get('frameworks'):
        return None
    
    # Combine libraries and frameworks
    all_tech = []
    if tech_stack.get('libraries'):
        for lib in tech_stack['libraries']:
            all_tech.append(f"{lib['name']} ({lib.get('version', 'unknown')})")
    
    if tech_stack.get('frameworks'):
        for fw in tech_stack['frameworks']:
            all_tech.append(fw['name'])
    
    if tech_stack.get('css_frameworks'):
        for css_fw in tech_stack['css_frameworks']:
            all_tech.append(f"{css_fw['name']} (CSS)")
    
    if not all_tech:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create horizontal bar chart
    y_pos = np.arange(len(all_tech))
    counts = [1] * len(all_tech)  # Each technology appears once
    
    bars = ax.barh(y_pos, counts, color=cm.tab10(np.linspace(0, 1, len(all_tech))))
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(all_tech)
    ax.set_xlabel('Detected')
    ax.set_title('Technology Stack', fontsize=16, fontweight='bold')
    
    # Remove x-axis ticks since they're not meaningful
    ax.set_xticks([])
    
    plt.tight_layout()
    return fig

def create_performance_metrics_chart(performance_data):
    """Create a performance metrics visualization"""
    if not performance_data:
        return None
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Total Requests
    ax1.bar(['Total Requests'], [performance_data.get('total_requests', 0)], 
            color='skyblue')
    ax1.set_title('External Requests')
    ax1.set_ylabel('Count')
    
    # 2. Image Optimization Score
    img_opt = performance_data.get('image_optimization', {})
    if img_opt:
        score = img_opt.get('optimization_score', 0) * 100
        ax2.pie([score, 100-score], labels=['Optimized', 'Not Optimized'], 
                colors=['green', 'red'], autopct='%1.1f%%')
        ax2.set_title('Image Optimization Score')
    
    # 3. Lazy Loading
    lazy_count = performance_data.get('lazy_loading', 0)
    total_images = img_opt.get('total_images', 1) if img_opt else 1
    non_lazy = max(0, total_images - lazy_count)
    
    ax3.bar(['Lazy Loaded', 'Not Lazy'], [lazy_count, non_lazy], 
            color=['green', 'orange'])
    ax3.set_title('Image Lazy Loading')
    ax3.set_ylabel('Count')
    
    # 4. Preload Hints
    preload_count = len(performance_data.get('preload_hints', []))
    ax4.bar(['Preload Hints'], [preload_count], color='purple')
    ax4.set_title('Resource Preload Hints')
    ax4.set_ylabel('Count')
    
    plt.tight_layout()
    return fig

def create_seo_accessibility_dashboard(seo_data, accessibility_data):
    """Create SEO and Accessibility metrics dashboard"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Alt Text Coverage
    alt_present = seo_data.get('alt_texts', {}).get('present', 0)
    alt_missing = seo_data.get('alt_texts', {}).get('missing', 0)
    
    if alt_present + alt_missing > 0:
        ax1.pie([alt_present, alt_missing], 
                labels=['With Alt Text', 'Missing Alt Text'],
                colors=['green', 'red'], autopct='%1.1f%%')
        ax1.set_title('Image Alt Text Coverage')
    else:
        ax1.text(0.5, 0.5, 'No Images Found', ha='center', va='center', transform=ax1.transAxes)
        ax1.set_title('Image Alt Text Coverage')
    
    # 2. Title and Description Length
    title_len = seo_data.get('title_length', 0)
    desc_len = seo_data.get('description_length', 0)
    
    lengths = ['Title', 'Description']
    values = [title_len, desc_len]
    colors = []
    
    # Color code based on SEO best practices
    colors.append('green' if 30 <= title_len <= 60 else 'orange' if title_len > 0 else 'red')
    colors.append('green' if 120 <= desc_len <= 160 else 'orange' if desc_len > 0 else 'red')
    
    ax2.bar(lengths, values, color=colors)
    ax2.set_title('SEO Meta Length')
    ax2.set_ylabel('Characters')
    ax2.axhline(y=30, color='gray', linestyle='--', alpha=0.5)  # Min title length
    ax2.axhline(y=60, color='gray', linestyle='--', alpha=0.5)  # Max title length
    
    # 3. Accessibility Features
    aria_labels = accessibility_data.get('aria_labels', 0)
    form_labels = accessibility_data.get('form_labels', 0)
    skip_links = accessibility_data.get('skip_links', 0)
    lang_attrs = accessibility_data.get('lang_attributes', 0)
    
    features = ['ARIA Labels', 'Form Labels', 'Skip Links', 'Lang Attributes']
    counts = [aria_labels, form_labels, skip_links, lang_attrs]
    
    ax3.bar(features, counts, color='lightblue')
    ax3.set_title('Accessibility Features')
    ax3.set_ylabel('Count')
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Social Media Tags
    og_count = len(seo_data.get('open_graph', {}))
    twitter_count = len(seo_data.get('twitter_cards', {}))
    schema_count = len(seo_data.get('schema_markup', []))
    
    social_features = ['Open Graph', 'Twitter Cards', 'Schema Markup']
    social_counts = [og_count, twitter_count, schema_count]
    
    ax4.bar(social_features, social_counts, color='lightcoral')
    ax4.set_title('Social Media & Schema')
    ax4.set_ylabel('Count')
    
    plt.tight_layout()
    return fig

def generate_website_blueprint(report):
    """Generate a comprehensive blueprint for rebuilding the website"""
    blueprint = {
        "metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "url": report["url"],
            "title": report["basic_info"]["title"],
            "language": report["basic_info"]["language"]
        },
        "html_structure": {
            "doctype": "<!DOCTYPE html>",
            "html_attributes": {
                "lang": report["basic_info"]["language"]
            },
            "head": {
                "meta_tags": {
                    "charset": report["basic_info"]["charset"] or "UTF-8",
                    "viewport": report["basic_info"]["viewport"] or "width=device-width, initial-scale=1.0",
                    "title": report["basic_info"]["title"],
                    "description": report["basic_info"]["description"]
                },
                "additional_meta": report["seo_analysis"]["meta_tags"],
                "open_graph": report["seo_analysis"]["open_graph"],
                "twitter_cards": report["seo_analysis"]["twitter_cards"],
                "favicon": report["basic_info"]["favicon"],
                "css_files": report["styling"]["css_files"],
                "preload_hints": report["performance"]["preload_hints"]
            }
        },
        "body_structure": {
            "semantic_elements": report["structure"]["semantic_structure"],
            "total_elements": report["structure"]["total_elements"],
            "element_distribution": report["structure"]["element_counts"],
            "depth_analysis": report["structure"]["depth_analysis"]
        },
        "content_blueprint": {
            "headings": report["content"]["headings"],
            "paragraphs": report["content"]["paragraphs"],
            "lists": report["content"]["lists"],
            "tables": report["content"]["tables"],
            "forms": report["content"]["forms"],
            "text_content_length": report["content"]["text_content_length"]
        },
        "media_assets": {
            "images": report["media"]["images"],
            "videos": report["media"]["videos"],
            "audio": report["media"]["audio"],
            "iframes": report["media"]["iframes"],
            "canvas_elements": report["media"]["canvas"],
            "svg_elements": report["media"]["svg"]
        },
        "navigation_structure": {
            "internal_links": report["links"]["internal"],
            "external_links": report["links"]["external"],
            "anchor_links": report["links"]["anchor"],
            "mailto_links": report["links"]["mailto"],
            "tel_links": report["links"]["tel"],
            "navigation_components": report["ui_components"]["navigation"]
        },
        "styling_guide": {
            "color_palette": report["styling"]["color_palette"],
            "fonts": report["styling"]["fonts"],
            "css_files": report["styling"]["css_files"],
            "css_frameworks": report["styling"]["css_frameworks"],
            "inline_styles_count": report["styling"]["inline_styles"]
        },
        "javascript_blueprint": {
            "external_scripts": report["technology_stack"]["cdn_resources"] + report["technology_stack"]["local_resources"],
            "inline_scripts_count": report["scripts"]["inline_scripts"],
            "libraries": report["technology_stack"]["libraries"],
            "analytics": report["technology_stack"]["analytics"]
        },
        "ui_components": {
            "buttons": report["ui_components"]["buttons"],
            "forms": report["ui_components"]["forms"],
            "navigation": report["ui_components"]["navigation"],
            "modals": report["ui_components"]["modals"],
            "carousels": report["ui_components"]["carousels"]
        },
        "performance_requirements": {
            "lazy_loading": report["performance"]["lazy_loading"] > 0,
            "image_optimization": report["performance"]["image_optimization"],
            "total_requests": report["performance"]["total_requests"],
            "preload_hints": report["performance"]["preload_hints"]
        },
        "seo_requirements": {
            "title_optimization": {
                "current_length": report["seo_analysis"]["title_length"],
                "recommended_range": "30-60 characters"
            },
            "description_optimization": {
                "current_length": report["seo_analysis"]["description_length"],
                "recommended_range": "120-160 characters"
            },
            "alt_text_coverage": report["seo_analysis"]["alt_texts"],
            "schema_markup": report["seo_analysis"]["schema_markup"],
            "open_graph": report["seo_analysis"]["open_graph"],
            "twitter_cards": report["seo_analysis"]["twitter_cards"]
        },
        "accessibility_requirements": {
            "aria_labels": report["accessibility"]["aria_labels"],
            "aria_roles": report["accessibility"]["aria_roles"],
            "form_labels": report["accessibility"]["form_labels"],
            "skip_links": report["accessibility"]["skip_links"],
            "heading_structure": report["accessibility"]["heading_structure"],
            "lang_attributes": report["accessibility"]["lang_attributes"]
        },
        "security_considerations": {
            "external_domains": list(set(report["security"]["external_domains"])),
            "mixed_content": report["security"]["mixed_content"],
            "security_headers": report["security"]["security_headers"]
        },
        "implementation_guide": {
            "critical_warnings": report["warnings"],
            "errors_to_fix": report["errors"],
            "recommendations": report["recommendations"],
            "priority_tasks": []
        }
    }
    
    # Generate priority tasks based on analysis
    priority_tasks = []
    
    if report["seo_analysis"]["alt_texts"]["missing"] > 0:
        priority_tasks.append({
            "priority": "HIGH",
            "task": "Add alt text to images",
            "count": report["seo_analysis"]["alt_texts"]["missing"],
            "impact": "SEO and Accessibility"
        })
    
    if not report["basic_info"]["viewport"]:
        priority_tasks.append({
            "priority": "HIGH",
            "task": "Add viewport meta tag",
            "impact": "Mobile responsiveness"
        })
    
    if report["performance"]["lazy_loading"] == 0 and len(report["media"]["images"]) > 5:
        priority_tasks.append({
            "priority": "MEDIUM",
            "task": "Implement lazy loading for images",
            "count": len(report["media"]["images"]),
            "impact": "Performance optimization"
        })
    
    if len(report["styling"]["css_files"]) > 5:
        priority_tasks.append({
            "priority": "MEDIUM",
            "task": "Optimize CSS loading",
            "count": len(report["styling"]["css_files"]),
            "impact": "Performance optimization"
        })
    
    if report["accessibility"]["aria_labels"] == 0:
        priority_tasks.append({
            "priority": "MEDIUM",
            "task": "Add ARIA labels for accessibility",
            "impact": "Accessibility compliance"
        })
    
    blueprint["implementation_guide"]["priority_tasks"] = priority_tasks
    
    return blueprint

def generate_html_template(blueprint):
    """Generate a basic HTML template based on the blueprint"""
    html_template = f"""<!DOCTYPE html>
<html lang="{blueprint['html_structure']['html_attributes']['lang']}">
<head>
    <meta charset="{blueprint['html_structure']['head']['meta_tags']['charset']}">
    <meta name="viewport" content="{blueprint['html_structure']['head']['meta_tags']['viewport']}">
    <title>{blueprint['html_structure']['head']['meta_tags']['title']}</title>
    <meta name="description" content="{blueprint['html_structure']['head']['meta_tags']['description']}">
    
    <!-- Open Graph Meta Tags -->"""
    
    for og_key, og_value in blueprint['html_structure']['head']['open_graph'].items():
        html_template += f'\n    <meta property="{og_key}" content="{og_value}">'
    
    html_template += """
    
    <!-- CSS Files -->"""
    
    for css_file in blueprint['styling_guide']['css_files']:
        media = css_file.get('media', 'all')
        html_template += f'\n    <link rel="stylesheet" href="{css_file["href"]}" media="{media}">'
    
    html_template += """
    
    <!-- Preload Hints -->"""
    
    for preload in blueprint['performance_requirements']['preload_hints']:
        html_template += f'\n    <link rel="preload" href="{preload["href"]}" as="{preload["as"]}">'
    
    html_template += """
</head>
<body>
    <!-- Page structure based on semantic analysis -->"""
    
    semantic = blueprint['body_structure']['semantic_elements']
    if semantic.get('header', 0) > 0:
        html_template += """
    <header>
        <!-- Header content -->
    </header>"""
    
    if semantic.get('nav', 0) > 0:
        html_template += """
    
    <nav>
        <!-- Navigation content -->
    </nav>"""
    
    if semantic.get('main', 0) > 0:
        html_template += """
    
    <main>"""
    else:
        html_template += """
    
    <div class="main-content">"""
    
    # Add sections based on content analysis
    headings = blueprint['content_blueprint']['headings']
    for h_level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        if headings.get(h_level):
            for heading_text in headings[h_level][:3]:  # Show first 3 headings as examples
                html_template += f'\n        <{h_level}>{heading_text}</{h_level}>'
    
    if semantic.get('main', 0) > 0:
        html_template += """
    </main>"""
    else:
        html_template += """
    </div>"""
    
    if semantic.get('aside', 0) > 0:
        html_template += """
    
    <aside>
        <!-- Sidebar content -->
    </aside>"""
    
    if semantic.get('footer', 0) > 0:
        html_template += """
    
    <footer>
        <!-- Footer content -->
    </footer>"""
    
    html_template += """
    
    <!-- JavaScript Files -->"""
    
    for script in blueprint['javascript_blueprint']['external_scripts']:
        async_attr = ' async' if script.get('async') else ''
        defer_attr = ' defer' if script.get('defer') else ''
        html_template += f'\n    <script src="{script["src"]}"{async_attr}{defer_attr}></script>'
    
    html_template += """
</body>
</html>"""
    
    return html_template

def main():
    """Main application function"""
    # Initialize theme in session state if not already present
    if 'theme' not in st.session_state:
        st.session_state.theme = "Futuristic"  # Default to Futuristic theme
        # Theme selector with new futuristic option
        theme = st.sidebar.radio("Select Theme", ["Futuristic", "Dark", "Light", "Blue"], index=0)
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # Define CSS for different themes
    dark_theme = """
    <style>
    .stApp {background-color: #121212 !important;}
    .card {background-color: #1E1E1E !important; color: #E0E0E0 !important;}
    .main-header {color: #BB86FC !important;}
    .stTextInput>div>div>input {background-color: #333 !important; color: white !important;}
    .stSelectbox>div>div>div {background-color: #333 !important; color: white !important;}
    .stTabs [data-baseweb="tab-list"] {background-color: #1E1E1E !important;}
    .stTabs [data-baseweb="tab"] {color: #E0E0E0 !important;}
    .stTabs [aria-selected="true"] {background-color: #333 !important;}
    .stMarkdown {color: #E0E0E0 !important;}
    .stDataFrame {color: #E0E0E0 !important;}
    .stButton>button {background-color: #333 !important; color: white !important;}
    .stExpander {background-color: #1E1E1E !important; color: #E0E0E0 !important;}
    .stRadio>div {color: #E0E0E0 !important;}
    .stSidebar .stButton>button {background-color: #444 !important; color: white !important;}
    </style>
    """

    light_theme = """
    <style>
    .stApp {background-color: #FFFFFF !important;}
    .card {background-color: #F8F9FA !important; color: #212529 !important;}
    .main-header {color: #0D6EFD !important;}
    </style>
    """

    blue_theme = """
    <style>
    .stApp {background-color: #E3F2FD !important;}
    .card {background-color: white !important;}
    .main-header {color: #0D47A1 !important;}
    </style>
    """

    # New futuristic theme with glassmorphism and neon effects
    futuristic_theme = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e) !important;
        background-size: 400% 400% !important;
        animation: gradient 15s ease infinite !important;
        font-family: 'Orbitron', sans-serif !important;
    }

    @keyframes gradient {
        0% { background-position: 0% 50% !important; }
        50% { background-position: 100% 50% !important; }
        100% { background-position: 0% 50% !important; }
    }

    .card {
        background: rgba(25, 25, 35, 0.7) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #e0f7fa !important;
        margin-bottom: 20px !important;
        padding: 20px !important;
    }

    .main-header {
        color: #80deea !important;
        text-shadow: 0 0 10px rgba(128, 222, 234, 0.7), 0 0 20px rgba(128, 222, 234, 0.5) !important;
        font-weight: 700 !important;
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 2px !important;
    }

    .stTextInput>div>div>input {
        background-color: rgba(30, 30, 40, 0.8) !important;
        color: #e0f7fa !important;
        border: 1px solid rgba(128, 222, 234, 0.5) !important;
        border-radius: 8px !important;
    }

    .stSelectbox>div>div>div {
        background-color: rgba(30, 30, 40, 0.8) !important;
        color: #e0f7fa !important;
        border: 1px solid rgba(128, 222, 234, 0.5) !important;
        border-radius: 8px !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(25, 25, 35, 0.5) !important;
        border-radius: 8px !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: #80deea !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: rgba(128, 222, 234, 0.2) !important;
        border-bottom: 2px solid #80deea !important;
    }

    .stMarkdown {
        color: #e0f7fa !important;
    }

    .stDataFrame {
        color: #e0f7fa !important;
    }

    .stButton>button {
        background: linear-gradient(45deg, #00bcd4, #80deea) !important;
        color: #0f2027 !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 0 10px rgba(0, 188, 212, 0.5) !important;
        transition: all 0.3s ease !important;
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 500 !important;
        letter-spacing: 1px !important;
    }

    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 15px rgba(0, 188, 212, 0.8) !important;
    }

    .stExpander {
        background-color: rgba(25, 25, 35, 0.7) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(128, 222, 234, 0.3) !important;
        color: #e0f7fa !important;
    }

    .stRadio>div {
        color: #e0f7fa !important;
    }

    .stSidebar .stButton>button {
        background: linear-gradient(45deg, #00bcd4, #80deea) !important;
        color: #0f2027 !important;
        border-radius: 8px !important;
    }

    /* Custom progress bar */
    .stProgress > div > div > div > div {
        background-color: #00bcd4 !important;
        background: linear-gradient(90deg, #00bcd4, #80deea) !important;
        box-shadow: 0 0 10px rgba(0, 188, 212, 0.7) !important;
    }

    /* Custom sidebar */
    .css-1d391kg, .css-12oz5g7 {
        background: rgba(15, 15, 25, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
    }

    /* Custom metric */
    .stMetric {
        background: rgba(25, 25, 35, 0.7) !important;
        border-radius: 8px !important;
        padding: 10px !important;
        border: 1px solid rgba(128, 222, 234, 0.3) !important;
    }

    /* Pulsing effect for important elements */
    .pulse {
        animation: pulse 2s infinite !important;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 188, 212, 0.7) !important; }
        70% { box-shadow: 0 0 0 10px rgba(0, 188, 212, 0) !important; }
        100% { box-shadow: 0 0 0 0 rgba(0, 188, 212, 0) !important; }
    }
    </style>
    """

    # Apply theme based on session state
    if st.session_state.theme == "Dark":
        st.markdown(dark_theme, unsafe_allow_html=True)
    elif st.session_state.theme == "Light":
        st.markdown(light_theme, unsafe_allow_html=True)
    elif st.session_state.theme == "Blue":
        st.markdown(blue_theme, unsafe_allow_html=True)
    elif st.session_state.theme == "Futuristic":
        st.markdown(futuristic_theme, unsafe_allow_html=True)
        st.title("Settings")
        st.markdown('<div class="card">', unsafe_allow_html=True)
    
        # Cache settings with futuristic styling
        st.markdown('<h3 class="main-header">Cache Settings</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
    
        with col1:
            if st.button("🧹 Clear Session Cache"):
                # Clear session state for cached data
                for key in ["crawl_results", "pages_text", "technical_report", "summaries", "qa_results"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Session cache cleared successfully!")
    
        with col2:
            if st.button("🗑️ Clear Disk Cache"):
                # Clear disk cache
                try:
                    cache.clear()
                    st.success("Disk cache cleared successfully!")
                except Exception as e:
                    st.error(f"Error clearing disk cache: {e}")
    
        # Add color preview boxes
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div style="background-color: #FFFFFF; color: #000000; padding: 10px; border-radius: 5px; text-align: center;">Light</div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="background-color: #121212; color: #E0E0E0; padding: 10px; border-radius: 5px; text-align: center;">Dark</div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div style="background-color: #E3F2FD; color: #0D47A1; padding: 10px; border-radius: 5px; text-align: center;">Blue</div>
            """, unsafe_allow_html=True)
    
        # Theme settings outside of form
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h3 class="main-header">Theme Settings</h3>', unsafe_allow_html=True)
    
        # Store theme preference in session state
        theme_options = ["Futuristic", "Light", "Dark", "Blue"]
        current_theme = st.session_state.theme if st.session_state.theme in theme_options else "Futuristic"
        theme = st.selectbox("Select Theme", theme_options, 
                           index=theme_options.index(current_theme),
                           key="theme_select")
    
        if st.button("Apply Theme", key="apply_theme_btn"):
            st.session_state.theme = theme
            st.rerun()
    
        st.markdown('</div>', unsafe_allow_html=True)
    
        # API Key management
        st.subheader("API Keys")
    
        # DeepSeek API Key input
        deepseek_key = st.text_input("DeepSeek API Key", type="password", 
                                    help="Enter your DeepSeek API key for AI analysis")
    
        if st.button("Save API Key"):
            if deepseek_key:
                # Save to session state (in production, save to secrets)
                st.session_state.deepseek_api_key = deepseek_key
                st.success("API Key saved successfully!")
            else:
                st.error("Please enter a valid API key")
    
        st.markdown('</div>', unsafe_allow_html=True)

    # --- UI Inputs ---
    # Add a sidebar for better navigation
    st.sidebar.title("Navigation")

    # Navigation with futuristic styling
    st.sidebar.markdown('<div class="card">', unsafe_allow_html=True)
    st.sidebar.markdown('<h3 class="main-header">Navigation</h3>', unsafe_allow_html=True)
    page = st.sidebar.radio("Go to", ["Scraper", "Analytics", "Settings"])
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # WhatsApp Integration Settings in Sidebar
    if WHATSAPP_AVAILABLE:
        st.sidebar.markdown('<div class="card">', unsafe_allow_html=True)
        st.sidebar.markdown('<h3 class="main-header">📱 WhatsApp Integration</h3>', unsafe_allow_html=True)
    
        whatsapp_client = get_whatsapp_client()
    
        if whatsapp_client.is_configured():
            st.sidebar.success("✅ WhatsApp Configured")
            status = whatsapp_client.get_instance_status()
            st.sidebar.caption(f"Status: {status.get('status', 'Unknown')}")
        else:
            st.sidebar.warning("⚠️ WhatsApp Not Configured")
    
        if st.sidebar.button("⚙️ Configure WhatsApp"):
            st.session_state.show_whatsapp_config = True
    
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # Main content based on navigation
    if page == "Analytics":
        st.markdown('<h1 class="main-header">Analytics Dashboard</h1>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
    
        if st.session_state.get("crawl_results"):
            # URL Health Monitoring
            st.markdown('<h3 class="main-header">URL Health Monitoring</h3>', unsafe_allow_html=True)
        
            # Select URLs to check health
            urls_to_check = [result['url'] for result in st.session_state.crawl_results[:10]]  # Limit to first 10 URLs
            selected_urls = st.multiselect("Select URLs to check health status", urls_to_check, default=urls_to_check[:3])
        
            if st.button("🔍 Check URL Health"):
                health_results = []
                progress_bar = st.progress(0)
            
                for i, url in enumerate(selected_urls):
                    health_data = check_url_health(url)
                    health_results.append({
                        "URL": url,
                        "Status Code": health_data["status_code"],
                        "Response Time (s)": health_data["response_time"],
                        "Is Healthy": health_data["is_healthy"]
                    })
                    progress_bar.progress((i + 1) / len(selected_urls))
            
                # Display health results
                health_df = pd.DataFrame(health_results)
                st.session_state.health_results = health_df
            
                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    healthy_count = health_df[health_df["Is Healthy"] == True].shape[0]
                    st.metric("Healthy URLs", healthy_count, f"{healthy_count/len(health_df)*100:.1f}%")
                with col2:
                    avg_response = health_df["Response Time (s)"].mean()
                    st.metric("Avg Response Time", f"{avg_response:.3f}s")
                with col3:
                    status_ok = health_df[health_df["Status Code"] == 200].shape[0]
                    st.metric("Status 200 OK", status_ok, f"{status_ok/len(health_df)*100:.1f}%")
            
                # Display detailed health data
                st.dataframe(health_df)
        else:
            st.info("Run a crawl first to access analytics features.")
    
        st.markdown('</div>', unsafe_allow_html=True)

    elif page == "Settings":
        st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)
    
        # WhatsApp Configuration Section
        if WHATSAPP_AVAILABLE:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<h3 class="main-header">📱 WhatsApp Integration</h3>', unsafe_allow_html=True)
        
            # Initialize session state for WhatsApp config
            if 'whatsapp_configured' not in st.session_state:
                st.session_state.whatsapp_configured = False
        
            whatsapp_client = get_whatsapp_client()
        
            st.markdown("Configure your WaPulse WhatsApp integration:")
        
            # Help information
            with st.expander("ℹ️ How to get WaPulse credentials"):
                st.markdown("""
                **Steps to get your WaPulse credentials:**
            
                1. **Sign up** at [WaPulse](https://wapulse.com)
                2. **Create an instance** in your dashboard
                3. **Copy your Instance ID** from the instance details
                4. **Generate an API token** in your account settings
                5. **Paste both values** in the form below
            
                **Note:** Your credentials are stored securely and only used for WhatsApp messaging.
                """)
        
            # Configuration form
            with st.form("whatsapp_config", clear_on_submit=False):
                instance_id = st.text_input(
                    "Instance ID", 
                    value=whatsapp_client.instance_id if whatsapp_client.instance_id else "",
                    help="Your WaPulse instance ID",
                    key="wa_instance_id"
                )
            
                token = st.text_input(
                    "API Token", 
                    value="",
                    type="password",
                    help="Your WaPulse API token",
                    placeholder="Enter your API token" if not whatsapp_client.token else "Token is configured",
                    key="wa_token"
                )
            
                # Single submit button for the form
                submitted = st.form_submit_button("💾 Save Configuration", use_container_width=True)
        
            # Handle form submission
            if submitted:
                if instance_id and token:
                    with st.spinner("Configuring WhatsApp integration..."):
                        if configure_whatsapp(instance_id, token):
                            st.success("✅ WhatsApp configuration saved successfully!")
                            st.session_state.whatsapp_configured = True
                            st.balloons()  # Celebration effect
                            time.sleep(1)  # Brief pause before rerun
                            st.rerun()  # Refresh to show updated status
                        else:
                            st.error("❌ Failed to configure WhatsApp integration")
                            st.session_state.whatsapp_configured = False
                else:
                    st.warning("⚠️ Please provide both Instance ID and Token")
        
            # Separate test connection button outside the form
            if st.button("🧪 Test Connection", use_container_width=True):
                if whatsapp_client.is_configured():
                    with st.spinner("Testing WhatsApp connection..."):
                        status = whatsapp_client.get_instance_status()
                        if status.get("configured"):
                            st.success(f"✅ Connection successful! Status: {status.get('status')}")
                            st.info(f"📱 Instance ID: {whatsapp_client.instance_id}")
                        else:
                            st.error(f"❌ Connection failed: {status.get('error', 'Unknown error')}")
                else:
                    st.warning("⚠️ Please configure WhatsApp first")
        
            # Current status
            if whatsapp_client.is_configured():
                st.success("✅ WhatsApp integration is configured")
                status = whatsapp_client.get_instance_status()
                st.caption(f"Instance: {whatsapp_client.instance_id}")
                st.caption(f"Status: {status.get('status', 'Unknown')}")
            else:
                st.warning("⚠️ WhatsApp integration not configured")
        
            st.markdown('</div>', unsafe_allow_html=True)
        
            # Notification Settings
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<h3 class="main-header">🔔 Notification Settings</h3>', unsafe_allow_html=True)
        
            # Default recipients
            default_recipients = st.text_area(
                "Default Recipients",
                placeholder="Enter phone numbers (one per line)\nExample: 1234567890",
                help="Phone numbers to receive notifications (include country code, no + or spaces)"
            )
        
            # Notification types
            st.markdown("**Notification Types:**")
            notify_scrape_complete = st.checkbox("Scraping completion notifications", value=True)
            notify_scrape_error = st.checkbox("Scraping error notifications", value=True)
            notify_report_ready = st.checkbox("Analysis report ready notifications", value=False)
        
            # File sharing settings
            st.markdown("**File Sharing:**")
            share_html_templates = st.checkbox("Share HTML templates", value=True)
            share_json_reports = st.checkbox("Share JSON reports", value=True)
            share_charts = st.checkbox("Share analysis charts", value=True)
        
            max_file_size = st.slider("Max file size (MB)", 1, 25, 10)
        
            if st.button("💾 Save Notification Settings"):
                # Here you would save these settings to your config
                st.success("✅ Notification settings saved!")
        
            st.markdown('</div>', unsafe_allow_html=True)
    
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.warning("📱 WhatsApp integration is not available. Please install required dependencies.")
            st.markdown('</div>', unsafe_allow_html=True)

    elif page == "About":
        st.title("About This Web Scraper")
        st.markdown("""
        <div class="card">
        <h2>AI-Powered Web Scraper</h2>
        <p>This web scraper combines the power of crawl4ai for efficient web crawling with DeepSeek AI for intelligent content analysis.</p>
    
        <h3>Key Features:</h3>
        <ul>
            <li>🕸️ <strong>Multi-threaded crawling</strong> - Crawl websites efficiently with parallel processing</li>
            <li>🧠 <strong>AI-powered analysis</strong> - Leverage DeepSeek AI to summarize and analyze web content</li>
            <li>📊 <strong>Technical reports</strong> - Get detailed technical information about each page</li>
            <li>📥 <strong>Export options</strong> - Download results in multiple formats</li>
            <li>🔍 <strong>Custom prompts</strong> - Create your own AI analysis instructions</li>
            <li>📱 <strong>WhatsApp integration</strong> - Send reports and notifications via WhatsApp</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    elif page == "Scraper":
        st.title("🤖 AI-Powered Web Scraper")
        st.markdown("""
        A simple web scraper that uses crawl4ai to fetch web content and DeepSeek API for AI-powered analysis.
        """)

        # System prompts for different summarization styles
        system_prompts = {
            "Default": "You are a helpful AI assistant. Your task is to summarize the provided web page content.",
            "Concise (2-3 Sentences)": "You are an AI assistant. Summarize the provided web page content concisely, in 2-3 sentences.",
            "Detailed (Key Points)": "You are an AI assistant. Provide a detailed summary of the web page content, covering main points, arguments, and conclusions.",
            "Bullet Points": "You are an AI assistant. Summarize the web page content as a list of bullet points, highlighting the key information."
        }

        # Create a card-like container for the main input
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Input for target URL with URL validation
        target_url = st.text_input("Target URL", "https://example.com")

        # Validate URL format
        if target_url:
            try:
                result = urlparse(target_url)
                is_valid = all([result.scheme, result.netloc])
                if not is_valid:
                    st.warning("Please enter a valid URL including http:// or https://")
            except:
                st.warning("Please enter a valid URL")

        st.markdown('</div>', unsafe_allow_html=True)

        # Advanced crawling parameters
        with st.expander("Advanced Crawling Parameters"):
            col1, col2 = st.columns(2)
        
            with col1:
                # Input for crawl depth
                crawl_depth = st.slider("Crawl Depth", min_value=1, max_value=5, value=1, help="How many links deep to crawl")
            
                # Input for max pages
                max_pages = st.number_input("Maximum Pages", min_value=1, max_value=100, value=4, help="Maximum number of pages to crawl")
            
                # Input for request timeout
                timeout = st.number_input("Request Timeout (seconds)", min_value=1, max_value=60, value=10, help="Timeout for each HTTP request")
            
                # Parallel workers
                max_workers = st.slider("Parallel Workers", min_value=1, max_value=10, value=5, help="Number of parallel requests to make")
        
            with col2:
                # Domain restriction options
                domain_restriction = st.radio(
                    "Domain Restriction", 
                    ["Stay in same domain", "Allow all domains", "Custom domain list"],
                    index=0,
                    help="Control which domains the crawler can visit")
            
                # Custom domain list (if selected)
                custom_domains = ""
                if domain_restriction == "Custom domain list":
                    custom_domains = st.text_area(
                        "Allowed Domains", 
                        "", 
                        help="Enter domains to allow, one per line (e.g., example.com)")
            
                # User agent
                user_agent = st.text_input(
                    "User Agent", 
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    help="Custom user agent for requests")
            
                # Add robots.txt compliance option
                respect_robots = st.checkbox("Respect robots.txt", value=True, help="Follow robots.txt rules for ethical scraping")
            
                # Cache option
                use_cache = st.checkbox("Use cached results if available", value=True, help="Use previously cached results to speed up repeated crawls")

        # Input for keywords with futuristic styling
        keywords = st.text_input("🔍 Keywords (optional)", help="Comma-separated keywords to filter pages")

        # Operation mode selection with futuristic styling
        st.markdown('<h4 class="main-header">AI Analysis Mode</h4>', unsafe_allow_html=True)
        operation_mode = st.radio("Select Operation Mode", ["✨ Summarize", "❓ Question & Answer"], index=0)

        # Question input if asking a question
        user_question = ""
        if operation_mode == "❓ Question & Answer":
            question = st.text_input("🤔 Enter your question about the content:")

        # Custom prompt input
        custom_prompt = ""
        custom_language = "English"
        if operation_mode == "✨ Summarize":
            summary_language = st.selectbox("Summary Language", ["English", "Hebrew"], index=0)
            summary_style = st.selectbox("Summary Style", list(system_prompts.keys()), index=0, help="Choose the style of summary to generate.")
            summary_temperature = 0.7  # Default temperature for summaries

        # DeepSeek API Key - Using Streamlit secrets management
        # For local development, you can use st.secrets or environment variables
        try:
            # Try to get from Streamlit secrets (for deployment)
            DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
        except:
            # Fallback for local development
            import os
            DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        
            # If no API key found, show input field
            if not DEEPSEEK_API_KEY:
                # API Key management with futuristic styling
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<h3 class="main-header">API Keys</h3>', unsafe_allow_html=True)
            
                # DeepSeek API Key
                api_key = st.text_input("DeepSeek API Key", value="", type="password")
                if st.button("💾 Save API Key"):
                    # In a real app, you'd save this securely. For demo, we'll just update the session state
                    st.session_state.deepseek_api_key = api_key
                    st.success("API Key saved!")
                st.markdown('</div>', unsafe_allow_html=True)

        # --- Scrape Button ---
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h3 class="main-header">Start Scraping</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            start_button = st.button("🚀 Start Scraping", use_container_width=True)
        with col2:
            clear_results = st.button("🗑️ Clear Results", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Add a session state to store results between reruns
        if 'crawl_results' not in st.session_state:
            st.session_state.crawl_results = None
        
        # Clear results if requested
        if clear_results:
            st.session_state.crawl_results = None
            st.rerun()

        # Display visualizations if we have results
        if st.session_state.crawl_results:
            with st.expander("📊 Data Visualizations"):
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<h2 class="main-header">Crawl Analysis</h2>', unsafe_allow_html=True)
            
                # Create tabs for different visualizations with futuristic styling
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Crawled Pages", "📝 Content", "⚙️ Technical Report", "😊 Sentiment Analysis", "🧠 AI Analysis"])
            
                with tab1:
                    # Create a DataFrame for element counts across pages
                    element_data = []
                    for page in st.session_state.crawl_results:
                        if "report" in page and "element_counts" in page["report"]:
                            for element, count in page["report"]["element_counts"].items():
                                element_data.append({
                                    "url": page["url"],
                                    "element": element,
                                    "count": count
                                })
                
                    if element_data:
                        df_elements = pd.DataFrame(element_data)
                    
                        # Group by element type and sum counts
                        element_summary = df_elements.groupby("element")["count"].sum().reset_index()
                        element_summary = element_summary.sort_values("count", ascending=False).head(10)
                    
                        # Create bar chart
                        fig, ax = plt.subplots(figsize=(10, 6))
                        sns.barplot(x="count", y="element", data=element_summary, palette="viridis")
                        plt.title("Top 10 HTML Elements Across All Pages")
                        plt.tight_layout()
                        st.pyplot(fig)
                    
                        # Show the data table
                        st.dataframe(element_summary)
            
                with tab5:
                    # AI analysis
                    st.write("AI Analysis")
                
                    # Display crawl errors if any with futuristic styling
                    if "errors" in st.session_state and st.session_state.errors:
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        with st.expander(f"⚠️ Crawling Errors ({len(st.session_state.errors)})"):
                            st.json(st.session_state.errors)
                        st.markdown('</div>', unsafe_allow_html=True)
                
                    # Display AI analysis results
                    if "summaries" in st.session_state:
                        st.dataframe(st.session_state.summaries)
                    else:
                        st.info("No AI analysis results available.")
        
            # This line was causing issues - removing it

        if start_button:
            if not target_url:
                st.warning("Please enter a target URL.")
            # Removed API key check from UI as it's hardcoded
            else:
                st.info("Starting crawl with crawl4ai...")
                # --- Crawl4ai usage (placeholder) ---
                try:
                    # Using our async crawler implementation with futuristic UI
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(f"<h3 class='main-header'>Crawling {target_url} to depth {crawl_depth}...</h3>", unsafe_allow_html=True)
                
                    # Show a futuristic progress animation
                    with st.spinner("Initializing crawl process..."):
                        crawl_results = perform_crawl(target_url, crawl_depth, max_pages, timeout, domain_restriction, 
                                                      custom_domains, user_agent, max_workers, respect_robots, use_cache)
                    if crawl_results:
                        st.success(f"✅ Crawling complete! {len(crawl_results)} pages fetched.")
                        st.markdown('</div>', unsafe_allow_html=True)
                        # Store results in session state
                        st.session_state.crawl_results = crawl_results
                    else:
                        st.error("No pages were fetched. Check the URL or crawl parameters.")
                except Exception as e:
                    st.error(f"❌ Error during crawling: {str(e)}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    crawl_results = []
                # --- DeepSeek API usage ---
                if crawl_results:
                    # Convert HTML to plain text for each page
                    for page in crawl_results:
                        page["text"] = html_to_text(page["content"])
                        page["report"] = generate_technical_report(page["content"], page["url"])

                    st.info("Sending data to DeepSeek API...")

                    # Perform AI analysis based on operation mode with futuristic styling
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown('<h3 class="main-header">AI Analysis</h3>', unsafe_allow_html=True)
                
                    if operation_mode == "✨ Summarize":
                        with st.spinner("Generating AI summaries..."):
                            # Define temperature for summaries if not already defined
                            if 'summary_temperature' not in locals():
                                summary_temperature = 0.7

                            # Helper to build prompt for a page
                        def build_summary_prompt(page_text, page_url):
                            base_prompt = f"Please summarize the following webpage content from {page_url}:\n\n{page_text}"
                            if summary_language == "Hebrew":
                                base_prompt += "\n\nPlease respond in Hebrew."
                            return base_prompt

                        # Process pages with progress tracking
                        summaries = []
                        
                        # Add a download button for the crawled data
                        if st.session_state.crawl_results:
                            crawl_data_json = json.dumps(st.session_state.crawl_results, indent=2)
                            st.download_button(
                                label="📥 Download Raw Crawl Data (JSON)",
                                data=crawl_data_json,
                                file_name="crawl_data.json",
                                mime="application/json"
                            )
                        
                        # Create and display progress bar
                        progress_text = "Preparing to summarize pages..."
                        my_bar = st.progress(0, text=progress_text)
                        
                        # Process each page one by one
                        total_pages = len(crawl_results)
                        for i, page in enumerate(crawl_results):
                            # Update progress
                            progress_text = f"Summarizing page {i+1} of {total_pages}"
                            progress_value = float(i) / float(total_pages)
                            my_bar.progress(progress_value, text=progress_text)
                            
                            # Extract text content (limit to 4000 chars)
                            text = page["text"][:4000] if "text" in page else ""
                            
                            # Build the prompt
                            prompt_text = build_summary_prompt(text, page["url"])
                            
                            # Call DeepSeek API with proper error handling
                            try:
                                # Make the API call
                                summary = deepseek_chat(
                                    [{"role": "user", "content": prompt_text}],
                                    system_prompt=system_prompts[summary_style],
                                    temperature=summary_temperature
                                )
                                summaries.append(summary)
                            except Exception as e:
                                # Handle any errors
                                error_message = f"Error processing summary: {str(e)}"
                                summaries.append(error_message)
                                st.error(f"Error on page {i+1}: {str(e)}")
                        
                        # Complete the progress bar
                        my_bar.progress(1.0, text="Summarization complete!")
                        time.sleep(0.5)  # Brief pause
                        my_bar.empty()

                        # Display summaries
                        st.subheader("Page Summaries")
                        for i, (page, summary_text) in enumerate(zip(crawl_results, summaries)):
                            with st.expander(f"Summary for {page['url']}"):
                                if isinstance(summary_text, str) and summary_text.startswith("Error"):
                                    st.error(summary_text)
                                else:
                                    st.write(summary_text)
                elif operation_mode == "❓ Question & Answer":
                    if question:
                        with st.spinner(f"Answering: {question}"):
                            # Concatenate texts with limit
                            combined_text = "\n---\n".join([p["text"] for p in crawl_results])
                            combined_text = combined_text[:12000]  # truncate to stay within token limit
                            prompt = (
                                f"You are provided with combined text from multiple web pages. "
                                f"Answer the following question based on this content.\n\n"
                                f"### Question:\n{question}\n\n### Content:\n{combined_text}"
                            )
                            result = deepseek_chat([
                                {"role": "user", "content": prompt}
                            ])
                            answer = result.get("choices", [{}])[0].get("message", {}).get("content", str(result))
                            st.subheader("DeepSeek Answer")
                            st.write(answer)

                # Display enhanced technical reports with visualizations
                st.subheader("📊 Comprehensive Technical Reports")
                if crawl_results:
                    url_options = [p["url"] for p in crawl_results]
                    selected_url = st.selectbox("Choose a page to analyze", url_options)
                    selected_report = next(p["report"] for p in crawl_results if p["url"] == selected_url)
                    
                    # Create tabs for different report sections
                    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                        "📈 Overview", "🎨 Visual Analysis", "⚡ Performance", 
                        "🔍 SEO & Accessibility", "🛠️ Technology Stack", "🏗️ Website Blueprint", "📋 Raw Data"
                    ])
                    
                    with tab1:
                        st.markdown("### 🔍 Page Overview")
                        
                        # Basic info metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Elements", selected_report["structure"]["total_elements"])
                        with col2:
                            st.metric("Text Content", f"{selected_report['content']['text_content_length']:,} chars")
                        with col3:
                            st.metric("External Links", len(selected_report["links"]["external"]))
                        with col4:
                            st.metric("Images", len(selected_report["media"]["images"]))
                        
                        # Basic info
                        st.markdown("#### 📝 Basic Information")
                        basic_info = selected_report["basic_info"]
                        st.write(f"**Title:** {basic_info['title']}")
                        st.write(f"**Language:** {basic_info['language']}")
                        st.write(f"**Charset:** {basic_info['charset']}")
                        st.write(f"**Viewport:** {basic_info['viewport']}")
                        
                        if basic_info["description"]:
                            st.write(f"**Description:** {basic_info['description']}")
                        
                        # Warnings and Errors
                        if selected_report["warnings"]:
                            st.markdown("#### ⚠️ Warnings")
                            for warning in selected_report["warnings"]:
                                st.warning(warning)
                        
                        if selected_report["errors"]:
                            st.markdown("#### ❌ Errors")
                            for error in selected_report["errors"]:
                                st.error(error)
                        
                        # Recommendations
                        if selected_report["recommendations"]:
                            st.markdown("#### 💡 Recommendations")
                            for rec in selected_report["recommendations"]:
                                st.info(rec)
                    
                    with tab2:
                        st.markdown("### 🎨 Visual Analysis")
                        
                        # Element Distribution Chart
                        if selected_report["structure"]["element_counts"]:
                            st.markdown("#### 📊 HTML Element Distribution")
                            fig_elements = create_element_distribution_chart(selected_report["structure"]["element_counts"])
                            if fig_elements:
                                st.pyplot(fig_elements)
                                plt.close(fig_elements)
                        
                        # Color Palette Visualization
                        if selected_report["styling"]["color_palette"]:
                            st.markdown("#### 🎨 Color Palette")
                            fig_colors = create_color_palette_visualization(selected_report["styling"]["color_palette"])
                            if fig_colors:
                                st.pyplot(fig_colors)
                                plt.close(fig_colors)
                            
                            # Color palette as swatches
                            st.markdown("##### Color Swatches")
                            cols = st.columns(min(5, len(selected_report["styling"]["color_palette"])))
                            for i, color_info in enumerate(selected_report["styling"]["color_palette"][:5]):
                                with cols[i]:
                                    color = color_info["color"]
                                    count = color_info["count"]
                                    # Create a colored box using HTML
                                    st.markdown(f"""
                                        <div style="background-color: {color}; width: 100%; height: 50px; 
                                                    border-radius: 5px; border: 1px solid #ccc;
                                                    display: flex; align-items: center; justify-content: center;
                                                    color: {'white' if color.lower() in ['black', '#000', '#000000'] else 'black'};
                                                    font-weight: bold;">
                                            {count}x
                                        </div>
                                        <p style="text-align: center; margin-top: 5px; font-size: 12px;">{color}</p>
                                    """, unsafe_allow_html=True)
                        
                        # Fonts
                        if selected_report["styling"]["fonts"]:
                            st.markdown("#### 🔤 Detected Fonts")
                            for font in selected_report["styling"]["fonts"]:
                                st.code(font, language="css")
                    
                    with tab3:
                        st.markdown("### ⚡ Performance Analysis")
                        
                        # Performance metrics visualization
                        fig_perf = create_performance_metrics_chart(selected_report["performance"])
                        if fig_perf:
                            st.pyplot(fig_perf)
                            plt.close(fig_perf)
                        
                        # Performance details
                        perf = selected_report["performance"]
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### 📊 Resource Loading")
                            st.metric("Total External Requests", perf["total_requests"])
                            st.metric("Lazy Loaded Images", perf["lazy_loading"])
                            st.metric("Preload Hints", len(perf["preload_hints"]))
                        
                        with col2:
                            st.markdown("#### 🖼️ Image Optimization")
                            img_opt = perf["image_optimization"]
                            if img_opt:
                                st.metric("Total Images", img_opt["total_images"])
                                st.metric("With Alt Text", img_opt["with_alt_text"])
                                st.metric("Responsive Images", img_opt["responsive"])
                                score = img_opt["optimization_score"] * 100
                                st.metric("Optimization Score", f"{score:.1f}%")
                    
                    with tab4:
                        st.markdown("### 🔍 SEO & Accessibility Analysis")
                        
                        # SEO and Accessibility dashboard
                        fig_seo = create_seo_accessibility_dashboard(
                            selected_report["seo_analysis"], 
                            selected_report["accessibility"]
                        )
                        if fig_seo:
                            st.pyplot(fig_seo)
                            plt.close(fig_seo)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### 🔍 SEO Analysis")
                            seo = selected_report["seo_analysis"]
                            st.write(f"**Title Length:** {seo['title_length']} chars")
                            st.write(f"**Description Length:** {seo['description_length']} chars")
                            st.write(f"**Images with Alt Text:** {seo['alt_texts']['present']}")
                            st.write(f"**Images missing Alt Text:** {seo['alt_texts']['missing']}")
                            
                            if seo["open_graph"]:
                                st.markdown("##### Open Graph Tags")
                                for key, value in seo["open_graph"].items():
                                    st.write(f"**{key}:** {value}")
                            
                            if seo["schema_markup"]:
                                st.markdown("##### Schema Markup")
                                st.write(f"Found {len(seo['schema_markup'])} schema objects")
                        
                        with col2:
                            st.markdown("#### ♿ Accessibility")
                            acc = selected_report["accessibility"]
                            st.write(f"**ARIA Labels:** {acc['aria_labels']}")
                            st.write(f"**Form Labels:** {acc['form_labels']}")
                            st.write(f"**Skip Links:** {acc['skip_links']}")
                            st.write(f"**Language Attributes:** {acc['lang_attributes']}")
                            
                            if acc["aria_roles"]:
                                st.markdown("##### ARIA Roles")
                                unique_roles = list(set(acc["aria_roles"]))
                                for role in unique_roles:
                                    st.code(role)
                    
                    with tab5:
                        st.markdown("### 🛠️ Technology Stack")
                        
                        # Technology stack visualization
                        fig_tech = create_technology_stack_chart(selected_report["technology_stack"])
                        if fig_tech:
                            st.pyplot(fig_tech)
                            plt.close(fig_tech)
                        
                        tech_stack = selected_report["technology_stack"]
                        
                        # Libraries and Frameworks
                        if tech_stack["libraries"]:
                            st.markdown("#### 📚 JavaScript Libraries")
                            for lib in tech_stack["libraries"]:
                                version = lib.get("version", "unknown")
                                st.write(f"**{lib['name']}** - Version: {version}")
                                st.caption(f"Source: {lib['source']}")
                        
                        if tech_stack["cdn_resources"]:
                            st.markdown("#### 🌐 CDN Resources")
                            for resource in tech_stack["cdn_resources"]:
                                st.write(f"**{resource['type']}** - {resource['src']}")
                                if resource["async"]:
                                    st.caption("⚡ Async loaded")
                                if resource["defer"]:
                                    st.caption("⏳ Deferred")
                        
                        if tech_stack["analytics"]:
                            st.markdown("#### 📊 Analytics & Tracking")
                            for analytics in tech_stack["analytics"]:
                                st.write(f"**{analytics['name']}** - {analytics['source']}")
                        
                        # CSS Frameworks
                        css_frameworks = selected_report["styling"]["css_frameworks"]
                        if css_frameworks:
                            st.markdown("#### 🎨 CSS Frameworks")
                            for fw in css_frameworks:
                                st.write(f"**{fw['name']}**")
                                st.caption(f"Source: {fw['source']}")
                    
                    with tab6:
                        st.markdown("### 🏗️ Website Blueprint & Reconstruction Guide")
                        
                        # Generate blueprint
                        blueprint = generate_website_blueprint(selected_report)
                        
                        st.markdown("#### 📋 Implementation Priority Tasks")
                        if blueprint["implementation_guide"]["priority_tasks"]:
                            for task in blueprint["implementation_guide"]["priority_tasks"]:
                                priority_color = {
                                    "HIGH": "🔴",
                                    "MEDIUM": "🟡", 
                                    "LOW": "🟢"
                                }.get(task["priority"], "⚪")
                                
                                count_text = f" ({task['count']} items)" if "count" in task else ""
                                st.write(f"{priority_color} **{task['priority']}**: {task['task']}{count_text}")
                                st.caption(f"Impact: {task['impact']}")
                        else:
                            st.success("✅ No critical issues found!")
                        
                        # HTML Template Generation
                        st.markdown("#### 📄 Generated HTML Template")
                        st.info("This is a basic HTML template based on the analyzed structure. You can use this as a starting point for rebuilding the website.")
                        
                        html_template = generate_html_template(blueprint)
                        st.code(html_template, language="html")
                        
                        # Download buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 Download Blueprint (JSON)",
                                data=json.dumps(blueprint, indent=2),
                                file_name=f"website_blueprint_{selected_url.replace('https://', '').replace('http://', '').replace('/', '_')}.json",
                                mime="application/json"
                            )
                        
                        with col2:
                            st.download_button(
                                label="📥 Download HTML Template",
                                data=html_template,
                                file_name=f"template_{selected_url.replace('https://', '').replace('http://', '').replace('/', '_')}.html",
                                mime="text/html"
                            )
                        
                        # Blueprint sections
                        st.markdown("#### 🔍 Blueprint Details")
                        
                        with st.expander("📊 Metadata & Structure"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.json(blueprint["metadata"])
                                st.json(blueprint["body_structure"])
                            with col2:
                                st.json(blueprint["html_structure"])
                        
                        with st.expander("🎨 Styling Guide"):
                            st.json(blueprint["styling_guide"])
                        
                        with st.expander("📱 Content Blueprint"):
                            st.json(blueprint["content_blueprint"])
                        
                        with st.expander("🖼️ Media Assets"):
                            st.json(blueprint["media_assets"])
                        
                        with st.expander("🔗 Navigation Structure"):
                            st.json(blueprint["navigation_structure"])
                        
                        with st.expander("⚙️ JavaScript Blueprint"):
                            st.json(blueprint["javascript_blueprint"])
                        
                        with st.expander("🧩 UI Components"):
                            st.json(blueprint["ui_components"])
                        
                        with st.expander("⚡ Performance Requirements"):
                            st.json(blueprint["performance_requirements"])
                        
                        with st.expander("🔍 SEO Requirements"):
                            st.json(blueprint["seo_requirements"])
                        
                        with st.expander("♿ Accessibility Requirements"):
                            st.json(blueprint["accessibility_requirements"])
                        
                        with st.expander("🔒 Security Considerations"):
                            st.json(blueprint["security_considerations"])
                        
                        # CSS Generation Helper
                        st.markdown("#### 🎨 CSS Starter Template")
                        st.info("Based on the detected color palette and fonts, here's a CSS starter template:")
                        
                        css_template = "/* CSS Starter Template based on analyzed website */\n\n"
                        css_template += ":root {\n"
                        
                        # Add color variables
                        for i, color_info in enumerate(blueprint["styling_guide"]["color_palette"][:5]):
                            css_template += f"  --color-{i+1}: {color_info['color']};\n"
                        
                        css_template += "}\n\n"
                        
                        # Add font families
                        if blueprint["styling_guide"]["fonts"]:
                            css_template += "body {\n"
                            primary_font = blueprint["styling_guide"]["fonts"][0] if blueprint["styling_guide"]["fonts"] else "Arial, sans-serif"
                            css_template += f"  font-family: {primary_font};\n"
                            css_template += "}\n\n"
                        
                        # Add semantic element styles
                        semantic_elements = blueprint["body_structure"]["semantic_elements"]
                        for element, count in semantic_elements.items():
                            if count > 0:
                                css_template += f"{element} {{\n  /* Add your {element} styles here */\n}}\n\n"
                        
                        st.code(css_template, language="css")
                        
                        st.download_button(
                            label="📥 Download CSS Template",
                            data=css_template,
                            file_name=f"styles_{selected_url.replace('https://', '').replace('http://', '').replace('/', '_')}.css",
                            mime="text/css"
                        )
                    
                    with tab7:
                        st.markdown("### 📋 Raw Technical Data")
                        
                        # Expandable sections for different data types
                        with st.expander("🏗️ Structure Analysis"):
                            st.json(selected_report["structure"])
                        
                        with st.expander("📝 Content Analysis"):
                            st.json(selected_report["content"])
                        
                        with st.expander("🖼️ Media Analysis"):
                            st.json(selected_report["media"])
                        
                        with st.expander("🔗 Links Analysis"):
                            st.json(selected_report["links"])
                        
                        with st.expander("🎨 Styling Analysis"):
                            st.json(selected_report["styling"])
                        
                        with st.expander("🔒 Security Analysis"):
                            st.json(selected_report["security"])
                        
                        with st.expander("🧩 UI Components"):
                            st.json(selected_report["ui_components"])
                        
                        # Complete raw data
                        with st.expander("📊 Complete Raw Report"):
                            st.json(selected_report)

                
                with st.expander("Show Raw Crawl Results"):
                    st.json(crawl_results)
                
                # Export options
                st.subheader("Export Results")
                col1, col2 = st.columns(2)
                
                # Export crawl results
                with col1:
                    if crawl_results:
                        # JSON export
                        json_data = json.dumps(crawl_results, indent=2)
                        b64_json = base64.b64encode(json_data.encode()).decode()
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"crawl_results_{timestamp}.json"
                        href = f'<a href="data:application/json;base64,{b64_json}" download="{filename}">Download Crawl Results (JSON)</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # CSV export (simplified - just URLs and text snippets)
                        csv_buffer = io.StringIO()
                        csv_writer = csv.writer(csv_buffer)
                        csv_writer.writerow(["URL", "Text Preview"])
                        for page in crawl_results:
                            # Truncate text for CSV
                            text_preview = page.get("text", "")[:500] + "..." if len(page.get("text", "")) > 500 else page.get("text", "")
                            csv_writer.writerow([page["url"], text_preview])
                        
                        b64_csv = base64.b64encode(csv_buffer.getvalue().encode()).decode()
                        filename_csv = f"crawl_results_{timestamp}.csv"
                        href_csv = f'<a href="data:text/csv;base64,{b64_csv}" download="{filename_csv}">Download Crawl Results (CSV)</a>'
                        st.markdown(href_csv, unsafe_allow_html=True)
                
                # Export DeepSeek results
                with col2:
                    if operation_mode == "✨ Summarize" and "summaries" in locals():
                        # Export summaries
                        summary_data = {page["url"]: summary for page, summary in zip(crawl_results, summaries)}
                        json_summary = json.dumps(summary_data, indent=2)
                        b64_summary = base64.b64encode(json_summary.encode()).decode()
                        filename_summary = f"summaries_{timestamp}.json"
                        href_summary = f'<a href="data:application/json;base64,{b64_summary}" download="{filename_summary}">Download Summaries (JSON)</a>'
                        st.markdown(href_summary, unsafe_allow_html=True)
                    elif operation_mode == "❓ Question & Answer" and "answer" in locals():
                        # Export Q&A
                        qa_data = {"question": question, "answer": answer}
                        json_qa = json.dumps(qa_data, indent=2)
                        b64_qa = base64.b64encode(json_qa.encode()).decode()
                        filename_qa = f"qa_result_{timestamp}.json"
                        href_qa = f'<a href="data:application/json;base64,{b64_qa}" download="{filename_qa}">Download Q&A Result (JSON)</a>'
                        st.markdown(href_qa, unsafe_allow_html=True)
                    # Export technical reports
                    if crawl_results and all("report" in p for p in crawl_results):
                        reports_json = json.dumps({p["url"]: p["report"] for p in crawl_results}, indent=2)
                        b64_rep = base64.b64encode(reports_json.encode()).decode()
                        filename_rep = f"tech_reports_{timestamp}.json"
                        href_rep = f'<a href="data:application/json;base64,{b64_rep}" download="{filename_rep}">Download Technical Reports (JSON)</a>'
                        st.markdown(href_rep, unsafe_allow_html=True)
                
                # WhatsApp Sharing Section
                if WHATSAPP_AVAILABLE:
                    st.subheader("📱 Share via WhatsApp")
                    whatsapp_client = get_whatsapp_client()
                    
                    if whatsapp_client.is_configured():
                        with st.expander("🚀 WhatsApp Sharing Options"):
                            # Phone number input
                            phone_number = st.text_input(
                                "Recipient Phone Number",
                                placeholder="1234567890 (include country code, no + or spaces)",
                                help="Enter the recipient's phone number with country code"
                            )
                            
                            col1, col2, col3 = st.columns(3)
                            
                            # Send notification about scraping completion
                            with col1:
                                if st.button("📢 Send Completion Notification"):
                                    if phone_number:
                                        result = whatsapp_client.send_scrape_notification(
                                            phone_number=phone_number,
                                            url=target_url,
                                            page_count=len(crawl_results),
                                            success=True
                                        )
                                        if result["success"]:
                                            st.success(f"✅ Notification sent to {result['recipient']}")
                                        else:
                                            st.error(f"❌ Failed to send: {result['error']}")
                                    else:
                                        st.warning("⚠️ Please enter a phone number")
                            
                            # Send report summary
                            with col2:
                                if st.button("📊 Send Report Summary"):
                                    if phone_number and crawl_results and crawl_results[0].get("report"):
                                        result = whatsapp_client.send_report_summary(
                                            phone_number=phone_number,
                                            report_data=crawl_results[0]["report"]
                                        )
                                        if result["success"]:
                                            st.success(f"✅ Report summary sent to {result['recipient']}")
                                        else:
                                            st.error(f"❌ Failed to send: {result['error']}")
                                    else:
                                        st.warning("⚠️ Please enter phone number and ensure reports are available")
                            
                            # Send chart
                            with col3:
                                if st.button("📈 Send Analysis Chart"):
                                    if phone_number and crawl_results and crawl_results[0].get("report"):
                                        # Create a sample chart to send
                                        report = crawl_results[0]["report"]
                                        element_counts = report.get("element_analysis", {}).get("element_counts", {})
                                        
                                        if element_counts:
                                            fig = create_element_distribution_chart(element_counts)
                                            if fig:
                                                result = whatsapp_client.send_chart_image(
                                                    phone_number=phone_number,
                                                    chart_figure=fig,
                                                    chart_title="Website Element Distribution"
                                                )
                                                if result["success"]:
                                                    st.success(f"✅ Chart sent to {result['recipient']} ({result['file_size_mb']}MB)")
                                                else:
                                                    st.error(f"❌ Failed to send: {result['error']}")
                                                plt.close(fig)
                                            else:
                                                st.warning("⚠️ Could not generate chart")
                                        else:
                                            st.warning("⚠️ No chart data available")
                                    else:
                                        st.warning("⚠️ Please enter phone number and ensure reports are available")
                            
                            # Send files section
                            st.markdown("**📁 Send Files:**")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("📄 Send JSON Report"):
                                    if phone_number and crawl_results:
                                        # Send the complete crawl results as JSON
                                        result = whatsapp_client.send_json_report(
                                            phone_number=phone_number,
                                            report_data={"crawl_results": crawl_results, "timestamp": timestamp}
                                        )
                                        if result["success"]:
                                            st.success(f"✅ JSON report sent to {result['recipient']} ({result['file_size_mb']}MB)")
                                        else:
                                            st.error(f"❌ Failed to send: {result['error']}")
                                    else:
                                        st.warning("⚠️ Please enter phone number and ensure results are available")
                            
                            with col2:
                                if st.button("🌐 Send HTML Template"):
                                    if phone_number and crawl_results and crawl_results[0].get("report"):
                                        # Generate and send HTML template
                                        report = crawl_results[0]["report"]
                                        blueprint = generate_website_blueprint(report)
                                        html_template = generate_html_template(blueprint)
                                        
                                        result = whatsapp_client.send_html_template(
                                            phone_number=phone_number,
                                            html_content=html_template
                                        )
                                        if result["success"]:
                                            st.success(f"✅ HTML template sent to {result['recipient']} ({result['file_size_mb']}MB)")
                                        else:
                                            st.error(f"❌ Failed to send: {result['error']}")
                                    else:
                                        st.warning("⚠️ Please enter phone number and ensure reports are available")
                    else:
                        st.warning("⚠️ WhatsApp integration not configured. Go to Settings to configure.")
                        if st.button("⚙️ Go to Settings"):
                            st.session_state.page = "Settings"
                            st.rerun()

    # --- Footer ---
    st.markdown("---")
    st.caption("Built with Streamlit, crawl4ai, and DeepSeek API. 🦾")

if __name__ == "__main__":
    main()

import streamlit as st
# Import crawl4ai and requests for scraping and API calls
import crawl4ai
import requests
from bs4 import BeautifulSoup
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
import seaborn as sns
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import hashlib
import urllib.robotparser
import nest_asyncio

# Apply nest_asyncio to make asyncio work with Streamlit
nest_asyncio.apply()

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

def generate_technical_report(html: str, url: str = "") -> dict:
    """Generate a simple technical report for a web page."""
    report = {
        "url": url,
        "title": "",
        "description": "",
        "element_counts": {},
        "links": 0,
        "images": 0,
        "libraries": [],
        "language": "",
        "buttons": [],
        "media": {
            "images": [],
            "videos": [],
            "audio": []
        },
        "color_palette": []
    }
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # Title & description
        if soup.title and soup.title.string:
            report["title"] = soup.title.string.strip()
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            report["description"] = desc_tag['content'][:300]
        # Element counts (top 10)
        tags = [tag.name for tag in soup.find_all()]
        tag_counts = Counter(tags)
        report["element_counts"] = dict(tag_counts.most_common(10))
        # Links & media counts and sources
        links = soup.find_all('a')
        report["links"] = len(links)
        imgs = soup.find_all('img')
        report["images"] = len(imgs)
        report["media"]["images"] = [img.get('src') for img in imgs if img.get('src')]
        videos = soup.find_all('video')
        report["media"]["videos"] = [vid.get('src') or vid.find('source').get('src') if vid.find('source') else None for vid in videos if (vid.get('src') or vid.find('source'))]
        audios = soup.find_all('audio')
        report["media"]["audio"] = [aud.get('src') for aud in audios if aud.get('src')]
        # Detect page language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            report["language"] = html_tag.get('lang')
        else:
            # rough detection via unicode block (hebrew/arabic etc.)
            text_sample = soup.get_text()[:500]
            if any('\u0590' <= ch <= '\u05EA' for ch in text_sample):
                report["language"] = "he"
            else:
                report["language"] = "en"

        # Detect JS/CSS libraries
        libs = set()
        lib_patterns = {
            'jquery': r'jquery',
            'react': r'react',
            'vue': r'vue',
            'angular': r'angular',
            'bootstrap': r'bootstrap',
            'tailwind': r'tailwind',
            'svelte': r'svelte',
            'wordpress': r'wp-|wordpress',
            'elementor': r'elementor',
            'nextjs': r'_next',
            'font-awesome': r'font[-]?awesome',
        }
        for script in soup.find_all('script', src=True):
            src = script['src'].lower()
            for name, pattern in lib_patterns.items():
                if pattern in src:
                    libs.add(name)
        for link in soup.find_all('link', href=True):
            href = link['href'].lower()
            for name, pattern in lib_patterns.items():
                if pattern in href:
                    libs.add(name)
        report["libraries"] = sorted(list(libs))
        # Capture buttons (text or aria-label)
        buttons = soup.find_all(['button', 'a'], attrs={'role': 'button'})
        report["buttons"] = [btn.get_text(strip=True) or btn.get('aria-label') or 'unnamed' for btn in buttons]

        # Extract colors from inline styles and style tags
        color_regex = r'#[0-9a-fA-F]{3,6}'
        colors = re.findall(color_regex, html)
        color_counts = Counter(colors)
        report["color_palette"] = [c for c, _ in color_counts.most_common(8)]
    except Exception as e:
        report["error"] = str(e)
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
            "status_code": None,
            "response_time": None,
            "is_healthy": False,
            "error": str(e)
        }

st.set_page_config(page_title="NeoScraper AI", layout="wide", initial_sidebar_state="expanded", 
                 menu_items={
                     'Get Help': 'https://github.com/yourusername/neoscraper',
                     'Report a bug': 'https://github.com/yourusername/neoscraper/issues',
                     'About': 'NeoScraper AI - Advanced web scraping with AI analysis'
                 })

# Initialize theme in session state if not already present
if 'theme' not in st.session_state:
    st.session_state.theme = "Futuristic"  # Default to Futuristic theme

# Sidebar with futuristic styling
st.sidebar.markdown('<h1 class="main-header">NeoScraper AI</h1>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="card">', unsafe_allow_html=True)

# Theme selector with new futuristic option
theme = st.sidebar.radio("Select Theme", ["Futuristic", "Dark", "Light", "Blue"], index=0)
if theme != st.session_state.theme:
    st.session_state.theme = theme
    st.experimental_rerun()
    
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
    
    # Input form with futuristic styling
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form(key="scraper_form"):
        st.markdown('<h3 class="main-header">Crawl Settings</h3>', unsafe_allow_html=True)
        
        # Theme settings
        st.subheader("Theme Settings")
        
        # Store theme preference in session state
        theme = st.selectbox("Select Theme", ["Light", "Dark", "Blue"], 
                           index=["Light", "Dark", "Blue"].index(st.session_state.theme),
                           key="theme_select")
        
        if st.button("Apply Theme", key="apply_theme_btn"):
            st.session_state.theme = theme
            st.rerun()
    
    # API Key management
    st.subheader("API Keys")

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

# --- UI Inputs ---
# Add a sidebar for better navigation
st.sidebar.title("Navigation")

# Navigation with futuristic styling
st.sidebar.markdown('<div class="card">', unsafe_allow_html=True)
st.sidebar.markdown('<h3 class="main-header">Navigation</h3>', unsafe_allow_html=True)
page = st.sidebar.radio("Go to", ["Scraper", "Analytics", "Settings"])
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
    </ul>
    </div>
    """, unsafe_allow_html=True)

elif page == "Scraper":
    st.markdown('<h1 class="main-header pulse">NeoScraper AI</h1>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    
    <div class="main-header">🤖 AI-Powered Web Scraper</div>
    """, unsafe_allow_html=True)

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
    # API Key management with futuristic styling
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 class="main-header">API Keys</h3>', unsafe_allow_html=True)
    
    # DeepSeek API Key
    api_key = st.text_input("DeepSeek API Key", value=DEEPSEEK_API_KEY if DEEPSEEK_API_KEY else "", type="password")
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

            # Display crawl results for reference
            st.subheader("Technical Reports")
            if crawl_results:
                url_options = [p["url"] for p in crawl_results]
                selected_url = st.selectbox("Choose a page to view its technical report", url_options)
                selected_report = next(p["report"] for p in crawl_results if p["url"] == selected_url)
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

# --- Footer ---
st.markdown("---")
st.caption("Built with Streamlit, crawl4ai, and DeepSeek API. 🦾")

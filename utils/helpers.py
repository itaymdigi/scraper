"""
Helper utility functions for the web scraper.
"""

import time
import requests
from textblob import TextBlob


def analyze_sentiment(text):
    """Analyze sentiment of text using TextBlob"""
    try:
        analysis = TextBlob(text)
        # Return polarity (-1 to 1) and subjectivity (0 to 1)
        return {
            "polarity": analysis.sentiment.polarity,
            "subjectivity": analysis.sentiment.subjectivity,
            "sentiment": "positive" if analysis.sentiment.polarity > 0.1 else 
                       "negative" if analysis.sentiment.polarity < -0.1 else "neutral"
        }
    except Exception as e:
        return {
            "polarity": 0,
            "subjectivity": 0,
            "sentiment": "neutral",
            "error": str(e)
        }


def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def extract_domain(url):
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return url


def is_external_url(url, base_domain):
    """Check if URL is external to the base domain"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc != base_domain and parsed.netloc != ""
    except Exception:
        return False


def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    
    # Remove common unwanted characters
    text = text.replace('\u00a0', ' ')  # Non-breaking space
    text = text.replace('\u200b', '')   # Zero-width space
    
    return text.strip()


def truncate_text(text, max_length=100):
    """Truncate text to specified length with ellipsis"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def get_color_brightness(hex_color):
    """Calculate brightness of a hex color (0-255)"""
    try:
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Calculate brightness using luminance formula
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)
        return brightness
    except Exception:
        return 128  # Default to medium brightness


def is_dark_color(hex_color):
    """Check if a color is dark (brightness < 128)"""
    return get_color_brightness(hex_color) < 128


def validate_url(url):
    """Validate if string is a proper URL"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def get_file_extension(url_or_path):
    """Extract file extension from URL or path"""
    try:
        from urllib.parse import urlparse
        import os
        
        parsed = urlparse(url_or_path)
        path = parsed.path if parsed.path else url_or_path
        
        return os.path.splitext(path)[1].lower()
    except Exception:
        return ""


def is_image_url(url):
    """Check if URL points to an image file"""
    from config.settings import IMAGE_EXTENSIONS
    extension = get_file_extension(url)
    return extension in IMAGE_EXTENSIONS


def is_video_url(url):
    """Check if URL points to a video file"""
    from config.settings import VIDEO_EXTENSIONS
    extension = get_file_extension(url)
    return extension in VIDEO_EXTENSIONS


def is_audio_url(url):
    """Check if URL points to an audio file"""
    from config.settings import AUDIO_EXTENSIONS
    extension = get_file_extension(url)
    return extension in AUDIO_EXTENSIONS


def calculate_performance_score(metrics):
    """Calculate overall performance score from various metrics"""
    try:
        score = 100
        
        # Deduct points for excessive requests
        total_requests = metrics.get('total_requests', 0)
        if total_requests > 50:
            score -= min(30, (total_requests - 50) * 0.5)
        
        # Add points for optimization
        img_opt = metrics.get('image_optimization', {})
        if img_opt:
            opt_score = img_opt.get('optimization_score', 0)
            score = score * (0.7 + 0.3 * opt_score)
        
        # Add points for lazy loading
        lazy_count = metrics.get('lazy_loading', 0)
        if lazy_count > 0:
            score += min(10, lazy_count * 2)
        
        # Add points for preload hints
        preload_count = len(metrics.get('preload_hints', []))
        if preload_count > 0:
            score += min(5, preload_count)
        
        return max(0, min(100, int(score)))
    except Exception:
        return 50  # Default score


def format_timestamp(timestamp_str):
    """Format ISO timestamp to readable format"""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return timestamp_str


def generate_report_summary(report):
    """Generate a brief summary of the technical report"""
    try:
        summary = []
        
        # Basic info
        title = report.get('basic_info', {}).get('title', 'Unknown')
        summary.append(f"Page: {title}")
        
        # Element count
        structure = report.get('structure_analysis', {})
        total_elements = structure.get('total_elements', 0)
        summary.append(f"Elements: {total_elements}")
        
        # Technology stack
        tech_stack = report.get('technology_stack', {})
        lib_count = len(tech_stack.get('libraries', []))
        if lib_count > 0:
            summary.append(f"Libraries: {lib_count}")
        
        # Performance score
        performance = report.get('performance_analysis', {})
        perf_score = performance.get('overall_score', 0)
        summary.append(f"Performance: {perf_score}/100")
        
        return " | ".join(summary)
    except Exception:
        return "Analysis completed" 
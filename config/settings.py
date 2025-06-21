"""
Configuration settings for the web scraper application.
"""

# Default crawling settings
DEFAULT_DEPTH = 1
DEFAULT_MAX_PAGES = 20
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_WORKERS = 5
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Domain restriction options
DOMAIN_RESTRICTIONS = [
    "Stay in same domain",
    "Allow all domains", 
    "Custom domain list"
]

# Cache settings
CACHE_ENABLED = True
CACHE_DIRECTORY = "cache"

# Streamlit settings
DEFAULT_PORT = 8503
PAGE_TITLE = "Advanced Web Scraper & Analyzer"
PAGE_ICON = "🕷️"
LAYOUT = "wide"

# Analysis settings
MAX_ELEMENT_DEPTH = 10
COLOR_PALETTE_SIZE = 10
CHART_FIGSIZE = (12, 8)
CHART_DPI = 100

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'excellent': 90,
    'good': 70,
    'fair': 50,
    'poor': 0
}

# File extensions for media detection
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.aac', '.wma', '.flac']

# Library detection patterns
LIBRARIES_PATTERNS = {
    'jQuery': [r'jquery', r'jquery-\d+'],
    'React': [r'react', r'react\.js', r'react\.min\.js'],
    'Vue': [r'vue', r'vue\.js', r'vue\.min\.js'],
    'Angular': [r'angular', r'angular\.js', r'angular\.min\.js'],
    'Bootstrap': [r'bootstrap', r'bootstrap\.js', r'bootstrap\.min\.js'],
    'D3': [r'd3', r'd3\.js', r'd3\.min\.js'],
    'Lodash': [r'lodash', r'lodash\.js', r'lodash\.min\.js'],
    'Moment': [r'moment', r'moment\.js', r'moment\.min\.js']
}

# Analytics detection patterns
ANALYTICS_PATTERNS = {
    'Google Analytics': [r'google-analytics\.com', r'gtag\(', r'ga\('],
    'Google Tag Manager': [r'googletagmanager\.com', r'gtm\.js'],
    'Facebook Pixel': [r'facebook\.net', r'fbevents\.js', r'fbq\('],
    'Hotjar': [r'hotjar\.com', r'hj\('],
    'Mixpanel': [r'mixpanel\.com', r'mixpanel\.track']
}

# SEO analysis settings
SEO_REQUIRED_TAGS = ['title', 'description', 'keywords']
SEO_RECOMMENDED_TAGS = ['og:title', 'og:description', 'og:image', 'twitter:card']

# File extensions for different media types
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.aac', '.flac', '.wma'}

# Common libraries and frameworks for detection
LIBRARIES_PATTERNS = {
    'jQuery': [r'jquery[.-](\d+(?:\.\d+)*)', r'jquery(?:\.min)?\.js'],
    'React': [r'react[.-](\d+(?:\.\d+)*)', r'react(?:\.min)?\.js'],
    'Vue': [r'vue[.-](\d+(?:\.\d+)*)', r'vue(?:\.min)?\.js'],
    'Angular': [r'angular[.-](\d+(?:\.\d+)*)', r'angular(?:\.min)?\.js'],
    'Bootstrap': [r'bootstrap[.-](\d+(?:\.\d+)*)', r'bootstrap(?:\.min)?\.css'],
    'Font Awesome': [r'font-awesome[.-](\d+(?:\.\d+)*)', r'fontawesome'],
    'Lodash': [r'lodash[.-](\d+(?:\.\d+)*)', r'lodash(?:\.min)?\.js'],
    'Moment.js': [r'moment[.-](\d+(?:\.\d+)*)', r'moment(?:\.min)?\.js'],
    'D3.js': [r'd3[.-](\d+(?:\.\d+)*)', r'd3(?:\.min)?\.js'],
    'Chart.js': [r'chart[.-](\d+(?:\.\d+)*)', r'chart(?:\.min)?\.js']
}

# Analytics patterns
ANALYTICS_PATTERNS = {
    'Google Analytics': [r'google-analytics\.com/analytics\.js', r'gtag\(', r'ga\('],
    'Google Tag Manager': [r'googletagmanager\.com/gtm\.js', r'GTM-'],
    'Facebook Pixel': [r'connect\.facebook\.net/.*?/fbevents\.js', r'fbq\('],
    'Hotjar': [r'static\.hotjar\.com/c/hotjar-', r'hjBootstrap'],
    'Mixpanel': [r'cdn\.mxpnl\.com/libs/mixpanel-', r'mixpanel\.'],
    'Adobe Analytics': [r'omniture\.com', r's_code\.js']
}

# WhatsApp/WaPulse settings
WHATSAPP_CONFIG = {
    'enabled': False,  # Will be enabled when user configures credentials
    'instance_id': '',
    'token': '',
    'default_recipients': [],  # List of default phone numbers to send reports to
    'message_templates': {
        'scrape_complete': "🕷️ *Scraping Complete*\n\n*URL:* {url}\n*Pages:* {page_count}\n*Status:* ✅ Success\n\n📊 Report ready for analysis!",
        'scrape_error': "🚨 *Scraping Error*\n\n*URL:* {url}\n*Error:* {error}\n\n⚠️ Please check the URL and try again.",
        'report_summary': "📋 *Website Analysis Report*\n\n*URL:* {url}\n*Title:* {title}\n*Elements:* {element_count}\n*Performance Score:* {performance_score}%\n\n🔍 Full report available in the dashboard."
    },
    'file_sharing': {
        'enable_html_templates': True,
        'enable_json_reports': True,
        'enable_charts': True,
        'max_file_size_mb': 10
    }
} 
# Advanced Web Scraper & Analyzer

A comprehensive, modular web scraping and analysis tool built with Python and Streamlit. This application can crawl websites, perform detailed technical analysis, and generate blueprints for website reconstruction.

## 🚀 Features

- **Multi-depth Web Crawling**: Crawl websites with configurable depth and domain restrictions
- **🧠 AI-Powered Analysis**: DeepSeek integration for intelligent content analysis and summarization
- **Comprehensive Technical Analysis**: Analyze HTML structure, SEO, accessibility, performance, and more
- **Visual Analytics**: Generate charts and dashboards for better insights
- **Website Blueprint Generation**: Create detailed reconstruction guides with downloadable templates
- **Modular Architecture**: Clean, maintainable codebase with separated concerns
- **Caching System**: Intelligent caching for improved performance
- **Export Capabilities**: Download results in JSON, CSV, and HTML formats

## 🤖 AI Features (DeepSeek Integration)

- **✨ Smart Summarization**: AI-powered content summaries with customizable styles (Professional, Casual, Technical, Creative)
- **❓ Question & Answer**: Ask questions about crawled content and get intelligent AI responses
- **🧠 Content Analysis**: Deep AI analysis for SEO optimization, technical insights, and business intelligence
- **🌐 Multi-language Support**: Generate summaries in English and Hebrew
- **🎨 Customizable Temperature**: Control AI creativity and focus levels
- **📊 AI Analysis Tab**: Integrated AI analysis within technical reports

## 📁 Project Structure

```
scraper/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── cache/                 # Cache directory
├── config/                # Configuration and settings
│   ├── __init__.py
│   └── settings.py        # Application constants and configurations
├── core/                  # Core functionality
│   ├── __init__.py
│   └── crawler.py         # Web crawling logic
├── analysis/              # Analysis modules
│   ├── __init__.py
│   └── technical_report.py # Technical report generation
├── visualization/         # Chart and dashboard generation
│   ├── __init__.py
│   └── charts.py          # Matplotlib chart functions
├── blueprint/             # Website reconstruction
│   ├── __init__.py
│   └── generator.py       # Blueprint and template generation
├── ui/                    # User interface components
│   └── __init__.py
└── utils/                 # Utility functions
    ├── __init__.py
    ├── cache.py           # Cache management
    ├── helpers.py         # Helper utilities
    └── deepseek_api.py    # DeepSeek AI integration
```

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd scraper
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure DeepSeek API (Optional for AI features):**
   - Get your API key from [DeepSeek](https://platform.deepseek.com/)
   - Set it as an environment variable:
     ```bash
     export DEEPSEEK_API_KEY="your-api-key-here"
     ```
   - Or enter it directly in the application sidebar when using AI features

## 🚀 Usage

### Running the Application

```bash
streamlit run main.py --server.port 8503
```

The application will open in your browser at `http://localhost:8503`

### Basic Workflow

1. **Enter Target URL**: Input the website URL you want to analyze
2. **Configure Settings**: Adjust crawl depth, max pages, domain restrictions, etc.
3. **Select Operation Mode**:
   - **🔍 Crawl Only**: Basic website crawling and data extraction
   - **📊 Technical Analysis**: Comprehensive analysis with visualizations and AI insights
   - **✨ Summarize**: AI-powered content summarization with DeepSeek
   - **❓ Q&A with AI**: Ask questions about crawled content and get AI answers
4. **Start Crawling**: Click the "Start Crawling" button
5. **View Results**: Explore the analysis in multiple tabs
6. **Export Data**: Download results in various formats

### Advanced Features

#### Technical Analysis Tabs

- **📊 Overview**: Key metrics and basic information
- **📈 Visual Analysis**: Element distribution and color palette charts
- **⚡ Performance**: Performance metrics and optimization suggestions
- **🔍 SEO & Accessibility**: SEO analysis and accessibility compliance
- **🛠️ Technology Stack**: Detected libraries, frameworks, and tools
- **🏗️ Website Blueprint**: Reconstruction guide with downloadable templates
- **📋 Raw Data**: Complete technical data in JSON format

#### Configuration Options

- **Crawl Depth**: How deep to crawl (1-5 levels)
- **Max Pages**: Maximum number of pages to crawl (1-100)
- **Timeout**: Request timeout in seconds (5-60)
- **Domain Restrictions**: Stay in domain, allow all, or custom list
- **User Agent**: Custom user agent string
- **Robots.txt**: Respect robots.txt rules
- **Caching**: Enable/disable result caching

## 🏗️ Architecture

### Modular Design

The application follows a clean modular architecture:

- **Separation of Concerns**: Each module has a single responsibility
- **Loose Coupling**: Modules interact through well-defined interfaces
- **High Cohesion**: Related functionality is grouped together
- **Testability**: Each module can be tested independently
- **Scalability**: Easy to add new features and analysis types

### Key Modules

#### Core Module (`core/`)
- `crawler.py`: Asynchronous web crawling with aiohttp
- Handles robots.txt compliance, domain restrictions, and caching

#### Analysis Module (`analysis/`)
- `technical_report.py`: Comprehensive website analysis
- Analyzes structure, content, SEO, accessibility, performance, and security

#### Visualization Module (`visualization/`)
- `charts.py`: Matplotlib-based chart generation
- Creates pie charts, bar charts, and multi-panel dashboards

#### Blueprint Module (`blueprint/`)
- `generator.py`: Website reconstruction blueprint generation
- Creates detailed guides and HTML/CSS templates

#### Utils Module (`utils/`)
- `cache.py`: Intelligent caching with disk persistence
- `helpers.py`: Utility functions for data processing

#### Config Module (`config/`)
- `settings.py`: Centralized configuration management
- Contains all constants, patterns, and default values

## 🔧 Configuration

### Environment Variables

You can customize the application behavior by modifying `config/settings.py`:

```python
# Default crawling settings
DEFAULT_DEPTH = 1
DEFAULT_MAX_PAGES = 20
DEFAULT_TIMEOUT = 10

# Streamlit settings
DEFAULT_PORT = 8503
PAGE_TITLE = "Advanced Web Scraper & Analyzer"

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'excellent': 90,
    'good': 70,
    'fair': 50,
    'poor': 0
}
```

### Library Detection

The application automatically detects popular libraries and frameworks. You can extend detection by adding patterns to `LIBRARIES_PATTERNS` in `config/settings.py`.

## 📊 Analysis Capabilities

### Technical Analysis
- HTML structure and semantic analysis
- Element counting and depth analysis
- Content structure (headings, paragraphs, lists, tables)
- Media analysis (images, videos, audio)
- Link analysis (internal, external, anchor links)

### Technology Stack Detection
- JavaScript libraries (jQuery, React, Vue, Angular, etc.)
- CSS frameworks (Bootstrap, Tailwind, etc.)
- Analytics tools (Google Analytics, GTM, Facebook Pixel, etc.)
- CDN vs local resource identification
- Version detection where possible

### SEO Analysis
- Meta tags analysis
- Open Graph and Twitter Cards detection
- Schema markup identification
- Alt text coverage
- Title and description optimization

### Accessibility Analysis
- ARIA labels and roles
- Form label compliance
- Heading structure validation
- Skip link detection
- Language attribute analysis

### Performance Analysis
- External request counting
- Lazy loading detection
- Preload hint identification
- Image optimization scoring
- Overall performance scoring

### Security Analysis
- External domain identification
- Mixed content detection
- Security header analysis

## 🎨 Visualization Features

### Interactive Charts
- **Element Distribution**: Pie chart showing HTML element usage
- **Color Palette**: Bar chart of detected colors with usage counts
- **Technology Stack**: Horizontal bar chart of detected technologies
- **Performance Dashboard**: Multi-panel performance metrics
- **SEO/Accessibility Dashboard**: Comprehensive compliance overview

### Export Options
- **JSON**: Complete raw data export
- **CSV**: Simplified tabular data
- **HTML Templates**: Ready-to-use website templates
- **CSS Starter**: Generated CSS based on detected styles
- **Blueprint**: Comprehensive reconstruction guide

## 🔄 Caching System

The application includes an intelligent caching system:

- **Memory Cache**: Fast in-memory storage for active sessions
- **Disk Cache**: Persistent storage for cross-session caching
- **TTL**: 24-hour cache expiration
- **Cache Management**: Built-in cache statistics and clearing

## 🚀 Performance Optimizations

- **Asynchronous Crawling**: Concurrent request processing with aiohttp
- **Connection Pooling**: Efficient connection management
- **Intelligent Caching**: Reduces redundant requests
- **Lazy Loading**: Charts generated only when needed
- **Progress Tracking**: Real-time crawling progress updates

## 🛡️ Security Features

- **Robots.txt Compliance**: Respects website crawling policies
- **Rate Limiting**: Configurable request throttling
- **Domain Restrictions**: Prevents unauthorized domain crawling
- **User Agent**: Customizable user agent identification
- **Mixed Content Detection**: Identifies security vulnerabilities

## 🧪 Testing

To test individual modules:

```bash
# Test core crawler
python -c "from core.crawler import perform_crawl; print('Crawler OK')"

# Test analysis
python -c "from analysis.technical_report import generate_technical_report; print('Analysis OK')"

# Test visualization
python -c "from visualization.charts import create_element_distribution_chart; print('Visualization OK')"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all functions
- Include type hints where appropriate
- Write unit tests for new features
- Update documentation for new features

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed (`pip install -r requirements.txt`)
2. **Port Conflicts**: Use a different port with `--server.port XXXX`
3. **Memory Issues**: Reduce `max_pages` for large websites
4. **Timeout Errors**: Increase timeout setting for slow websites
5. **Cache Issues**: Clear cache from the sidebar if experiencing stale data

### Performance Tips

- Use caching for repeated analysis of the same websites
- Limit crawl depth for large websites
- Use domain restrictions to focus crawling
- Enable lazy loading for better image performance
- Monitor memory usage for large crawls

## 🔮 Future Enhancements

- [ ] AI-powered content summarization
- [ ] Advanced SEO scoring algorithms
- [ ] Real-time website monitoring
- [ ] API endpoints for programmatic access
- [ ] Database integration for result storage
- [ ] Multi-language support
- [ ] Advanced security scanning
- [ ] Performance benchmarking
- [ ] Custom analysis plugins
- [ ] Automated report generation

## 📞 Support

For support, questions, or feature requests, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ using Python, Streamlit, and modern web technologies.**

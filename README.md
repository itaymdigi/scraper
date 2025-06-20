# 🤖 AI Web Scraper

An AI-powered web scraper with an interactive Streamlit UI that uses crawl4ai for web crawling and DeepSeek API for content analysis. This advanced tool combines efficient multi-threaded crawling with powerful AI analysis capabilities.

## Features

### Core Features
- 🕸️ Web crawling with configurable depth and domain restrictions
- 🧠 AI-powered content analysis with DeepSeek API
- 🔄 Multiple operation modes:
  - Summarize each page
  - Ask questions about crawled content
  - Custom prompts for specialized analysis
- 🌐 Multi-language support (English and Hebrew)
- 📊 Technical report generation for each page
- 📥 Export options (JSON, CSV)

### New Improvements
- ⚡ Multi-threaded parallel crawling for faster performance
- 📊 Advanced data visualizations:
  - Page structure analysis
  - Link network graphs
  - Content word frequency analysis and word clouds
- 🤖 Robots.txt compliance for ethical scraping
- 🎨 Multiple theme options (Light, Dark, Blue)
- 💾 Session state management for persistent results
- 🔄 Retry logic for API resilience
- ⚙️ Enhanced settings management with import/export
- 🧹 Cache management tools

## Installation

1. Clone this repository
2. Install dependencies:
```powershell
pip install -r requirements.txt
```

### Optional Dependencies
For word cloud visualization:
```powershell
pip install wordcloud
```

## Local Development

1. Set your DeepSeek API key as an environment variable:
```powershell
$env:DEEPSEEK_API_KEY = "your-api-key"
```

2. Run the Streamlit app:
```powershell
streamlit run scraper.py
```

3. Access the app in your browser at http://localhost:8501

### Using the App

1. **Web Scraper Tab**: Enter a URL and configure crawling parameters
2. **Settings Tab**: Configure API keys, themes, and system settings
3. **About Tab**: View information about the application

## Deployment to Streamlit Cloud

1. Push your code to GitHub (make sure `.streamlit/secrets.toml` is in your `.gitignore`)

2. Create a new app on [Streamlit Cloud](https://streamlit.io/cloud)

3. Connect your GitHub repository

4. Add your DeepSeek API key to Streamlit secrets:
   - Go to your app settings
   - Find the "Secrets" section
   - Add the following:
   ```toml
   DEEPSEEK_API_KEY = "your-api-key"
   ```

5. Deploy your app!

## Security Notes

- Never commit your API keys to Git
- The app uses Streamlit secrets management for secure API key handling
- For local development, use environment variables or the built-in input field
- The Settings page allows secure saving of API keys to the secrets.toml file

## Performance Tips

- Adjust the "Parallel Workers" setting based on your system capabilities
- For large websites, start with a smaller crawl depth and increase gradually
- Enable "Respect robots.txt" for ethical scraping
- Use domain restrictions to focus your crawl on relevant content
- The cache management tool in Settings can help if you encounter memory issues

## Troubleshooting

- **API Key Issues**: Verify your DeepSeek API key is correctly set in Settings or environment variables
- **Crawling Errors**: Check the expanded error section for details on failed requests
- **Visualization Errors**: Ensure you have the required packages installed (matplotlib, seaborn, networkx)
- **Performance Issues**: Reduce parallel workers or max pages if your system is struggling

## License

MIT

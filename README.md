# AI Web Scraper

An AI-powered web scraper with an interactive Streamlit UI that uses crawl4ai for web crawling and DeepSeek API for content analysis.

## Features

- Web crawling with configurable depth and domain restrictions
- AI-powered content analysis with DeepSeek API
- Multiple operation modes:
  - Summarize each page
  - Ask questions about crawled content
  - Custom prompts for specialized analysis
- Multi-language support (English and Hebrew)
- Technical report generation for each page
- Export options (JSON, CSV)

## Installation

1. Clone this repository
2. Install dependencies:
```
pip install -r requirements.txt
```

## Local Development

1. Set your DeepSeek API key as an environment variable:
```powershell
$env:DEEPSEEK_API_KEY = "your-api-key"
```

2. Run the Streamlit app:
```
streamlit run scraper.py
```

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

## License

MIT

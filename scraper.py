import streamlit as st
# Import crawl4ai and requests for scraping and API calls
import crawl4ai
import requests
from bs4 import BeautifulSoup
import json
import csv
import io
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from collections import Counter

# --- Helper Functions ---

def perform_crawl(target_url: str, depth: int = 1, max_pages: int = 20, timeout: int = 10, 
                domain_restriction: str = "Stay in same domain", custom_domains: str = "", 
                user_agent: str = "Mozilla/5.0"):
    """Crawl a website using crawl4ai and return a list of dicts with url and content."""
    results = []
    try:
        import requests
        from urllib.parse import urljoin, urlparse
        from bs4 import BeautifulSoup
        
        # Parse custom domains if provided
        allowed_domains = set()
        if domain_restriction == "Custom domain list" and custom_domains:
            allowed_domains = set(domain.strip() for domain in custom_domains.split('\n') if domain.strip())
        
        # Set up headers with user agent
        headers = {'User-Agent': user_agent}
        
        visited = set()
        to_visit = [(target_url, 0)]
        
        # Progress bar for crawling
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while to_visit and len(visited) < max_pages:
            current_url, current_depth = to_visit.pop(0)
            if current_url in visited or current_depth > depth:
                continue
                
            visited.add(current_url)
            status_text.text(f"Crawling: {current_url}")
            progress_bar.progress(min(len(visited) / max_pages, 1.0))
            
            try:
                response = requests.get(current_url, timeout=timeout, headers=headers)
                if response.status_code == 200:
                    results.append({"url": current_url, "content": response.text})
                    
                    if current_depth < depth:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        base_url = urlparse(current_url)
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
                                to_visit.append((href, current_depth + 1))
            except Exception as e:
                st.warning(f"Error fetching {current_url}: {e}")
        
        # Clear the progress indicators
        status_text.empty()
        progress_bar.empty()
        
    except Exception as e:
        st.error(f"Error during crawl: {e}")
    
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

# --- Streamlit UI ---
st.set_page_config(page_title="AI Web Scraper", layout="wide")
st.title("🤖 AI-Powered Web Scraper")
st.markdown("""
Easily scrape web data and process it with DeepSeek AI. Configure your crawl and analysis below.
""")

# --- UI Inputs ---
st.title("Web Scraper with DeepSeek AI")

# Input for target URL
target_url = st.text_input("Target URL", "https://example.com")

# Advanced crawling parameters
with st.expander("Advanced Crawling Parameters"):
    col1, col2 = st.columns(2)
    
    with col1:
        # Input for crawl depth
        crawl_depth = st.slider("Crawl Depth", min_value=1, max_value=5, value=1, help="How many links deep to crawl")
        
        # Input for max pages
        max_pages = st.number_input("Maximum Pages", min_value=1, max_value=100, value=20, help="Maximum number of pages to crawl")
        
        # Input for request timeout
        timeout = st.number_input("Request Timeout (seconds)", min_value=1, max_value=60, value=10, help="Timeout for each HTTP request")
    
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

# Input for keywords (optional)
keywords = st.text_input("Keywords (optional)", help="Comma-separated keywords to filter pages")

# Operation mode selection
operation = st.radio("Choose DeepSeek operation", ["Summarize each page", "Ask a question about crawl", "Custom prompt"], index=0)

# Question input if asking a question
user_question = ""
if operation == "Ask a question about crawl":
    summary_language = "English"  # default
    user_question = st.text_input("Your question about the crawled content")

# Custom prompt input
custom_prompt = ""
custom_language = "English"
if operation == "Summarize each page":
    summary_language = st.selectbox("Summary Language", ["English", "Hebrew"], index=0)

if operation == "Custom prompt": 
    # Language option
    custom_language = st.selectbox("Response Language", ["English", "Hebrew"], index=0)
    with st.expander("Custom Prompt Configuration", expanded=True):
        st.markdown("""### Custom Prompt Guidelines
        - Use `{content}` as a placeholder for the page content
        - Use `{url}` as a placeholder for the page URL
        - Keep prompts clear and specific for best results
        """)
        
        custom_prompt_template = st.text_area(
            "Custom Prompt Template", 
            """Analyze the following webpage content from {url}:

{content}

Provide a detailed analysis including:
1. Main topic and purpose
2. Key points or arguments
3. Target audience
4. Writing style and tone
5. Credibility assessment""", 
            height=200)
        
        # Choose summarization language
        summary_language = st.selectbox("Summary Language", ["English", "Hebrew"], index=0)
        
        custom_system_prompt = st.text_area(
            "System Prompt (Optional)", 
            """You are an expert web content analyst. Analyze the provided web content thoroughly and provide insightful, accurate analysis. Be objective and focus on the facts presented in the content.""", 
            height=100)

# DeepSeek API Key (for demo purposes, using provided key directly)
# SECURITY WARNING: Never hardcode API keys in production! Use st.secrets or environment variables.
# The API key is hardcoded here for this demo and the input field has been removed.
DEEPSEEK_API_KEY = "sk-54b8868459fe40ea9dd75b90740a5891"

# --- Scrape Button ---
if st.button("Start Scraping"):
    if not target_url:
        st.warning("Please enter a target URL.")
    # Removed API key check from UI as it's hardcoded
    else:
        st.info("Starting crawl with crawl4ai...")
        # --- Crawl4ai usage (placeholder) ---
        try:
            # Example: crawl4ai.crawl(url, depth=crawl_depth)
            # Replace with actual crawl4ai usage
            st.write(f"Crawling {target_url} to depth {crawl_depth}...")
            crawl_results = perform_crawl(target_url, crawl_depth)
            if crawl_results:
                st.success(f"Crawling complete! {len(crawl_results)} pages fetched.")
            else:
                st.error("No pages were fetched. Check the URL or crawl parameters.")
        except Exception as e:
            st.error(f"Crawling failed: {e}")
            crawl_results = []
        # --- DeepSeek API usage ---
        if crawl_results:
            # Convert HTML to plain text for each page
            for page in crawl_results:
                page["text"] = html_to_text(page["content"])
                page["report"] = generate_technical_report(page["content"], page["url"])

            st.info("Sending data to DeepSeek API...")
            def deepseek_chat(messages, system_prompt="You are a helpful AI assistant.", temperature=0.7, max_tokens=None):
                """Call the DeepSeek API for chat completion."""
                DEEPSEEK_API_KEY = "sk-54b8868459fe40ea9dd75b90740a5891"  # Hardcoded for demo purposes
                
                try:
                    # Build the request payload
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
                    
                    response = requests.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                        },
                        json=payload
                    )
                    
                    # Check for errors in the API response
                    if response.status_code != 200:
                        st.error(f"DeepSeek API Error: {response.status_code} - {response.text}")
                        return f"Error: API returned status code {response.status_code}"
                        
                    return response.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    st.error(f"DeepSeek API Error: {e}")
                    return f"Error: {e}"

            if operation == "Summarize each page":
                st.subheader("Page Summaries")

                # Helper to build prompt for a page
                def build_summary_prompt(page_text, page_url):
                    base_prompt = f"Please summarize the following webpage content from {page_url}:\n\n{page_text}"
                    if summary_language == "Hebrew":
                        base_prompt += "\n\nPlease respond in Hebrew."
                    return base_prompt

                summaries = [None]*len(crawl_results)
                progress = st.progress(0.0)
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_idx = {}
                    for idx, page in enumerate(crawl_results):
                        # Extract plain text
                        text = page["text"][:4000]
                        prompt_text = build_summary_prompt(text, page["url"])
                        future = executor.submit(
                            deepseek_chat,
                            [{"role": "user", "content": prompt_text}],
                            system_prompt=system_prompts[summary_style],
                            temperature=summary_temperature
                        )
                        future_to_idx[future] = idx
                    completed = 0
                    total = len(crawl_results)
                    for future in as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            summaries[idx] = future.result()
                        except Exception as e:
                            summaries[idx] = f"Error: {e}"
                        completed += 1
                        progress.progress(completed/total)
                progress.empty()

                # Display summaries
                for idx, (page, summary) in enumerate(zip(crawl_results, summaries), start=1):
                    with st.expander(f"Summary for {page['url']}"):
                        st.write(summary)
                    prompt = (
                        "Summarize the following web page content in 3-5 concise sentences.\n"\
                        "### Content:\n" + page["text"][:4000]
                    )
                    result = deepseek_chat([
                        {"role": "user", "content": prompt}
                    ])
                    summary = result.get("choices", [{}])[0].get("message", {}).get("content", str(result))
                    st.markdown(f"**Page {idx}: {page['url']}**")
                    st.write(summary)
            else:  # Ask a question about crawl
                if not user_question:
                    st.warning("Please enter a question to ask about the crawl.")
                else:
                    # Concatenate texts with limit
                    combined_text = "\n---\n".join([p["text"] for p in crawl_results])
                    combined_text = combined_text[:12000]  # truncate to stay within token limit
                    prompt = (
                        f"You are provided with combined text from multiple web pages. "
                        f"Answer the following question based on this content.\n\n"
                        f"### Question:\n{user_question}\n\n### Content:\n{combined_text}"
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
                if operation == "Summarize each page" and "summaries" in locals():
                    # Export summaries
                    summary_data = {page["url"]: summary for page, summary in zip(crawl_results, summaries)}
                    json_summary = json.dumps(summary_data, indent=2)
                    b64_summary = base64.b64encode(json_summary.encode()).decode()
                    filename_summary = f"summaries_{timestamp}.json"
                    href_summary = f'<a href="data:application/json;base64,{b64_summary}" download="{filename_summary}">Download Summaries (JSON)</a>'
                    st.markdown(href_summary, unsafe_allow_html=True)
                elif operation == "Ask a question about crawl" and "answer" in locals():
                    # Export Q&A
                    qa_data = {"question": user_question, "answer": answer}
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

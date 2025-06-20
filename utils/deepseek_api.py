"""
DeepSeek API integration for AI-powered content analysis.
"""

import requests
import time
import streamlit as st
import os

# Global variable for the API key
DEEPSEEK_API_KEY = ""

def set_api_key(api_key: str):
    """Set the DeepSeek API key"""
    global DEEPSEEK_API_KEY
    DEEPSEEK_API_KEY = api_key

def get_api_key():
    """Get DeepSeek API key from various sources"""
    global DEEPSEEK_API_KEY
    
    # Try to get from session state first
    if hasattr(st, 'session_state') and hasattr(st.session_state, 'deepseek_api_key'):
        return st.session_state.deepseek_api_key
    
    # Try Streamlit secrets
    try:
        return st.secrets["DEEPSEEK_API_KEY"]
    except:
        pass
    
    # Try environment variable
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        return env_key
    
    return DEEPSEEK_API_KEY

def deepseek_chat(messages, system_prompt="You are a helpful AI assistant.", temperature=0.7, max_tokens=None, retry_count=3):
    """Call the DeepSeek API for chat completion with retry logic."""
    api_key = get_api_key()
    
    if not api_key:
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
                    "Authorization": f"Bearer {api_key}"
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

def summarize_pages(crawl_results, summary_style="Professional", summary_language="English", temperature=0.7):
    """Summarize multiple pages using DeepSeek API"""
    
    # System prompts for different styles
    system_prompts = {
        "Professional": "You are a professional content analyst. Provide clear, structured summaries.",
        "Casual": "You are a friendly assistant. Provide easy-to-understand summaries in a conversational tone.",
        "Technical": "You are a technical writer. Focus on technical details and implementation aspects.",
        "Creative": "You are a creative writer. Make the summaries engaging and interesting to read."
    }
    
    def build_summary_prompt(page_text, page_url):
        base_prompt = f"Please summarize the following webpage content from {page_url}:\n\n{page_text}"
        if summary_language == "Hebrew":
            base_prompt += "\n\nPlease respond in Hebrew."
        return base_prompt
    
    summaries = []
    
    # Create progress bar
    progress_text = "Preparing to summarize pages..."
    progress_bar = st.progress(0, text=progress_text)
    
    total_pages = len(crawl_results)
    for i, page in enumerate(crawl_results):
        # Update progress
        progress_text = f"Summarizing page {i+1} of {total_pages}"
        progress_value = float(i) / float(total_pages)
        progress_bar.progress(progress_value, text=progress_text)
        
        # Extract text content (limit to 4000 chars)
        text = page.get("text", "")[:4000] if page.get("text") else ""
        
        # Build the prompt
        prompt_text = build_summary_prompt(text, page["url"])
        
        # Call DeepSeek API with proper error handling
        try:
            summary = deepseek_chat(
                [{"role": "user", "content": prompt_text}],
                system_prompt=system_prompts.get(summary_style, system_prompts["Professional"]),
                temperature=temperature
            )
            summaries.append(summary)
        except Exception as e:
            error_message = f"Error processing summary: {str(e)}"
            summaries.append(error_message)
            st.error(f"Error on page {i+1}: {str(e)}")
    
    # Complete the progress bar
    progress_bar.progress(1.0, text="Summarization complete!")
    time.sleep(0.5)
    progress_bar.empty()
    
    return summaries

def answer_question(crawl_results, question):
    """Answer a question based on crawled content using DeepSeek API"""
    
    # Concatenate texts with limit
    combined_text = "\n---\n".join([p.get("text", "") for p in crawl_results])
    combined_text = combined_text[:12000]  # truncate to stay within token limit
    
    prompt = (
        f"You are provided with combined text from multiple web pages. "
        f"Answer the following question based on this content.\n\n"
        f"### Question:\n{question}\n\n### Content:\n{combined_text}"
    )
    
    try:
        result = deepseek_chat([
            {"role": "user", "content": prompt}
        ])
        return result
    except Exception as e:
        return f"Error answering question: {str(e)}"

def analyze_content_with_ai(content, analysis_type="general"):
    """Analyze content using DeepSeek API for various purposes"""
    
    analysis_prompts = {
        "general": "Analyze this content and provide insights about its structure, purpose, and key information.",
        "seo": "Analyze this content from an SEO perspective. Identify keywords, content structure, and optimization opportunities.",
        "technical": "Perform a technical analysis of this content. Focus on technical implementation, frameworks, and architecture.",
        "business": "Analyze this content from a business perspective. Identify value propositions, target audience, and business model insights."
    }
    
    prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
    prompt += f"\n\nContent to analyze:\n{content[:8000]}"  # Limit content length
    
    try:
        result = deepseek_chat([
            {"role": "user", "content": prompt}
        ])
        return result
    except Exception as e:
        return f"Error analyzing content: {str(e)}" 
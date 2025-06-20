"""
DeepSeek API integration for AI-powered content analysis.
"""

import requests
import time
import streamlit as st
import os

from utils.error_handler import APIException, global_error_handler, handle_errors
from utils.logger import get_logger, scraper_logger
from utils.validators import ParameterValidator

# Get logger for this module
logger = get_logger("deepseek_api")

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

@handle_errors(exceptions=(APIException, requests.RequestException), max_retries=2)
def deepseek_chat(messages, system_prompt="You are a helpful AI assistant.", temperature=0.7, max_tokens=None, retry_count=3):
    """
    Call the DeepSeek API for chat completion with validation and error handling.
    
    Args:
        messages: List of message dictionaries
        system_prompt: System prompt for the AI
        temperature: AI temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        retry_count: Number of retries (deprecated, use global error handler)
        
    Returns:
        AI response content
        
    Raises:
        APIException: If API call fails or validation fails
    """
    api_key = get_api_key()
    
    if not api_key:
        raise APIException("DeepSeek API key is required but not provided")
    
    # Validate API parameters
    validation_result = ParameterValidator.validate_ai_params(api_key, temperature, max_tokens)
    if not validation_result.is_valid:
        error_msg = f"Invalid API parameters: {'; '.join(validation_result.errors)}"
        logger.error(error_msg)
        raise APIException(error_msg, {"validation_errors": validation_result.errors})
    
    validated_params = validation_result.value
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            *messages
        ],
        "temperature": validated_params['temperature']
    }
    
    # Add max_tokens if specified
    if validated_params['max_tokens']:
        payload["max_tokens"] = validated_params['max_tokens']
    
    start_time = time.time()
    
    try:
        logger.debug(f"Making DeepSeek API call with {len(messages)} messages")
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {validated_params['api_key']}"
            },
            json=payload,
            timeout=30
        )
        
        duration = time.time() - start_time
        
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Log successful API call
        scraper_logger.log_api_call(
            "DeepSeek", 
            "chat/completions", 
            "success", 
            duration
        )
        
        logger.info(f"DeepSeek API call successful in {duration:.2f}s")
        return content
        
    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        error_msg = f"DeepSeek API request failed: {str(e)}"
        logger.error(error_msg)
        
        # Log failed API call
        scraper_logger.log_api_call(
            "DeepSeek", 
            "chat/completions", 
            "error", 
            duration
        )
        
        raise APIException(error_msg, {
            "duration": duration,
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
            "original_error": str(e)
        })
    except (KeyError, IndexError) as e:
        error_msg = f"Invalid DeepSeek API response format: {str(e)}"
        logger.error(error_msg)
        raise APIException(error_msg, {"response_error": str(e)})

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
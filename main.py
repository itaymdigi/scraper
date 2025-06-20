"""
Main entry point for the Advanced Web Scraper & Analyzer.
"""

import streamlit as st
import json
import base64
import datetime
import io
import csv

# Import our modules
from config.settings import PAGE_TITLE, PAGE_ICON, LAYOUT, DEFAULT_PORT, DOMAIN_RESTRICTIONS
from core.crawler import perform_crawl, html_to_text
from analysis.technical_report import generate_technical_report
from visualization.charts import (
    create_element_distribution_chart, 
    create_color_palette_visualization,
    create_technology_stack_chart,
    create_performance_metrics_chart,
    create_seo_accessibility_dashboard
)
from blueprint.generator import generate_website_blueprint, generate_html_template
from utils.helpers import generate_report_summary
from utils.cache import clear_cache, get_cache_stats
from utils.deepseek_api import (
    deepseek_chat, summarize_pages, answer_question, 
    analyze_content_with_ai, set_api_key, get_api_key
)


def setup_page_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=LAYOUT,
        initial_sidebar_state="expanded"
    )


def create_sidebar():
    """Create and configure the sidebar"""
    st.sidebar.header("🕷️ Web Scraper Settings")
    
    # URL input
    target_url = st.sidebar.text_input("🌐 Target URL", 
                                      placeholder="https://example.com")
    
    # Advanced settings
    with st.sidebar.expander("⚙️ Advanced Settings"):
        depth = st.slider("🔍 Crawl Depth", 1, 5, 1)
        max_pages = st.slider("📄 Max Pages", 1, 100, 20)
        timeout = st.slider("⏱️ Timeout (seconds)", 5, 60, 10)
        max_workers = st.slider("👥 Max Workers", 1, 20, 5)
        
        # Domain restrictions
        domain_restriction = st.selectbox("🌍 Domain Restriction", DOMAIN_RESTRICTIONS)
        custom_domains = ""
        if domain_restriction == "Custom domain list":
            custom_domains = st.text_area("📝 Custom Domains (one per line)")
        
        # Additional options
        user_agent = st.text_input("🤖 User Agent", 
                                  value="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        respect_robots = st.checkbox("🤖 Respect robots.txt", value=True)
        use_cache = st.checkbox("💾 Use Cache", value=True)
    
    # Operation mode
    operation_mode = st.sidebar.selectbox(
        "🎯 Operation Mode",
        ["🔍 Crawl Only", "📊 Technical Analysis", "✨ Summarize", "❓ Q&A with AI"]
    )
    
    # DeepSeek API settings (only show if AI features are selected)
    if operation_mode in ["✨ Summarize", "❓ Q&A with AI"]:
        with st.sidebar.expander("🧠 AI Settings (DeepSeek)"):
            # API Key input
            current_key = get_api_key()
            api_key = st.text_input(
                "🔑 DeepSeek API Key", 
                value=current_key if current_key else "",
                type="password",
                help="Enter your DeepSeek API key for AI analysis"
            )
            
            if api_key and api_key != current_key:
                st.session_state.deepseek_api_key = api_key
                set_api_key(api_key)
            
            # AI-specific settings for summarization
            if operation_mode == "✨ Summarize":
                summary_style = st.selectbox(
                    "📝 Summary Style",
                    ["Professional", "Casual", "Technical", "Creative"]
                )
                summary_language = st.selectbox(
                    "🌐 Summary Language",
                    ["English", "Hebrew"]
                )
                temperature = st.slider(
                    "🌡️ AI Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.7,
                    step=0.1,
                    help="Lower values = more focused, Higher values = more creative"
                )
            else:
                summary_style = "Professional"
                summary_language = "English"
                temperature = 0.7
            
            # Question input for Q&A mode
            if operation_mode == "❓ Q&A with AI":
                question = st.text_area(
                    "❓ Your Question",
                    placeholder="What would you like to know about the crawled content?",
                    help="Ask any question about the content that will be crawled"
                )
            else:
                question = ""
    else:
        summary_style = "Professional"
        summary_language = "English"
        temperature = 0.7
        question = ""
    
    # Cache management
    with st.sidebar.expander("💾 Cache Management"):
        cache_stats = get_cache_stats()
        st.write(f"**Memory entries:** {cache_stats['memory_entries']}")
        st.write(f"**Disk entries:** {cache_stats['disk_entries']}")
        
        if st.button("🗑️ Clear Cache"):
            clear_cache()
            st.success("Cache cleared!")
            st.rerun()
    
    return {
        'target_url': target_url,
        'depth': depth,
        'max_pages': max_pages,
        'timeout': timeout,
        'max_workers': max_workers,
        'domain_restriction': domain_restriction,
        'custom_domains': custom_domains,
        'user_agent': user_agent,
        'respect_robots': respect_robots,
        'use_cache': use_cache,
        'operation_mode': operation_mode,
        'summary_style': summary_style,
        'summary_language': summary_language,
        'temperature': temperature,
        'question': question
    }


def display_technical_analysis(crawl_results):
    """Display technical analysis results with tabbed interface"""
    if not crawl_results:
        st.warning("No crawl results to analyze.")
        return
    
    # URL selection for analysis
    urls = [page["url"] for page in crawl_results]
    selected_url = st.selectbox("🎯 Select URL for Technical Analysis", urls)
    
    # Find selected page data
    selected_page = next((page for page in crawl_results if page["url"] == selected_url), None)
    if not selected_page:
        st.error("Selected page not found.")
        return
    
    # Generate technical report
    with st.spinner("🔍 Generating comprehensive technical report..."):
        report = generate_technical_report(selected_page["content"], selected_url)
    
    # Display results in tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Overview", "📈 Visual Analysis", "⚡ Performance", 
        "🔍 SEO & Accessibility", "🛠️ Technology Stack", 
        "🏗️ Website Blueprint", "🧠 AI Analysis", "📋 Raw Data"
    ])
    
    with tab1:
        display_overview_tab(report)
    
    with tab2:
        display_visual_analysis_tab(report)
    
    with tab3:
        display_performance_tab(report)
    
    with tab4:
        display_seo_accessibility_tab(report)
    
    with tab5:
        display_technology_tab(report)
    
    with tab6:
        display_blueprint_tab(report, selected_url)
    
    with tab7:
        display_ai_analysis_tab(selected_page, selected_url)
    
    with tab8:
        display_raw_data_tab(report)


def display_overview_tab(report):
    """Display overview tab content"""
    st.markdown("### 📊 Website Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_elements = report.get('structure_analysis', {}).get('total_elements', 0)
        st.metric("Total Elements", total_elements)
    
    with col2:
        performance_score = report.get('performance_analysis', {}).get('overall_score', 0)
        st.metric("Performance Score", f"{performance_score}/100")
    
    with col3:
        tech_count = len(report.get('technology_stack', {}).get('libraries', []))
        st.metric("Technologies", tech_count)
    
    with col4:
        seo_score = len(report.get('seo_analysis', {}).get('meta_tags', {}))
        st.metric("SEO Tags", seo_score)
    
    # Basic information
    st.markdown("#### 📄 Basic Information")
    basic_info = report.get('basic_info', {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Title:** {basic_info.get('title', 'N/A')}")
        st.write(f"**Language:** {basic_info.get('language', 'N/A')}")
        st.write(f"**Charset:** {basic_info.get('charset', 'N/A')}")
    
    with col2:
        st.write(f"**Description:** {basic_info.get('description', 'N/A')[:100]}...")
        st.write(f"**Viewport:** {basic_info.get('viewport', 'N/A')}")
        st.write(f"**Favicon:** {'✅' if basic_info.get('favicon') else '❌'}")


def display_visual_analysis_tab(report):
    """Display visual analysis tab content"""
    st.markdown("### 📈 Visual Analysis")
    
    # Element distribution chart
    element_counts = report.get('structure_analysis', {}).get('element_counts', {})
    if element_counts:
        try:
            fig = create_element_distribution_chart(element_counts)
            if fig:
                st.pyplot(fig)
                import matplotlib.pyplot as plt
                plt.close(fig)
            else:
                st.info("📊 Element distribution chart not available")
        except Exception as e:
            st.error(f"Error creating element distribution chart: {e}")
    
    # Color palette visualization
    color_palette = report.get('styling', {}).get('color_palette', [])
    if color_palette:
        try:
            fig = create_color_palette_visualization(color_palette)
            if fig:
                st.pyplot(fig)
                import matplotlib.pyplot as plt
                plt.close(fig)
            else:
                st.info("🎨 Color palette visualization not available")
        except Exception as e:
            st.error(f"Error creating color palette visualization: {e}")
    else:
        st.info("🎨 No color palette detected")


def display_performance_tab(report):
    """Display performance tab content"""
    st.markdown("### ⚡ Performance Analysis")
    
    performance_data = report.get('performance_analysis', {})
    if performance_data:
        try:
            fig = create_performance_metrics_chart(performance_data)
            if fig:
                st.pyplot(fig)
                import matplotlib.pyplot as plt
                plt.close(fig)
            else:
                st.info("⚡ Performance chart not available")
        except Exception as e:
            st.error(f"Error creating performance chart: {e}")
    else:
        st.info("⚡ No performance data available")


def display_seo_accessibility_tab(report):
    """Display SEO and accessibility tab content"""
    st.markdown("### 🔍 SEO & Accessibility Analysis")
    
    seo_data = report.get('seo_analysis', {})
    accessibility_data = report.get('accessibility', {})
    
    if seo_data or accessibility_data:
        try:
            fig = create_seo_accessibility_dashboard(seo_data, accessibility_data)
            if fig:
                st.pyplot(fig)
                import matplotlib.pyplot as plt
                plt.close(fig)
            else:
                st.info("🔍 SEO/Accessibility dashboard not available")
        except Exception as e:
            st.error(f"Error creating SEO/Accessibility dashboard: {e}")
    else:
        st.info("🔍 No SEO or accessibility data available")


def display_technology_tab(report):
    """Display technology stack tab content"""
    st.markdown("### 🛠️ Technology Stack")
    
    tech_stack = report.get('technology_stack', {})
    if tech_stack:
        try:
            fig = create_technology_stack_chart(tech_stack)
            if fig:
                st.pyplot(fig)
                import matplotlib.pyplot as plt
                plt.close(fig)
            else:
                st.info("🛠️ Technology stack chart not available")
        except Exception as e:
            st.error(f"Error creating technology stack chart: {e}")
    else:
        st.info("🛠️ No technology stack data available")


def display_ai_analysis_tab(selected_page, selected_url):
    """Display AI analysis tab content"""
    st.markdown("### 🧠 AI-Powered Content Analysis")
    
    # Check if API key is available
    if not get_api_key():
        st.warning("🔑 Enter your DeepSeek API key in the sidebar to enable AI analysis features.")
        return
    
    # Analysis type selection
    analysis_type = st.selectbox(
        "🎯 Analysis Type",
        ["general", "seo", "technical", "business"],
        format_func=lambda x: {
            "general": "🔍 General Analysis",
            "seo": "📈 SEO Analysis", 
            "technical": "⚙️ Technical Analysis",
            "business": "💼 Business Analysis"
        }[x]
    )
    
    if st.button("🚀 Analyze with AI"):
        with st.spinner(f"🤖 Performing {analysis_type} analysis..."):
            try:
                # Get page content
                content = selected_page.get("text", "")[:8000]  # Limit content length
                
                # Perform AI analysis
                analysis_result = analyze_content_with_ai(content, analysis_type)
                
                st.markdown("### 📊 AI Analysis Results")
                if isinstance(analysis_result, str) and analysis_result.startswith("Error"):
                    st.error(analysis_result)
                else:
                    st.markdown(str(analysis_result))
                
                # Export analysis
                if st.button("📥 Export Analysis"):
                    analysis_data = {
                        "url": selected_url,
                        "analysis_type": analysis_type,
                        "analysis": analysis_result,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    analysis_json = json.dumps(analysis_data, indent=2, ensure_ascii=False)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.download_button(
                        label="📥 Download Analysis (JSON)",
                        data=analysis_json,
                        file_name=f"ai_analysis_{analysis_type}_{timestamp}.json",
                        mime="application/json"
                    )
                    
            except Exception as e:
                st.error(f"❌ Error performing AI analysis: {str(e)}")


def display_blueprint_tab(report, selected_url):
    """Display website blueprint tab content"""
    st.markdown("### 🏗️ Website Blueprint & Reconstruction Guide")
    
    # Generate blueprint
    blueprint = generate_website_blueprint(report)
    
    # Implementation tasks
    st.markdown("#### 📋 Implementation Priority Tasks")
    if blueprint.get("implementation_guide", {}).get("priority_tasks"):
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
    
    # HTML Template
    st.markdown("#### 📄 Generated HTML Template")
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


def display_raw_data_tab(report):
    """Display raw data tab content"""
    st.markdown("### 📋 Raw Technical Data")
    
    # Expandable sections for different data types
    sections = [
        ("🏗️ Structure Analysis", "structure_analysis"),
        ("📝 Content Analysis", "content"),
        ("🖼️ Media Analysis", "media"),
        ("🔗 Links Analysis", "links"),
        ("🎨 Styling Analysis", "styling"),
        ("🔒 Security Analysis", "security"),
        ("🧩 UI Components", "ui_components"),
    ]
    
    for title, key in sections:
        with st.expander(title):
            data = report.get(key, {})
            if data:
                st.json(data)
            else:
                st.write("No data available")
    
    # Complete raw data
    with st.expander("📊 Complete Raw Report"):
        st.json(report)


def export_results(crawl_results):
    """Handle result exports"""
    if not crawl_results:
        return
    
    st.subheader("📤 Export Results")
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        json_data = json.dumps(crawl_results, indent=2)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="📥 Download JSON",
            data=json_data,
            file_name=f"crawl_results_{timestamp}.json",
            mime="application/json"
        )
    
    with col2:
        # CSV export
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(["URL", "Text Preview"])
        
        for page in crawl_results:
            text_preview = page.get("text", "")[:500]
            if len(page.get("text", "")) > 500:
                text_preview += "..."
            csv_writer.writerow([page["url"], text_preview])
        
        st.download_button(
            label="📥 Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"crawl_results_{timestamp}.csv",
            mime="text/csv"
        )


def main():
    """Main application function"""
    setup_page_config()
    
    # Title and description
    st.title("🕷️ Advanced Web Scraper & Analyzer")
    st.markdown("A comprehensive tool for web crawling, analysis, and website blueprint generation.")
    
    # Sidebar configuration
    config = create_sidebar()
    
    # Main content area
    if not config['target_url']:
        st.info("👈 Enter a URL in the sidebar to get started!")
        return
    
    # URL validation
    if not config['target_url'].startswith(('http://', 'https://')):
        st.error("❌ Please enter a valid URL starting with http:// or https://")
        return
    
    # Start crawling button
    if st.button("🚀 Start Crawling", type="primary"):
        with st.spinner("🕷️ Crawling website..."):
            try:
                # Perform crawl
                crawl_results = perform_crawl(
                    target_url=config['target_url'],
                    depth=config['depth'],
                    max_pages=config['max_pages'],
                    timeout=config['timeout'],
                    domain_restriction=config['domain_restriction'],
                    custom_domains=config['custom_domains'],
                    user_agent=config['user_agent'],
                    max_workers=config['max_workers'],
                    respect_robots=config['respect_robots'],
                    use_cache=config['use_cache']
                )
                
                if not crawl_results:
                    st.error("❌ No pages were successfully crawled. Please check the URL and try again.")
                    return
                
                # Convert HTML to text for each page
                for page in crawl_results:
                    page["text"] = html_to_text(page["content"])
                
                # Store results in session state
                st.session_state.crawl_results = crawl_results
                st.session_state.config = config
                
                st.success(f"✅ Successfully crawled {len(crawl_results)} pages!")
                
            except Exception as e:
                st.error(f"❌ Error during crawling: {str(e)}")
                return
    
    # Display results if available
    if hasattr(st.session_state, 'crawl_results') and st.session_state.crawl_results:
        crawl_results = st.session_state.crawl_results
        config = st.session_state.config
        
        # Display based on operation mode
        if config['operation_mode'] == "📊 Technical Analysis":
            display_technical_analysis(crawl_results)
        
        elif config['operation_mode'] == "🔍 Crawl Only":
            st.subheader("📄 Crawled Pages")
            for i, page in enumerate(crawl_results, 1):
                with st.expander(f"{i}. {page['url']}"):
                    st.write(f"**Content Preview:** {page['text'][:500]}...")
        
        elif config['operation_mode'] == "✨ Summarize":
            # Check if API key is available
            if not get_api_key():
                st.error("❌ DeepSeek API key is required for summarization. Please enter your API key in the sidebar.")
            else:
                st.subheader("🧠 AI-Powered Summaries")
                
                with st.spinner("🤖 Generating AI summaries using DeepSeek..."):
                    try:
                        summaries = summarize_pages(
                            crawl_results, 
                            summary_style=config['summary_style'],
                            summary_language=config['summary_language'],
                            temperature=config['temperature']
                        )
                        
                        # Display summaries
                        st.success(f"✅ Generated {len(summaries)} summaries!")
                        
                        for i, (page, summary) in enumerate(zip(crawl_results, summaries), 1):
                            with st.expander(f"📝 Summary {i}: {page['url']}", expanded=True):
                                if isinstance(summary, str) and summary.startswith("Error"):
                                    st.error(summary)
                                else:
                                    st.markdown(str(summary))
                                    
                                # Show original content preview
                                with st.expander("👀 Original Content Preview"):
                                    st.write(page['text'][:1000] + "..." if len(page['text']) > 1000 else page['text'])
                        
                        # Export summaries
                        if st.button("📥 Export Summaries"):
                            summary_data = []
                            for page, summary in zip(crawl_results, summaries):
                                summary_data.append({
                                    "url": page["url"],
                                    "summary": summary,
                                    "style": config['summary_style'],
                                    "language": config['summary_language']
                                })
                            
                            summary_json = json.dumps(summary_data, indent=2, ensure_ascii=False)
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                            st.download_button(
                                label="📥 Download Summaries (JSON)",
                                data=summary_json,
                                file_name=f"ai_summaries_{timestamp}.json",
                                mime="application/json"
                            )
                        
                    except Exception as e:
                        st.error(f"❌ Error generating summaries: {str(e)}")
        
        elif config['operation_mode'] == "❓ Q&A with AI":
            # Check if API key is available
            if not get_api_key():
                st.error("❌ DeepSeek API key is required for Q&A. Please enter your API key in the sidebar.")
            elif not config['question']:
                st.warning("❓ Please enter a question in the sidebar to get started.")
            else:
                st.subheader("🤖 AI Question & Answer")
                
                with st.spinner(f"🧠 Analyzing content and answering: '{config['question']}'"):
                    try:
                        answer = answer_question(crawl_results, config['question'])
                        
                        st.markdown("### 💬 Your Question:")
                        st.info(config['question'])
                        
                        st.markdown("### 🤖 DeepSeek Answer:")
                        if isinstance(answer, str) and answer.startswith("Error"):
                            st.error(answer)
                        else:
                            st.markdown(str(answer))
                        
                        # Show sources
                        st.markdown("### 📚 Sources Analyzed:")
                        for i, page in enumerate(crawl_results, 1):
                            st.write(f"{i}. {page['url']}")
                        
                        # Export Q&A
                        if st.button("📥 Export Q&A"):
                            qa_data = {
                                "question": config['question'],
                                "answer": answer,
                                "sources": [page["url"] for page in crawl_results],
                                "timestamp": datetime.datetime.now().isoformat()
                            }
                            
                            qa_json = json.dumps(qa_data, indent=2, ensure_ascii=False)
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                            st.download_button(
                                label="📥 Download Q&A (JSON)",
                                data=qa_json,
                                file_name=f"ai_qa_{timestamp}.json",
                                mime="application/json"
                            )
                        
                    except Exception as e:
                        st.error(f"❌ Error answering question: {str(e)}")
        
        # Export options
        export_results(crawl_results)
        
        # Raw results expander
        with st.expander("📋 Show Raw Crawl Results"):
            st.json(crawl_results)


if __name__ == "__main__":
    main() 
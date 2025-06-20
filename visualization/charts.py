"""
Chart generation for technical analysis visualization.
"""

try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    np = None

from config.settings import CHART_FIGSIZE, CHART_DPI


def create_element_distribution_chart(element_counts):
    """Create a pie chart for HTML element distribution"""
    if not MATPLOTLIB_AVAILABLE or not element_counts:
        return None
    
    # Get top 10 elements for better visualization
    top_elements = dict(list(element_counts.items())[:10])
    
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE, dpi=CHART_DPI)
    colors = plt.cm.Set3(np.linspace(0, 1, len(top_elements)))
    
    wedges, texts, autotexts = ax.pie(
        top_elements.values(), 
        labels=top_elements.keys(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    
    ax.set_title('HTML Element Distribution', fontsize=16, fontweight='bold')
    
    # Enhance text readability
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    plt.tight_layout()
    return fig


def create_color_palette_visualization(color_palette):
    """Create a visual representation of the color palette"""
    if not MATPLOTLIB_AVAILABLE or not color_palette:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=CHART_DPI)
    
    colors = []
    counts = []
    labels = []
    
    for item in color_palette[:10]:  # Show top 10 colors
        color = item['color']
        count = item['count']
        
        colors.append(color)
        counts.append(count)
        labels.append(f"{color}\n({count} uses)")
    
    # Create horizontal bar chart
    bars = ax.barh(range(len(colors)), counts, color=colors)
    
    ax.set_yticks(range(len(colors)))
    ax.set_yticklabels(labels)
    ax.set_xlabel('Usage Count')
    ax.set_title('Color Palette Usage', fontsize=16, fontweight='bold')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                str(counts[i]), ha='left', va='center')
    
    plt.tight_layout()
    return fig


def create_technology_stack_chart(tech_stack):
    """Create a visualization for technology stack"""
    if not MATPLOTLIB_AVAILABLE or (not tech_stack.get('libraries') and not tech_stack.get('frameworks')):
        return None
    
    # Combine libraries and frameworks
    all_tech = []
    if tech_stack.get('libraries'):
        for lib in tech_stack['libraries']:
            all_tech.append(f"{lib['name']} ({lib.get('version', 'unknown')})")
    
    if tech_stack.get('frameworks'):
        for fw in tech_stack['frameworks']:
            all_tech.append(fw['name'])
    
    if tech_stack.get('css_frameworks'):
        for css_fw in tech_stack['css_frameworks']:
            all_tech.append(f"{css_fw['name']} (CSS)")
    
    if not all_tech:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=CHART_DPI)
    
    # Create horizontal bar chart
    y_pos = np.arange(len(all_tech))
    counts = [1] * len(all_tech)  # Each technology appears once
    
    bars = ax.barh(y_pos, counts, color=plt.cm.tab10(np.linspace(0, 1, len(all_tech))))
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(all_tech)
    ax.set_xlabel('Detected')
    ax.set_title('Technology Stack', fontsize=16, fontweight='bold')
    
    # Remove x-axis ticks since they're not meaningful
    ax.set_xticks([])
    
    plt.tight_layout()
    return fig


def create_performance_metrics_chart(performance_data):
    """Create a performance metrics visualization"""
    if not MATPLOTLIB_AVAILABLE or not performance_data:
        return None
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10), dpi=CHART_DPI)
    
    # 1. Total Requests
    ax1.bar(['Total Requests'], [performance_data.get('total_requests', 0)], 
            color='skyblue')
    ax1.set_title('External Requests')
    ax1.set_ylabel('Count')
    
    # 2. Performance Score
    score = performance_data.get('overall_score', 0)
    ax2.pie([score, 100-score], labels=['Score', 'Remaining'], 
            colors=['green', 'lightgray'], autopct='%1.1f%%')
    ax2.set_title('Performance Score')
    
    # 3. Lazy Loading
    lazy_count = performance_data.get('lazy_loading', 0)
    ax3.bar(['Lazy Loaded'], [lazy_count], color='green')
    ax3.set_title('Lazy Loading')
    ax3.set_ylabel('Count')
    
    # 4. Preload Hints
    preload_count = len(performance_data.get('preload_hints', []))
    ax4.bar(['Preload Hints'], [preload_count], color='purple')
    ax4.set_title('Resource Preload Hints')
    ax4.set_ylabel('Count')
    
    plt.tight_layout()
    return fig


def create_seo_accessibility_dashboard(seo_data, accessibility_data):
    """Create SEO and accessibility dashboard"""
    if not MATPLOTLIB_AVAILABLE or (not seo_data and not accessibility_data):
        return None
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10), dpi=CHART_DPI)
    
    # 1. SEO Meta Tags
    if seo_data:
        meta_count = len(seo_data.get('meta_tags', {}))
        ax1.bar(['Meta Tags'], [meta_count], color='blue')
        ax1.set_title('SEO Meta Tags')
        ax1.set_ylabel('Count')
    
    # 2. Alt Text Analysis
    if seo_data and 'alt_texts' in seo_data:
        alt_data = seo_data['alt_texts']
        ax2.pie([alt_data.get('present', 0), alt_data.get('missing', 0)], 
                labels=['With Alt Text', 'Missing Alt Text'],
                colors=['green', 'red'], autopct='%1.1f%%')
        ax2.set_title('Image Alt Text Coverage')
    
    # 3. ARIA Labels
    if accessibility_data:
        aria_count = accessibility_data.get('aria_labels', 0)
        ax3.bar(['ARIA Labels'], [aria_count], color='orange')
        ax3.set_title('ARIA Labels')
        ax3.set_ylabel('Count')
    
    # 4. Form Labels
    if accessibility_data:
        form_labels = accessibility_data.get('form_labels', 0)
        ax4.bar(['Form Labels'], [form_labels], color='purple')
        ax4.set_title('Form Labels')
        ax4.set_ylabel('Count')
    
    plt.tight_layout()
    return fig 
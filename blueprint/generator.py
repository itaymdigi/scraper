"""
Website blueprint generation for reconstruction purposes.
"""

import datetime


def generate_website_blueprint(report):
    """Generate a comprehensive blueprint for website reconstruction"""
    blueprint = {
        "metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "source_url": report.get("url", ""),
            "analysis_version": "1.0"
        },
        "html_structure": {
            "doctype": "html5",
            "language": report.get("basic_info", {}).get("language", "en"),
            "charset": report.get("basic_info", {}).get("charset", "UTF-8")
        },
        "head_elements": {
            "title": report.get("basic_info", {}).get("title", ""),
            "meta_description": report.get("basic_info", {}).get("description", ""),
            "viewport": report.get("basic_info", {}).get("viewport", "width=device-width, initial-scale=1.0"),
            "favicon": report.get("basic_info", {}).get("favicon", "")
        },
        "body_structure": {
            "semantic_elements": report.get("structure_analysis", {}).get("semantic_structure", {}),
            "total_elements": report.get("structure_analysis", {}).get("total_elements", 0)
        },
        "content_blueprint": {
            "headings": report.get("content", {}).get("headings", {}),
            "paragraphs": report.get("content", {}).get("paragraphs", 0),
            "lists": report.get("content", {}).get("lists", {}),
            "tables": report.get("content", {}).get("tables", 0)
        },
        "styling_guide": {
            "color_palette": report.get("styling", {}).get("color_palette", []),
            "fonts": report.get("styling", {}).get("fonts", []),
            "css_frameworks": report.get("styling", {}).get("css_frameworks", [])
        },
        "media_assets": {
            "images": len(report.get("media", {}).get("images", [])),
            "videos": len(report.get("media", {}).get("videos", [])),
            "audio": len(report.get("media", {}).get("audio", []))
        },
        "navigation_structure": {
            "internal_links": len(report.get("links", {}).get("internal", [])),
            "external_links": len(report.get("links", {}).get("external", [])),
            "navigation_elements": len(report.get("ui_components", {}).get("navigation", []))
        },
        "javascript_blueprint": {
            "libraries": report.get("technology_stack", {}).get("libraries", []),
            "frameworks": report.get("technology_stack", {}).get("frameworks", [])
        },
        "ui_components": {
            "buttons": len(report.get("ui_components", {}).get("buttons", [])),
            "forms": len(report.get("ui_components", {}).get("forms", [])),
            "modals": report.get("ui_components", {}).get("modals", 0),
            "carousels": report.get("ui_components", {}).get("carousels", 0)
        },
        "performance_requirements": {
            "lazy_loading": report.get("performance_analysis", {}).get("lazy_loading", 0) > 0,
            "preload_hints": len(report.get("performance_analysis", {}).get("preload_hints", [])) > 0,
            "performance_score": report.get("performance_analysis", {}).get("overall_score", 0)
        },
        "seo_requirements": {
            "meta_tags": list(report.get("seo_analysis", {}).get("meta_tags", {}).keys()),
            "open_graph": bool(report.get("seo_analysis", {}).get("open_graph", {})),
            "twitter_cards": bool(report.get("seo_analysis", {}).get("twitter_cards", {}))
        },
        "accessibility_requirements": {
            "aria_labels": report.get("accessibility", {}).get("aria_labels", 0) > 0,
            "alt_texts": report.get("seo_analysis", {}).get("alt_texts", {}).get("present", 0) > 0,
            "form_labels": report.get("accessibility", {}).get("form_labels", 0) > 0
        },
        "security_considerations": {
            "external_domains": len(report.get("security", {}).get("external_domains", [])),
            "mixed_content": len(report.get("security", {}).get("mixed_content", [])) > 0
        },
        "implementation_guide": {
            "priority_tasks": _generate_priority_tasks(report),
            "estimated_complexity": _estimate_complexity(report)
        }
    }
    
    return blueprint


def generate_html_template(blueprint):
    """Generate HTML template from blueprint"""
    html_template = f"""<!DOCTYPE html>
<html lang="{blueprint['html_structure']['language']}">
<head>
    <meta charset="{blueprint['html_structure']['charset']}">
    <meta name="viewport" content="{blueprint['head_elements']['viewport']}">
    <title>{blueprint['head_elements']['title']}</title>
    <meta name="description" content="{blueprint['head_elements']['meta_description']}">
    
    <!-- CSS Files -->
    <link rel="stylesheet" href="styles.css">
    
    <!-- Favicon -->
    {f'<link rel="icon" href="{blueprint["head_elements"]["favicon"]}">' if blueprint["head_elements"]["favicon"] else "<!-- Add favicon -->"}
</head>
<body>
    <!-- Header Section -->
    <header>
        <nav>
            <!-- Navigation menu -->
            <ul>
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </nav>
    </header>
    
    <!-- Main Content -->
    <main>
        <!-- Hero Section -->
        <section class="hero">
            <h1>{blueprint['head_elements']['title']}</h1>
            <p>{blueprint['head_elements']['meta_description']}</p>
        </section>
        
        <!-- Content Sections -->
        <section class="content">
            <!-- Add your content here based on the original structure -->
            <h2>Section Title</h2>
            <p>Section content...</p>
        </section>
    </main>
    
    <!-- Footer -->
    <footer>
        <p>&copy; 2024 Website. All rights reserved.</p>
    </footer>
    
    <!-- JavaScript -->
    <script src="scripts.js"></script>
</body>
</html>"""
    
    return html_template


def _generate_priority_tasks(report):
    """Generate priority tasks for implementation"""
    tasks = []
    
    # High priority tasks
    if not report.get("basic_info", {}).get("title"):
        tasks.append({
            "priority": "HIGH",
            "task": "Add page title",
            "impact": "Critical for SEO and user experience"
        })
    
    if not report.get("basic_info", {}).get("description"):
        tasks.append({
            "priority": "HIGH", 
            "task": "Add meta description",
            "impact": "Important for SEO and search results"
        })
    
    # Medium priority tasks
    if report.get("seo_analysis", {}).get("alt_texts", {}).get("missing", 0) > 0:
        tasks.append({
            "priority": "MEDIUM",
            "task": "Add alt text to images",
            "count": report["seo_analysis"]["alt_texts"]["missing"],
            "impact": "Improves accessibility and SEO"
        })
    
    # Low priority tasks
    if report.get("performance_analysis", {}).get("lazy_loading", 0) == 0:
        tasks.append({
            "priority": "LOW",
            "task": "Implement lazy loading for images",
            "impact": "Improves page load performance"
        })
    
    return tasks


def _estimate_complexity(report):
    """Estimate implementation complexity"""
    complexity_score = 0
    
    # Add complexity based on various factors
    complexity_score += report.get("structure_analysis", {}).get("total_elements", 0) // 100
    complexity_score += len(report.get("technology_stack", {}).get("libraries", [])) * 2
    complexity_score += len(report.get("ui_components", {}).get("forms", [])) * 3
    complexity_score += report.get("ui_components", {}).get("modals", 0) * 2
    
    if complexity_score < 5:
        return "Simple"
    elif complexity_score < 15:
        return "Moderate"
    else:
        return "Complex" 
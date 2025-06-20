"""
Technical report generation for comprehensive website analysis.
"""

import datetime
from bs4 import BeautifulSoup
from collections import Counter
import re
from urllib.parse import urlparse, urljoin

from config.settings import (
    LIBRARIES_PATTERNS, ANALYTICS_PATTERNS, IMAGE_EXTENSIONS, 
    VIDEO_EXTENSIONS, AUDIO_EXTENSIONS, COLOR_PALETTE_SIZE
)
from utils.helpers import is_external_url, extract_domain, calculate_performance_score


def generate_technical_report(html: str, url: str = "") -> dict:
    """Generate a comprehensive technical report for a web page."""
    report = {
        "url": url,
        "timestamp": datetime.datetime.now().isoformat(),
        "basic_info": {},
        "structure_analysis": {},
        "content": {},
        "media": {},
        "links": {},
        "technology_stack": {},
        "styling": {},
        "seo_analysis": {},
        "accessibility": {},
        "performance_analysis": {},
        "security": {},
        "ui_components": {},
        "errors": [],
        "warnings": [],
        "recommendations": []
    }
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Basic Info Analysis
        report["basic_info"] = _analyze_basic_info(soup, report)
        
        # Structure Analysis  
        report["structure_analysis"] = _analyze_structure(soup, report)
        
        # Generate simple recommendations
        _generate_recommendations(report)
        
    except Exception as e:
        report["errors"].append(f"Technical report generation error: {str(e)}")
    
    return report


def _analyze_basic_info(soup, report):
    """Analyze basic page information"""
    basic_info = {
        "title": "",
        "description": "",
        "language": "en",
        "charset": "",
        "viewport": "",
        "favicon": ""
    }
    
    try:
        # Title
        if soup.title and soup.title.string:
            basic_info["title"] = soup.title.string.strip()
        
        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            basic_info["description"] = desc_tag['content']
        
        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            basic_info["language"] = html_tag.get('lang')
            
    except Exception as e:
        report["errors"].append(f"Basic info analysis error: {str(e)}")
    
    return basic_info


def _analyze_structure(soup, report):
    """Analyze HTML structure"""
    structure = {
        "total_elements": 0,
        "element_counts": {},
        "semantic_structure": {}
    }
    
    try:
        all_elements = soup.find_all()
        structure["total_elements"] = len(all_elements)
        
        # Element counts
        tags = [tag.name for tag in all_elements]
        tag_counts = Counter(tags)
        structure["element_counts"] = dict(tag_counts.most_common())
        
    except Exception as e:
        report["errors"].append(f"Structure analysis error: {str(e)}")
    
    return structure


def _analyze_content(soup, report):
    """Analyze content structure"""
    content = {
        "text_content_length": 0,
        "headings": {},
        "paragraphs": 0,
        "lists": {"ul": 0, "ol": 0},
        "tables": 0,
        "forms": []
    }
    
    try:
        # Text content
        text = soup.get_text()
        content["text_content_length"] = len(text)
        
        # Headings
        for i in range(1, 7):
            headings = soup.find_all(f'h{i}')
            if headings:
                content["headings"][f'h{i}'] = len(headings)
        
        # Paragraphs
        content["paragraphs"] = len(soup.find_all('p'))
        
        # Lists
        content["lists"]["ul"] = len(soup.find_all('ul'))
        content["lists"]["ol"] = len(soup.find_all('ol'))
        
        # Tables
        content["tables"] = len(soup.find_all('table'))
        
        # Forms
        forms = soup.find_all('form')
        for form in forms:
            form_info = {
                "action": form.get('action', ''),
                "method": form.get('method', 'get'),
                "inputs": len(form.find_all('input')),
                "textareas": len(form.find_all('textarea')),
                "selects": len(form.find_all('select'))
            }
            content["forms"].append(form_info)
        
    except Exception as e:
        report["errors"].append(f"Content analysis error: {str(e)}")
    
    return content


def _analyze_media(soup, url, report):
    """Analyze media elements"""
    media = {
        "images": [],
        "videos": [],
        "audio": [],
        "iframes": [],
        "canvas": 0,
        "svg": 0
    }
    
    try:
        base_url = url if url else ""
        
        # Images
        for img in soup.find_all('img'):
            img_info = {
                "src": img.get('src', ''),
                "alt": img.get('alt', ''),
                "width": img.get('width'),
                "height": img.get('height'),
                "loading": img.get('loading'),
                "has_alt": bool(img.get('alt'))
            }
            media["images"].append(img_info)
        
        # Videos
        for video in soup.find_all('video'):
            video_info = {
                "src": video.get('src') or (video.find('source') and video.find('source').get('src')),
                "controls": video.has_attr('controls'),
                "autoplay": video.has_attr('autoplay'),
                "loop": video.has_attr('loop')
            }
            media["videos"].append(video_info)
        
        # Audio
        for audio in soup.find_all('audio'):
            audio_info = {
                "src": audio.get('src') or (audio.find('source') and audio.find('source').get('src')),
                "controls": audio.has_attr('controls'),
                "autoplay": audio.has_attr('autoplay')
            }
            media["audio"].append(audio_info)
        
        # Iframes
        for iframe in soup.find_all('iframe'):
            iframe_info = {
                "src": iframe.get('src', ''),
                "width": iframe.get('width'),
                "height": iframe.get('height'),
                "loading": iframe.get('loading')
            }
            media["iframes"].append(iframe_info)
        
        # Canvas and SVG
        media["canvas"] = len(soup.find_all('canvas'))
        media["svg"] = len(soup.find_all('svg'))
        
    except Exception as e:
        report["errors"].append(f"Media analysis error: {str(e)}")
    
    return media


def _analyze_links(soup, url, base_domain, report):
    """Analyze link structure"""
    links = {
        "internal": [],
        "external": [],
        "mailto": [],
        "tel": [],
        "anchor": [],
        "total_count": 0
    }
    
    try:
        all_links = soup.find_all('a', href=True)
        links["total_count"] = len(all_links)
        
        for link in all_links:
            href = link['href'].strip()
            text = link.get_text().strip()
            
            link_info = {
                "href": href,
                "text": text,
                "title": link.get('title', ''),
                "target": link.get('target', '')
            }
            
            if href.startswith('mailto:'):
                links["mailto"].append(link_info)
            elif href.startswith('tel:'):
                links["tel"].append(link_info)
            elif href.startswith('#'):
                links["anchor"].append(link_info)
            elif is_external_url(href, base_domain):
                links["external"].append(link_info)
            else:
                links["internal"].append(link_info)
        
    except Exception as e:
        report["errors"].append(f"Links analysis error: {str(e)}")
    
    return links


def _analyze_technology_stack(soup, html, report):
    """Analyze technology stack"""
    tech_stack = {
        "libraries": [],
        "frameworks": [],
        "analytics": [],
        "cdn_resources": [],
        "css_frameworks": []
    }
    
    try:
        # JavaScript libraries detection
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            for lib_name, patterns in LIBRARIES_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, src, re.IGNORECASE):
                        version_match = re.search(r'(\d+(?:\.\d+)*)', src)
                        version = version_match.group(1) if version_match else "unknown"
                        
                        tech_stack["libraries"].append({
                            "name": lib_name,
                            "version": version,
                            "source": src,
                            "type": "script"
                        })
                        break
        
        # Analytics detection
        for analytics_name, patterns in ANALYTICS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    tech_stack["analytics"].append({
                        "name": analytics_name,
                        "source": "detected in HTML"
                    })
                    break
        
        # CSS frameworks
        css_links = soup.find_all('link', rel='stylesheet')
        for link in css_links:
            href = link.get('href', '')
            if 'bootstrap' in href.lower():
                tech_stack["css_frameworks"].append({
                    "name": "Bootstrap",
                    "source": href
                })
            elif 'tailwind' in href.lower():
                tech_stack["css_frameworks"].append({
                    "name": "Tailwind CSS",
                    "source": href
                })
        
    except Exception as e:
        report["errors"].append(f"Technology stack analysis error: {str(e)}")
    
    return tech_stack


def _analyze_styling(soup, html, report):
    """Analyze styling and design"""
    styling = {
        "css_files": [],
        "inline_styles": 0,
        "color_palette": [],
        "fonts": [],
        "css_frameworks": []
    }
    
    try:
        # CSS files
        css_links = soup.find_all('link', rel='stylesheet')
        for link in css_links:
            styling["css_files"].append({
                "href": link.get('href', ''),
                "media": link.get('media', 'all')
            })
        
        # Inline styles
        elements_with_style = soup.find_all(attrs={"style": True})
        styling["inline_styles"] = len(elements_with_style)
        
        # Color extraction (simplified)
        color_pattern = r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|rgb\([^)]+\)|rgba\([^)]+\)'
        colors = re.findall(color_pattern, html)
        color_counts = Counter(colors)
        
        styling["color_palette"] = [
            {"color": color, "count": count} 
            for color, count in color_counts.most_common(COLOR_PALETTE_SIZE)
        ]
        
        # Font detection (simplified)
        font_pattern = r'font-family:\s*([^;]+)'
        fonts = re.findall(font_pattern, html, re.IGNORECASE)
        styling["fonts"] = list(set(fonts))
        
    except Exception as e:
        report["errors"].append(f"Styling analysis error: {str(e)}")
    
    return styling


def _analyze_seo(soup, report):
    """Analyze SEO elements"""
    seo = {
        "meta_tags": {},
        "open_graph": {},
        "twitter_cards": {},
        "schema_markup": [],
        "alt_texts": {"missing": 0, "present": 0}
    }
    
    try:
        # Meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                seo["meta_tags"][name] = content
                
                # Open Graph
                if name.startswith('og:'):
                    seo["open_graph"][name] = content
                
                # Twitter Cards
                if name.startswith('twitter:'):
                    seo["twitter_cards"][name] = content
        
        # Alt text analysis
        images = soup.find_all('img')
        for img in images:
            if img.get('alt'):
                seo["alt_texts"]["present"] += 1
            else:
                seo["alt_texts"]["missing"] += 1
        
        # Schema markup
        scripts = soup.find_all('script', type='application/ld+json')
        seo["schema_markup"] = [script.get_text() for script in scripts]
        
    except Exception as e:
        report["errors"].append(f"SEO analysis error: {str(e)}")
    
    return seo


def _analyze_accessibility(soup, report):
    """Analyze accessibility features"""
    accessibility = {
        "aria_labels": 0,
        "aria_roles": [],
        "alt_attributes": 0,
        "form_labels": 0,
        "skip_links": 0,
        "lang_attributes": 0
    }
    
    try:
        # ARIA labels
        aria_labeled = soup.find_all(attrs={"aria-label": True})
        accessibility["aria_labels"] = len(aria_labeled)
        
        # ARIA roles
        role_elements = soup.find_all(attrs={"role": True})
        accessibility["aria_roles"] = [elem.get('role') for elem in role_elements]
        
        # Alt attributes
        img_with_alt = soup.find_all('img', alt=True)
        accessibility["alt_attributes"] = len(img_with_alt)
        
        # Form labels
        labels = soup.find_all('label')
        accessibility["form_labels"] = len(labels)
        
        # Skip links
        skip_links = soup.find_all('a', href=lambda x: x and x.startswith('#'))
        accessibility["skip_links"] = len([link for link in skip_links if 'skip' in link.get_text().lower()])
        
        # Language attributes
        lang_elements = soup.find_all(attrs={"lang": True})
        accessibility["lang_attributes"] = len(lang_elements)
        
    except Exception as e:
        report["errors"].append(f"Accessibility analysis error: {str(e)}")
    
    return accessibility


def _analyze_performance(soup, report):
    """Analyze performance-related elements"""
    performance = {
        "total_requests": 0,
        "lazy_loading": 0,
        "preload_hints": [],
        "critical_resources": [],
        "overall_score": 0
    }
    
    try:
        # Count external resources
        external_resources = []
        external_resources.extend(soup.find_all('script', src=True))
        external_resources.extend(soup.find_all('link', href=True))
        external_resources.extend(soup.find_all('img', src=True))
        
        performance["total_requests"] = len(external_resources)
        
        # Lazy loading detection
        lazy_imgs = soup.find_all('img', loading='lazy')
        performance["lazy_loading"] = len(lazy_imgs)
        
        # Preload hints
        preload_links = soup.find_all('link', rel='preload')
        performance["preload_hints"] = [link.get('href') for link in preload_links]
        
        # Calculate overall score
        performance["overall_score"] = calculate_performance_score(performance)
        
    except Exception as e:
        report["errors"].append(f"Performance analysis error: {str(e)}")
    
    return performance


def _analyze_security(soup, url, report):
    """Analyze security-related elements"""
    security = {
        "external_domains": [],
        "mixed_content": [],
        "security_headers": {}
    }
    
    try:
        # External domains
        external_links = soup.find_all(['script', 'link', 'img'], src=True) + soup.find_all('link', href=True)
        domains = set()
        
        for elem in external_links:
            src = elem.get('src') or elem.get('href')
            if src and src.startswith(('http://', 'https://')):
                domain = extract_domain(src)
                if domain:
                    domains.add(domain)
        
        security["external_domains"] = list(domains)
        
        # Mixed content detection (simplified)
        if url and url.startswith('https://'):
            http_resources = soup.find_all(['script', 'link', 'img'], src=lambda x: x and x.startswith('http://'))
            security["mixed_content"] = [elem.get('src') for elem in http_resources]
        
    except Exception as e:
        report["errors"].append(f"Security analysis error: {str(e)}")
    
    return security


def _analyze_ui_components(soup, report):
    """Analyze UI components"""
    ui_components = {
        "buttons": [],
        "forms": [],
        "navigation": [],
        "modals": 0,
        "carousels": 0
    }
    
    try:
        # Buttons
        buttons = soup.find_all(['button', 'input'])
        for btn in buttons:
            if btn.name == 'button' or (btn.name == 'input' and btn.get('type') in ['button', 'submit']):
                ui_components["buttons"].append({
                    "type": btn.get('type', 'button'),
                    "text": btn.get_text().strip() or btn.get('value', ''),
                    "classes": btn.get('class', [])
                })
        
        # Navigation
        nav_elements = soup.find_all('nav')
        for nav in nav_elements:
            links = nav.find_all('a')
            ui_components["navigation"].append({
                "links_count": len(links),
                "classes": nav.get('class', [])
            })
        
        # Modals (simplified detection)
        modal_indicators = soup.find_all(attrs={"class": lambda x: x and 'modal' in ' '.join(x).lower()})
        ui_components["modals"] = len(modal_indicators)
        
        # Carousels (simplified detection)
        carousel_indicators = soup.find_all(attrs={"class": lambda x: x and any(term in ' '.join(x).lower() for term in ['carousel', 'slider', 'swiper'])})
        ui_components["carousels"] = len(carousel_indicators)
        
    except Exception as e:
        report["errors"].append(f"UI components analysis error: {str(e)}")
    
    return ui_components


def _generate_recommendations(report):
    """Generate actionable recommendations"""
    recommendations = []
    
    if not report["basic_info"].get("title"):
        recommendations.append("Add a descriptive page title")
    
    if not report["basic_info"].get("description"):
        recommendations.append("Add a meta description")
    
    report["recommendations"] = recommendations 
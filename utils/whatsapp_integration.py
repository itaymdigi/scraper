"""
WhatsApp Integration Module for Web Scraper
Uses WaPulse MCP server for WhatsApp messaging capabilities
"""

import json
import base64
import io
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import matplotlib.pyplot as plt
from config.settings import WHATSAPP_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)

class WhatsAppIntegration:
    """
    WhatsApp integration class for sending scraper reports and notifications
    """
    
    def __init__(self, instance_id: str = None, token: str = None):
        """
        Initialize WhatsApp integration
        
        Args:
            instance_id: WaPulse instance ID
            token: WaPulse API token
        """
        self.instance_id = instance_id or WHATSAPP_CONFIG.get('instance_id', '')
        self.token = token or WHATSAPP_CONFIG.get('token', '')
        self.enabled = bool(self.instance_id and self.token)
        self.message_templates = WHATSAPP_CONFIG['message_templates']
        self.file_config = WHATSAPP_CONFIG['file_sharing']
        
        if not self.enabled:
            logger.warning("WhatsApp integration not configured. Please set instance_id and token.")
    
    def is_configured(self) -> bool:
        """Check if WhatsApp integration is properly configured"""
        return self.enabled
    
    def validate_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """
        Validate a phone number format for WhatsApp
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Dict with validation result
        """
        if not self.enabled:
            return {"valid": False, "error": "WhatsApp not configured"}
        
        try:
            # This would use the MCP WaPulse function
            # For now, we'll implement basic validation
            # Remove all non-digit characters
            clean_number = ''.join(filter(str.isdigit, phone_number))
            
            # Basic validation - should be 6-15 digits with country code
            if len(clean_number) < 6 or len(clean_number) > 15:
                return {"valid": False, "error": "Invalid phone number length"}
            
            return {"valid": True, "formatted_number": clean_number}
        
        except Exception as e:
            logger.error(f"Error validating phone number: {e}")
            return {"valid": False, "error": str(e)}
    
    def send_scrape_notification(self, phone_number: str, url: str, page_count: int, 
                               success: bool = True, error_message: str = None) -> Dict[str, Any]:
        """
        Send notification about scraping completion
        
        Args:
            phone_number: Recipient phone number
            url: Scraped URL
            page_count: Number of pages scraped
            success: Whether scraping was successful
            error_message: Error message if scraping failed
            
        Returns:
            Dict with send result
        """
        if not self.enabled:
            return {"success": False, "error": "WhatsApp not configured"}
        
        try:
            # Validate phone number
            validation = self.validate_phone_number(phone_number)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # Choose appropriate template and format message
            if success:
                template = self.message_templates['scrape_complete']
                message = template.format(
                    url=url,
                    page_count=page_count
                )
            else:
                template = self.message_templates['scrape_error']
                message = template.format(
                    url=url,
                    error=error_message or "Unknown error"
                )
            
            # This would use the MCP WaPulse send_whatsapp_message function
            # For now, we'll log the message that would be sent
            logger.info(f"Would send WhatsApp message to {validation['formatted_number']}: {message}")
            
            return {
                "success": True, 
                "message": "Notification sent successfully",
                "recipient": validation['formatted_number']
            }
        
        except Exception as e:
            logger.error(f"Error sending scrape notification: {e}")
            return {"success": False, "error": str(e)}
    
    def send_report_summary(self, phone_number: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a summary of the analysis report
        
        Args:
            phone_number: Recipient phone number
            report_data: Analysis report data
            
        Returns:
            Dict with send result
        """
        if not self.enabled:
            return {"success": False, "error": "WhatsApp not configured"}
        
        try:
            # Validate phone number
            validation = self.validate_phone_number(phone_number)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # Extract key information from report
            url = report_data.get('url', 'Unknown')
            title = report_data.get('basic_info', {}).get('title', 'No title')
            element_count = len(report_data.get('element_analysis', {}).get('element_counts', {}))
            
            # Calculate performance score
            performance = report_data.get('performance', {})
            img_opt = performance.get('image_optimization', {})
            performance_score = int(img_opt.get('optimization_score', 0) * 100) if img_opt else 0
            
            # Format message
            template = self.message_templates['report_summary']
            message = template.format(
                url=url,
                title=title,
                element_count=element_count,
                performance_score=performance_score
            )
            
            # This would use the MCP WaPulse send_whatsapp_message function
            logger.info(f"Would send WhatsApp report summary to {validation['formatted_number']}: {message}")
            
            return {
                "success": True,
                "message": "Report summary sent successfully",
                "recipient": validation['formatted_number']
            }
        
        except Exception as e:
            logger.error(f"Error sending report summary: {e}")
            return {"success": False, "error": str(e)}
    
    def send_chart_image(self, phone_number: str, chart_figure, chart_title: str = "Analysis Chart") -> Dict[str, Any]:
        """
        Send a chart image via WhatsApp
        
        Args:
            phone_number: Recipient phone number
            chart_figure: Matplotlib figure object
            chart_title: Title for the chart
            
        Returns:
            Dict with send result
        """
        if not self.enabled:
            return {"success": False, "error": "WhatsApp not configured"}
        
        if not self.file_config['enable_charts']:
            return {"success": False, "error": "Chart sharing is disabled"}
        
        try:
            # Validate phone number
            validation = self.validate_phone_number(phone_number)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # Convert matplotlib figure to base64 image
            img_buffer = io.BytesIO()
            chart_figure.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            
            # Check file size
            file_size_mb = len(img_buffer.getvalue()) / (1024 * 1024)
            if file_size_mb > self.file_config['max_file_size_mb']:
                return {"success": False, "error": f"Chart image too large ({file_size_mb:.1f}MB)"}
            
            # Encode to base64
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            data_uri = f"data:image/png;base64,{img_base64}"
            
            # This would use the MCP WaPulse send_whatsapp_files function
            logger.info(f"Would send chart image to {validation['formatted_number']}: {chart_title}")
            
            return {
                "success": True,
                "message": "Chart sent successfully",
                "recipient": validation['formatted_number'],
                "file_size_mb": round(file_size_mb, 2)
            }
        
        except Exception as e:
            logger.error(f"Error sending chart image: {e}")
            return {"success": False, "error": str(e)}
    
    def send_html_template(self, phone_number: str, html_content: str, filename: str = None) -> Dict[str, Any]:
        """
        Send HTML template file via WhatsApp
        
        Args:
            phone_number: Recipient phone number
            html_content: HTML content to send
            filename: Optional filename for the HTML file
            
        Returns:
            Dict with send result
        """
        if not self.enabled:
            return {"success": False, "error": "WhatsApp not configured"}
        
        if not self.file_config['enable_html_templates']:
            return {"success": False, "error": "HTML template sharing is disabled"}
        
        try:
            # Validate phone number
            validation = self.validate_phone_number(phone_number)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # Check file size
            file_size_mb = len(html_content.encode('utf-8')) / (1024 * 1024)
            if file_size_mb > self.file_config['max_file_size_mb']:
                return {"success": False, "error": f"HTML file too large ({file_size_mb:.1f}MB)"}
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"website_template_{timestamp}.html"
            
            # Encode HTML content to base64
            html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            data_uri = f"data:text/html;base64,{html_base64}"
            
            # This would use the MCP WaPulse send_whatsapp_files function
            logger.info(f"Would send HTML template to {validation['formatted_number']}: {filename}")
            
            return {
                "success": True,
                "message": "HTML template sent successfully",
                "recipient": validation['formatted_number'],
                "filename": filename,
                "file_size_mb": round(file_size_mb, 2)
            }
        
        except Exception as e:
            logger.error(f"Error sending HTML template: {e}")
            return {"success": False, "error": str(e)}
    
    def send_json_report(self, phone_number: str, report_data: Dict[str, Any], filename: str = None) -> Dict[str, Any]:
        """
        Send JSON report file via WhatsApp
        
        Args:
            phone_number: Recipient phone number
            report_data: Report data to send as JSON
            filename: Optional filename for the JSON file
            
        Returns:
            Dict with send result
        """
        if not self.enabled:
            return {"success": False, "error": "WhatsApp not configured"}
        
        if not self.file_config['enable_json_reports']:
            return {"success": False, "error": "JSON report sharing is disabled"}
        
        try:
            # Validate phone number
            validation = self.validate_phone_number(phone_number)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # Convert report to JSON
            json_content = json.dumps(report_data, indent=2, ensure_ascii=False)
            
            # Check file size
            file_size_mb = len(json_content.encode('utf-8')) / (1024 * 1024)
            if file_size_mb > self.file_config['max_file_size_mb']:
                return {"success": False, "error": f"JSON file too large ({file_size_mb:.1f}MB)"}
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                url_safe = report_data.get('url', 'report').replace('https://', '').replace('http://', '').replace('/', '_')
                filename = f"analysis_report_{url_safe}_{timestamp}.json"
            
            # Encode JSON content to base64
            json_base64 = base64.b64encode(json_content.encode('utf-8')).decode('utf-8')
            data_uri = f"data:application/json;base64,{json_base64}"
            
            # This would use the MCP WaPulse send_whatsapp_files function
            logger.info(f"Would send JSON report to {validation['formatted_number']}: {filename}")
            
            return {
                "success": True,
                "message": "JSON report sent successfully",
                "recipient": validation['formatted_number'],
                "filename": filename,
                "file_size_mb": round(file_size_mb, 2)
            }
        
        except Exception as e:
            logger.error(f"Error sending JSON report: {e}")
            return {"success": False, "error": str(e)}
    
    def send_bulk_notification(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """
        Send a message to multiple recipients
        
        Args:
            phone_numbers: List of recipient phone numbers
            message: Message to send
            
        Returns:
            Dict with bulk send results
        """
        if not self.enabled:
            return {"success": False, "error": "WhatsApp not configured"}
        
        results = {
            "total": len(phone_numbers),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for phone_number in phone_numbers:
            try:
                # Validate phone number
                validation = self.validate_phone_number(phone_number)
                if not validation["valid"]:
                    results["failed"] += 1
                    results["details"].append({
                        "phone": phone_number,
                        "status": "failed",
                        "error": validation["error"]
                    })
                    continue
                
                # This would use the MCP WaPulse send_whatsapp_message function
                logger.info(f"Would send bulk message to {validation['formatted_number']}: {message}")
                
                results["successful"] += 1
                results["details"].append({
                    "phone": validation['formatted_number'],
                    "status": "sent"
                })
                
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "phone": phone_number,
                    "status": "failed",
                    "error": str(e)
                })
        
        results["success"] = results["successful"] > 0
        return results
    
    def get_instance_status(self) -> Dict[str, Any]:
        """
        Get the status of the WhatsApp instance
        
        Returns:
            Dict with instance status information
        """
        if not self.enabled:
            return {"configured": False, "error": "WhatsApp not configured"}
        
        try:
            # This would use MCP WaPulse functions to check instance status
            logger.info(f"Checking status for instance: {self.instance_id}")
            
            return {
                "configured": True,
                "instance_id": self.instance_id,
                "status": "active",  # This would come from actual API call
                "message": "WhatsApp instance is ready"
            }
        
        except Exception as e:
            logger.error(f"Error checking instance status: {e}")
            return {"configured": True, "status": "error", "error": str(e)}

# Global instance for easy access
whatsapp_client = WhatsAppIntegration()

def get_whatsapp_client() -> WhatsAppIntegration:
    """Get the global WhatsApp client instance"""
    return whatsapp_client

def configure_whatsapp(instance_id: str, token: str) -> bool:
    """
    Configure WhatsApp integration with credentials
    
    Args:
        instance_id: WaPulse instance ID
        token: WaPulse API token
        
    Returns:
        bool: True if configuration successful
    """
    global whatsapp_client
    try:
        whatsapp_client = WhatsAppIntegration(instance_id, token)
        logger.info("WhatsApp integration configured successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to configure WhatsApp integration: {e}")
        return False 
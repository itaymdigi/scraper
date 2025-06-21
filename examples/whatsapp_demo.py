#!/usr/bin/env python3
"""
WhatsApp Integration Demo for Web Scraper
This script demonstrates how to use WaPulse MCP capabilities with the scraper
"""

import json
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.whatsapp_integration import WhatsAppIntegration, configure_whatsapp

def demo_whatsapp_integration():
    """
    Demo function showing WhatsApp integration capabilities
    """
    print("🚀 WhatsApp Integration Demo")
    print("=" * 50)
    
    # Example configuration (replace with your actual credentials)
    INSTANCE_ID = "your_wapulse_instance_id"
    TOKEN = "your_wapulse_token"
    
    print("1. Configuring WhatsApp Integration...")
    if configure_whatsapp(INSTANCE_ID, TOKEN):
        print("✅ WhatsApp configured successfully!")
    else:
        print("❌ Failed to configure WhatsApp")
        return
    
    # Get the client
    whatsapp = WhatsAppIntegration(INSTANCE_ID, TOKEN)
    
    # Example phone number (replace with actual number)
    phone_number = "1234567890"  # Include country code, no + or spaces
    
    print("\n2. Testing Phone Number Validation...")
    validation = whatsapp.validate_phone_number(phone_number)
    if validation["valid"]:
        print(f"✅ Phone number valid: {validation['formatted_number']}")
    else:
        print(f"❌ Invalid phone number: {validation['error']}")
        return
    
    print("\n3. Sending Scraping Notification...")
    result = whatsapp.send_scrape_notification(
        phone_number=phone_number,
        url="https://example.com",
        page_count=5,
        success=True
    )
    print(f"Result: {result}")
    
    print("\n4. Sending Report Summary...")
    # Example report data
    sample_report = {
        "url": "https://example.com",
        "basic_info": {
            "title": "Example Website"
        },
        "element_analysis": {
            "element_counts": {
                "div": 25,
                "p": 10,
                "a": 15
            }
        },
        "performance": {
            "image_optimization": {
                "optimization_score": 0.85
            }
        }
    }
    
    result = whatsapp.send_report_summary(
        phone_number=phone_number,
        report_data=sample_report
    )
    print(f"Result: {result}")
    
    print("\n5. Sending JSON Report...")
    result = whatsapp.send_json_report(
        phone_number=phone_number,
        report_data=sample_report
    )
    print(f"Result: {result}")
    
    print("\n6. Checking Instance Status...")
    status = whatsapp.get_instance_status()
    print(f"Status: {status}")
    
    print("\n🎉 Demo completed!")

def demo_with_actual_mcp():
    """
    Example of how to use actual MCP WaPulse functions
    This would be used when MCP server is available
    """
    print("\n🔗 Using Actual MCP WaPulse Functions")
    print("=" * 50)
    
    # These would be actual MCP function calls
    # when the MCP server is available in the environment
    
    print("""
    # Example MCP function usage:
    
    # 1. Send a WhatsApp message
    result = mcp_wapulse_whatsapp.send_whatsapp_message(
        to="1234567890",
        message="🕷️ Scraping Complete!\\n\\nURL: https://example.com\\nPages: 5\\nStatus: ✅ Success"
    )
    
    # 2. Send a file
    result = mcp_wapulse_whatsapp.send_whatsapp_files(
        to="1234567890",
        files=[{
            "file": "data:application/json;base64,eyJ0ZXN0IjogInZhbHVlIn0=",
            "filename": "report.json",
            "caption": "Website analysis report"
        }]
    )
    
    # 3. Validate phone number
    result = mcp_wapulse_whatsapp.validate_phone_number(
        phoneNumber="1234567890"
    )
    
    # 4. Check if ID exists
    result = mcp_wapulse_whatsapp.check_id_exists(
        value="1234567890",
        type="user"
    )
    
    # 5. Get all chats
    result = mcp_wapulse_whatsapp.get_all_chats()
    """)

def integration_guide():
    """
    Print integration guide for setting up WaPulse
    """
    print("\n📖 WaPulse Integration Guide")
    print("=" * 50)
    
    print("""
    To integrate WaPulse with your scraper:
    
    1. 🔑 Get WaPulse Credentials:
       - Sign up at WaPulse
       - Create a WhatsApp instance
       - Get your Instance ID and API Token
    
    2. ⚙️ Configure in Scraper:
       - Go to Settings page in the scraper
       - Enter your Instance ID and Token
       - Test the connection
    
    3. 📱 Set up WhatsApp:
       - Scan QR code to connect your WhatsApp
       - Ensure instance is active
    
    4. 🚀 Use Features:
       - Send scraping notifications
       - Share analysis reports
       - Send charts and files
       - Bulk notifications
    
    5. 🔧 MCP Integration:
       - Ensure MCP WaPulse server is running
       - Functions will use actual API calls
       - Currently using simulation mode
    
    📚 For more information:
    - WaPulse Documentation: https://wapulse.com/docs
    - MCP Documentation: https://github.com/modelcontextprotocol
    """)

if __name__ == "__main__":
    print("WhatsApp Integration Demo for Web Scraper")
    print("Note: This demo uses simulation mode. For actual WhatsApp sending,")
    print("configure real WaPulse credentials and MCP server.")
    print()
    
    choice = input("Choose demo: (1) Basic Integration (2) MCP Examples (3) Integration Guide: ")
    
    if choice == "1":
        demo_whatsapp_integration()
    elif choice == "2":
        demo_with_actual_mcp()
    elif choice == "3":
        integration_guide()
    else:
        print("Running all demos...")
        demo_whatsapp_integration()
        demo_with_actual_mcp()
        integration_guide() 
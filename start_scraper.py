#!/usr/bin/env python3
"""
Startup script for the Web Scraper with error handling and configuration
"""

import os
import sys
import subprocess
import time
import socket
from pathlib import Path

def check_port_available(port):
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    try:
        if os.name == 'nt':  # Windows
            subprocess.run([
                'netstat', '-ano', '|', 'findstr', f':{port}', '|', 
                'for', '/f', '"tokens=5"', '%a', 'in', "('more')", 
                'do', 'taskkill', '/F', '/PID', '%a'
            ], shell=True, capture_output=True)
        else:  # Unix/Linux/Mac
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(['kill', '-9', pid])
    except Exception as e:
        print(f"Warning: Could not kill process on port {port}: {e}")

def setup_environment():
    """Setup the environment for the scraper"""
    print("🔧 Setting up environment...")
    
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Create necessary directories
    directories = ['.streamlit', 'cache', 'logs', 'data']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Set environment variables for better Streamlit behavior
    os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
    os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'true'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'
    
    print("✅ Environment setup complete!")

def clear_streamlit_cache():
    """Clear Streamlit cache and temporary files"""
    print("🧹 Clearing Streamlit cache...")
    try:
        subprocess.run(['streamlit', 'cache', 'clear'], check=False, capture_output=True)
        
        # Also clear cache directories
        cache_dirs = ['.streamlit', '__pycache__', '.pytest_cache']
        for cache_dir in cache_dirs:
            cache_path = Path(cache_dir)
            if cache_path.exists():
                try:
                    import shutil
                    shutil.rmtree(cache_path)
                    cache_path.mkdir(exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not clear {cache_dir}: {e}")
        
        print("✅ Cache cleared!")
    except Exception as e:
        print(f"Warning: Could not clear cache: {e}")

def start_streamlit(port=8501, max_retries=3):
    """Start Streamlit with error handling and retries"""
    print(f"🚀 Starting Streamlit on port {port}...")
    
    for attempt in range(max_retries):
        try:
            # Check if port is available
            if not check_port_available(port):
                print(f"⚠️ Port {port} is busy, trying to free it...")
                kill_process_on_port(port)
                time.sleep(2)
                
                # Try next port if still busy
                if not check_port_available(port):
                    port += 1
                    print(f"🔄 Trying port {port}...")
                    continue
            
            # Start Streamlit
            cmd = [
                'streamlit', 'run', 'scraper.py',
                '--server.port', str(port),
                '--server.address', 'localhost',
                '--browser.serverAddress', 'localhost',
                '--server.enableCORS', 'false',
                '--browser.gatherUsageStats', 'false',
                '--global.developmentMode', 'false'
            ]
            
            print(f"📡 Starting server: {' '.join(cmd)}")
            print(f"🌐 Open your browser to: http://localhost:{port}")
            print("🛑 Press Ctrl+C to stop the server")
            print("-" * 50)
            
            # Start the process
            process = subprocess.run(cmd)
            return process.returncode
            
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            return 0
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in 3 seconds...")
                time.sleep(3)
                port += 1
            else:
                print("💥 All attempts failed!")
                return 1

def main():
    """Main startup function"""
    print("🕷️ Web Scraper Startup Script")
    print("=" * 50)
    
    # Setup environment
    setup_environment()
    
    # Clear cache
    clear_streamlit_cache()
    
    # Check Python environment
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Check if scraper.py exists
    if not Path('scraper.py').exists():
        print("❌ scraper.py not found! Make sure you're in the correct directory.")
        return 1
    
    # Start Streamlit
    return start_streamlit()

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Startup failed: {e}")
        sys.exit(1) 
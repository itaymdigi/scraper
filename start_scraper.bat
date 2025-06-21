@echo off
echo 🕷️ Web Scraper Pro - Startup Script
echo =====================================

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️ Virtual environment not found. Using system Python.
)

:: Clear any existing Streamlit processes
echo 🧹 Clearing existing processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq streamlit*" >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1

:: Clear Streamlit cache
echo 🗑️ Clearing Streamlit cache...
streamlit cache clear >nul 2>&1

:: Start the scraper
echo 🚀 Starting Web Scraper...
echo.
echo 🌐 The scraper will open in your default browser
echo 🛑 Press Ctrl+C to stop the server
echo.

:: Try to start with the startup script first, fallback to direct streamlit
python start_scraper.py
if errorlevel 1 (
    echo.
    echo ⚠️ Startup script failed, trying direct Streamlit...
    streamlit run scraper.py --server.port 8501 --server.address localhost --browser.serverAddress localhost --server.enableCORS false --browser.gatherUsageStats false
)

echo.
echo 👋 Scraper stopped. Press any key to exit...
pause >nul 
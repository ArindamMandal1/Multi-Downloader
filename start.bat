@echo off
TITLE HyperDownload - Next-Gen Multi-Part Downloader
color 0b
echo ========================================================
echo         Starting HyperDownload Local Web App...
echo ========================================================

:: Navigate directly to the Multi-Downloader project folder
cd /d "C:\Users\arind\Desktop\Multi-Downloader"

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start /B python app.py

echo [2/2] Opening Web Browser...
timeout /t 2 >nul
start http://localhost:8000

echo.
echo Server is running! Keep this window open while downloading.
echo Press any key to close this window (server will keep running in background).
pause >nul

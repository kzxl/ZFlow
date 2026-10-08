@echo off
title ZFlow - AI Chatbot Workflow Studio
echo ========================================================
echo   Starting ZFlow Studio (FastAPI Backend + React Web)
echo ========================================================

:: Change to root directory of script
cd /d "%~dp0"

:: Start Backend FastAPI server in background window
echo [1/2] Starting Backend Execution Engine on http://127.0.0.1:8000 ...
start "ZFlow Backend" cmd /k "cd server && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait 2 seconds for server startup
timeout /t 2 /nobreak >nul

:: Start Web Studio in background window
echo [2/2] Starting Web UI Studio on http://localhost:5173 ...
start "ZFlow Web Studio" cmd /k "cd web && npm run dev"

:: Open browser
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo ========================================================
echo   ZFlow is running!
echo   - Web Studio: http://localhost:5173
echo   - Backend API: http://127.0.0.1:8000/docs
echo ========================================================

@echo off
REM rowpic — server mode (Windows)
REM Headless: only the FastAPI backend, on 0.0.0.0:8765.
setlocal
cd /d "%~dp0\.."
cd backend
set ROWPIC_HOST=0.0.0.0
set ROWPIC_PORT=8765
python -m uvicorn app.main:app --host 0.0.0.0 --port 8765 --log-level info
endlocal

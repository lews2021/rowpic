@echo off
REM rowpic - web mode (Windows)
REM Starts backend + (Vite dev | built dist), opens browser.
REM If Node/npm is missing, falls back to serving the built dist or backend /ui.
setlocal
cd /d "%~dp0\.."
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found.  Install Python 3.12 from https://python.org
  exit /b 1
)
python scripts\start_web.py
endlocal
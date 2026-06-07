@echo off
REM rowpic — desktop mode (Windows)
REM Starts backend, opens native window via pywebview.
setlocal
cd /d "%~dp0\.."
where python >nul 2>nul || (echo Python not found & exit /b 1)
python -m pip install --quiet pywebview || echo (pywebview install optional)
python scripts\start_desktop.py
endlocal

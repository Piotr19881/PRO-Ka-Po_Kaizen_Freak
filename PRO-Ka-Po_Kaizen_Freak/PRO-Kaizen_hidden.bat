@echo off
rem PRO-Kaizen_hidden.bat — launch main.py with hidden console (prefer venv pythonw)
rem Place this file in the project root (same folder as main.py)

:: ensure we run from this script's folder
cd /d "%~dp0"
set "APP_DIR=%~dp0"
set "PYW=%APP_DIR%venv\Scripts\pythonw.exe"
set "PY=%APP_DIR%venv\Scripts\python.exe"

:: If project venv has pythonw, use it (runs without console)
if exist "%PYW%" (
    "%PYW%" "%APP_DIR%main.py"
    exit /b 0
)

:: If venv has python.exe, use PowerShell to start it hidden
if exist "%PY%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PY%' -ArgumentList '%APP_DIR%main.py' -WindowStyle Hidden"
    exit /b 0
)

:: Try system pythonw
where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
    pythonw "%APP_DIR%main.py"
    exit /b 0
)

:: Try system python via PowerShell hidden start
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'python' -ArgumentList '%APP_DIR%main.py' -WindowStyle Hidden"
    exit /b 0
)

echo ERROR: No Python executable found to run main.py
pause
exit /b 1

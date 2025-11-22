@echo off
rem PRO-Kaizen.bat — wrapper to start launcher.py using project venv or system Python
setlocal
set "APP_DIR=%~dp0"
set "PYW=%APP_DIR%venv\Scripts\pythonw.exe"
set "PY=%APP_DIR%venv\Scripts\python.exe"

rem If venv exists, prefer its pythonw/python. Otherwise try system Python (py -3).
if exist "%PYW%" (
    "%PYW%" "%APP_DIR%launcher.py"
) else if exist "%PY%" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PY%' -ArgumentList '%APP_DIR%launcher.py' -WindowStyle Hidden"
) else (
    rem No venv: try system Python launcher 'py -3' to bootstrap venv via launcher.py
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo Found system Python launcher 'py'. Running launcher to create venv and install requirements...
        py -3 "%APP_DIR%launcher.py"
        goto :EOF
    )
    echo ERROR: No Python interpreter found. Install Python or run launcher.py manually.
    echo You can install Python from https://www.python.org or run the project in development mode.
    pause
    exit /b 1
)

endlocal
exit /b 0

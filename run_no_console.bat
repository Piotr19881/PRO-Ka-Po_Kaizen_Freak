@echo off
rem run_no_console.bat — robust launcher: prefer pythonw in venv, fallback to python+VBS to hide console

setlocal
rem SCRIPT_DIR = directory where this script lives (with trailing \)
set "SCRIPT_DIR=%~dp0"
rem APP_DIR = script dir without trailing backslash
set "APP_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%APP_DIR%"

rem 1) Prefer pythonw from common venv locations
set "PYW=%APP_DIR%\venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%APP_DIR%\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%APP_DIR%\env\Scripts\pythonw.exe"

if exist "%PYW%" (
    "%PYW%" "%APP_DIR%\main.py"
    endlocal
    exit /b 0
)

rem 2) If pythonw not available, prefer python from venv and run it hidden via a temporary VBS
set "PY=%APP_DIR%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%APP_DIR%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%APP_DIR%\env\Scripts\python.exe"

if exist "%PY%" (
    set "VBSFILE=%TEMP%\run_py_hidden.vbs"
    >"%VBSFILE%" echo Set WshShell = CreateObject("WScript.Shell")
    >>"%VBSFILE%" echo WshShell.Run Chr(34) ^& "%PY%" ^& Chr(34) ^& " " ^& Chr(34) ^& "%APP_DIR%\main.py" ^& Chr(34), 0, False
    cscript //nologo "%VBSFILE%"
    del "%VBSFILE%" >nul 2>&1
    endlocal
    exit /b 0
)

rem 3) Try system pythonw
where pythonw >nul 2>nul
if %ERRORLEVEL%==0 (
    pythonw "%APP_DIR%\main.py"
    endlocal
    exit /b 0
)

rem 4) Try system python + VBS wrapper
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY=python"
    set "VBSFILE=%TEMP%\run_py_hidden.vbs"
    >"%VBSFILE%" echo Set WshShell = CreateObject("WScript.Shell")
    >>"%VBSFILE%" echo WshShell.Run Chr(34) ^& "%PY%" ^& Chr(34) ^& " " ^& Chr(34) ^& "%APP_DIR%\main.py" ^& Chr(34), 0, False
    cscript //nologo "%VBSFILE%"
    del "%VBSFILE%" >nul 2>&1
    endlocal
    exit /b 0
)

echo ERROR: No suitable Python interpreter found (pythonw or python). Create a virtualenv under "%APP_DIR%\venv" or install Python and add it to PATH.
pause
endlocal
exit /b 1

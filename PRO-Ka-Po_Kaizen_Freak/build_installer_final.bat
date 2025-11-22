@echo off
rem build_installer_final.bat — calls Inno Setup compiler at the provided path.
rem Edit ISCC path if needed.
set "ISCC=C:\Program Files (x86)\Inno Setup 6\Compil32.exe"
if not exist "%ISCC%" goto :NO_INNO

"%ISCC%" "%~dp0installer_c_drive.iss"
echo Build finished.
pause
goto :EOF

:NO_INNO
echo Cannot find %ISCC%
echo Please install Inno Setup or edit this file to the correct path.
pause
exit /b 1

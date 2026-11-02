@echo off
REM Start ORRIN Architect hidden every time you sign in to Windows (no admin rights needed).
cd /d "%~dp0"
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
> "%STARTUP%\ORRIN Architect.vbs" echo CreateObject("WScript.Shell").Run """%~dp0start.bat""", 0, False
echo Autostart installed: "%STARTUP%\ORRIN Architect.vbs"
echo Remove it any time with remove_autostart.bat
pause

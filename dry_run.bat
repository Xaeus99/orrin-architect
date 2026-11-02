@echo off
REM Print the plan for a prompt without touching Discord:  dry_run.bat a chill gaming clan
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run start.bat once first. & pause & exit /b 1)
".venv\Scripts\python.exe" -m architect.cli %*
pause

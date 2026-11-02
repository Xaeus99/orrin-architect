@echo off
REM ORRIN Architect - start the bot on Windows. First run sets everything up.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
if not exist ".venv\Scripts\python.exe" (
  echo Setting up Python environment...
  %PY% -m venv .venv || (echo Python 3.10+ is needed: https://www.python.org/downloads/ & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (pause & exit /b 1)
)
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo.
  echo Created .env - open it, paste your bot token after DISCORD_TOKEN=, save, then run start.bat again.
  notepad ".env"
  pause
  exit /b 0
)
:loop
".venv\Scripts\python.exe" -m architect.bot
echo Bot stopped. Restarting in 10 seconds (close this window to stop)...
timeout /t 10 /nobreak >nul
goto loop

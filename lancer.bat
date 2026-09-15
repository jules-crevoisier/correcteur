@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Lancez d'abord installer.bat
    pause
    exit /b 1
)
call .venv\Scripts\pythonw.exe -m papote

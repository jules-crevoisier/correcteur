@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Construction de l'executable autonome...
if not exist ".venv\Scripts\python.exe" ( echo Lancez d'abord installer.bat & pause & exit /b 1 )
call .venv\Scripts\python.exe -m pip install pyinstaller --quiet
call .venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm --clean --onefile --windowed ^
    --name Correcteur ^
    --collect-all language_tool_python ^
    --collect-all pystray ^
    --hidden-import PIL._tkinter_finder ^
    lancement.py
echo.
echo Executable genere dans dist\Correcteur.exe
echo ^(Java reste necessaire sur la machine cible.^)
pause

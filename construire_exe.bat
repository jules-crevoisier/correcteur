@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ================================================
echo   Construction de Correcteur.exe
echo ================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [X] Lancez d'abord installer.bat
    pause
    exit /b 1
)

echo [1/3] Installation de PyInstaller...
call .venv\Scripts\python.exe -m pip install pyinstaller --quiet
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo [2/3] Compilation...
call .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean correcteur.spec
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo [3/3] Assemblage de la distribution portable...
call .venv\Scripts\python.exe outils\assembler.py
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo.
echo ================================================
echo   Termine : dist\Correcteur\
echo.
echo   Ce dossier est autonome — ni Python ni Java
echo   ne sont requis sur la machine de destination.
echo   Deplacez-le ou vous voulez, puis lancez
echo   Correcteur.exe et activez le demarrage
echo   automatique depuis l'icone.
echo ================================================
pause

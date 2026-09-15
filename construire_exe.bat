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

echo [1/2] Installation de PyInstaller...
call .venv\Scripts\python.exe -m pip install pyinstaller --quiet
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo [2/2] Compilation...
call .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean correcteur.spec
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo.
echo ================================================
echo   Termine : dist\Correcteur.exe
echo.
echo   Un seul fichier, dictionnaire compris. Ni Python
echo   ni quoi que ce soit d'autre n'est requis sur la
echo   machine de destination. Copiez-le ou vous voulez,
echo   double-cliquez, puis activez le demarrage
echo   automatique depuis l'icone.
echo ================================================
pause

@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ================================================
echo   Installation du Correcteur
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [X] Python est introuvable.
    echo     Installez-le depuis https://www.python.org/downloads/
    echo     en cochant "Add Python to PATH", puis relancez ce fichier.
    pause
    exit /b 1
)

where java >nul 2>&1
if errorlevel 1 (
    echo [X] Java est introuvable.
    echo     Le moteur de correction en a besoin pour fonctionner hors ligne.
    echo     Installez-le depuis https://adoptium.net/ ^(bouton "Latest LTS"^),
    echo     puis relancez ce fichier.
    pause
    exit /b 1
)

echo [1/3] Creation de l'environnement Python...
if not exist ".venv" python -m venv .venv
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo [2/3] Installation des dependances...
call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo [3/3] Telechargement du dictionnaire francais ^(~250 Mo, une seule fois^)...
call .venv\Scripts\python.exe -m correcteur --texte "sa va bien" >nul
if errorlevel 1 ( echo [X] Echec. & pause & exit /b 1 )

echo.
echo ================================================
echo   Installation terminee.
echo.
echo   Lancez "Correcteur.vbs" pour demarrer.
echo   Raccourci par defaut : Ctrl+Alt+C
echo ================================================
pause

@echo off
echo ================================================
echo   Construction de Amah Agent (format dossier)
echo ================================================
echo.

:: Installe PyInstaller si absent
py -3.13 -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installation de PyInstaller...
    py -3.13 -m pip install pyinstaller
    echo.
)

:: Version (source unique : tools\updater.py)
for /f "delims=" %%v in ('py -3.13 -c "from tools.updater import CURRENT_VERSION; print(CURRENT_VERSION)"') do set VERSION=%%v

:: Nettoyage avant build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: Compilation
echo Compilation de la v%VERSION% en cours (plusieurs minutes)...
py -3.13 -m PyInstaller amah.spec --clean --noconfirm

echo.
if exist "dist\Amah Agent\Amah Agent.exe" (
    :: Fichiers clients dans le dossier livre
    copy /y "installer_navigateur.bat" "dist\Amah Agent\installer_navigateur.bat" >nul
    copy /y "GUIDE_INSTALLATION.md"    "dist\Amah Agent\GUIDE_INSTALLATION.md"    >nul

    :: Zip a envoyer au client
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\Amah Agent' -DestinationPath 'dist\Amah-Agent-v%VERSION%.zip' -Force"

    echo ================================================
    echo   Succes ! A livrer : dist\Amah-Agent-v%VERSION%.zip
    echo.
    echo   dist\Amah Agent\
    echo   ^|-- Amah Agent.exe          ^(a lancer^)
    echo   ^|-- _internal\              ^(ne pas toucher^)
    echo   ^|-- installer_navigateur.bat
    echo   ^|-- GUIDE_INSTALLATION.md
    echo.
    echo   IMPORTANT : ajoute le fichier .env du client dans
    echo   le dossier "Amah Agent" avant de zipper/livrer,
    echo   ou laisse le client le creer au premier lancement.
    echo ================================================
) else (
    echo   ERREUR : le .exe n'a pas ete cree.
    echo   Verifie les messages d'erreur ci-dessus.
)

echo.
if not "%~1"=="--no-pause" pause

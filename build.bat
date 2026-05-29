@echo off
echo ================================================
echo   Construction de Amah Agent.exe
echo ================================================
echo.

:: Installe PyInstaller si absent
py -3.13 -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installation de PyInstaller...
    py -3.13 -m pip install pyinstaller
    echo.
)

:: Nettoyage avant build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: Compilation
echo Compilation en cours...
py -3.13 -m PyInstaller amah.spec --clean

echo.
if exist "dist\Amah Agent.exe" (
    :: Copie les fichiers necessaires dans dist/
    copy /y "installer_navigateur.bat" "dist\installer_navigateur.bat" >nul
    copy /y "GUIDE_INSTALLATION.md"    "dist\GUIDE_INSTALLATION.md"    >nul

    echo ================================================
    echo   Succes ! Dossier dist\ pret a distribuer :
    echo.
    echo   dist\
    echo   |-- Amah Agent.exe
    echo   |-- installer_navigateur.bat
    echo   |-- GUIDE_INSTALLATION.md
    echo.
    echo   IMPORTANT : Ajoute le fichier .env dans dist\
    echo   avant de livrer au client.
    echo ================================================
) else (
    echo   ERREUR : le .exe n'a pas ete cree.
    echo   Verifie les messages d'erreur ci-dessus.
)

echo.
pause

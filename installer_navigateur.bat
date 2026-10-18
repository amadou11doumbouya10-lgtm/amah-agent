@echo off
setlocal
echo ================================================
echo   Amah Agent - Installation du navigateur
echo ================================================
echo.
echo Cette operation est necessaire une seule fois.
echo Elle va telecharger le navigateur d'Amah (~170 Mo).
echo.

:: 1. Moteur Playwright embarque dans Amah (aucun Python necessaire)
set "DRIVER=%~dp0_internal\playwright\driver"
if exist "%DRIVER%\node.exe" (
    "%DRIVER%\node.exe" "%DRIVER%\package\cli.js" install chromium
    if not errorlevel 1 goto :done
    echo.
    echo Le moteur embarque a echoue, essai avec Python...
    echo.
)

:: 2. Repli : Python installe sur ce PC
where py >nul 2>&1
if %errorlevel% == 0 (
    py -m playwright install chromium
    goto :done
)

where python >nul 2>&1
if %errorlevel% == 0 (
    python -m playwright install chromium
    goto :done
)

echo ERREUR : installation impossible.
echo Verifiez que ce fichier est bien dans le dossier "Amah Agent"
echo (a cote de Amah Agent.exe et du dossier _internal).
echo Support : contact.amah.officiel@gmail.com
goto :end

:done
echo.
echo ================================================
echo   Navigateur installe ! Vous pouvez lancer
echo   "Amah Agent.exe"
echo ================================================

:end
echo.
pause

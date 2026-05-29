@echo off
echo ================================================
echo   Amah Agent - Installation du navigateur
echo ================================================
echo.
echo Cette operation est necessaire une seule fois.
echo Elle va telecharger Chrome pour Amah (~170 Mo).
echo.

:: Cherche Python dans l'ordre
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

where python3 >nul 2>&1
if %errorlevel% == 0 (
    python3 -m playwright install chromium
    goto :done
)

echo ERREUR : Python n'est pas installe sur ce PC.
echo Contactez le support : contact.amah.officiel@gmail.com
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

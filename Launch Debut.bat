@echo off
REM Debut: local development launcher (SQLite + demo billing). For production see DEPLOY.md
setlocal
cd /d "%~dp0"
echo ============================================
echo  Debut - local launcher
echo ============================================
echo.

set PYEXE=
where python >nul 2>nul
if %errorlevel%==0 (
    python --version >nul 2>nul
    if %errorlevel%==0 set PYEXE=python
)
if "%PYEXE%"=="" (
    where py >nul 2>nul
    if %errorlevel%==0 set PYEXE=py
)
if "%PYEXE%"=="" (
    echo ERROR: Python was not found on this computer.
    echo.
    echo Install Python 3.10 or newer from https://python.org/downloads
    echo IMPORTANT: on the first install screen, tick the box that says
    echo "Add python.exe to PATH" before clicking Install.
    echo Then close this window and double-click Launch Debut.bat again.
    pause
    exit /b 1
)
echo Found Python: %PYEXE%
%PYEXE% --version

if not exist "venv\Scripts\python.exe" (
    echo.
    echo First run: creating a virtual environment...
    %PYEXE% -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo.
        echo ERROR: Could not create the virtual environment.
        echo This usually means Python is installed but broken, or you have
        echo no write permission in this folder. Try moving this folder out
        echo of Program Files / Downloads-protected areas and try again.
        pause
        exit /b 1
    )

    echo.
    echo Installing required packages (this can take a minute)...
    venv\Scripts\python.exe -m pip install --upgrade pip >nul
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ============================================
        echo  ERROR: Package installation failed.
        echo ============================================
        echo The exact error is printed above this message - scroll up to read it.
        echo Common fixes:
        echo   - Make sure you have an internet connection.
        echo   - Try running this same command yourself in this folder to see more detail:
        echo       venv\Scripts\python.exe -m pip install -r requirements.txt
        echo   - If it mentions "Microsoft Visual C++" or "Build Tools", your Python
        echo     version may be too new for a package; try Python 3.11 or 3.12 instead.
        echo Please copy the red/error text above and send it back for help.
        pause
        exit /b 1
    )
    echo Packages installed successfully.
)

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Starting Debut on http://127.0.0.1:8001
echo (Opening your browser in a few seconds. If it doesn't open, go to that
echo  address yourself.)
echo.
echo Leave THIS window open while you use the app. Close it to stop Debut.
echo If this window closes by itself right after this point, an error
echo happened - it will be printed just above; please copy it and send it back.
echo.
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8001"
venv\Scripts\python.exe app.py
echo.
echo Debut has stopped. If that was unexpected, scroll up to read why.
pause

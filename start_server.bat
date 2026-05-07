@echo off
REM Nevada County Experience — Local Server launcher
REM Double-click this file to start the server.

cd /d "%~dp0"

echo.
echo ============================================================
echo   Nevada County Experience -- Starting Server
echo   The server will run in this window.
echo   Open http://localhost:5000 in your browser.
echo   Press Ctrl+C (or close this window) to stop.
echo ============================================================
echo.

REM Find Python — try several common locations and pick the first one that works
set "PYTHON_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
if not defined PYTHON_EXE if exist "C:\Windows\py.exe" set "PYTHON_EXE=C:\Windows\py.exe"

REM Last-resort: try whatever's on PATH
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
    where py >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py"
)

if not defined PYTHON_EXE (
    echo ERROR: Could not find Python on this system.
    echo Looked in:
    echo   %LOCALAPPDATA%\Programs\Python\Python3xx\python.exe
    echo   %LOCALAPPDATA%\Programs\Python\Launcher\py.exe
    echo   C:\Windows\py.exe
    echo   PATH (python, py^)
    echo.
    echo Install Python from https://www.python.org/downloads/ — make sure
    echo to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
echo.

"%PYTHON_EXE%" server.py

REM If the server exits, keep the window open so you can read errors
echo.
echo Server has stopped.
pause

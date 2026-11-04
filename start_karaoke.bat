@echo off
setlocal
set "PROJECT_DIR=%~dp0"

if exist "%PROJECT_DIR%venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_DIR%venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" "%PROJECT_DIR%app.py"
exit /b %ERRORLEVEL%

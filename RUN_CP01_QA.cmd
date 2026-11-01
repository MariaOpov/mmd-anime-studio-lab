@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -V >nul 2>nul
    if not errorlevel 1 (
        py -3.12 launcher.py qa
        exit /b !errorlevel!
    )
)
python launcher.py qa
exit /b %errorlevel%

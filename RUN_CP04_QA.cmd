@echo off
setlocal
cd /d "%~dp0"
py -3.12 -B -m cp04.runner qa
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%

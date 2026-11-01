@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%CD%;%PYTHONPATH%"
py -3.12 -B -m cp09.cli status && py -3.12 -B -m cp09.cli readiness && py -3.12 -B -m cp09.cli plan both && py -3.12 -B -m cp09.cli run both
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%

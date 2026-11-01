@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%;%CD%\src;%PYTHONPATH%"
py -3.12 -B -m cp06.runner demo
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%

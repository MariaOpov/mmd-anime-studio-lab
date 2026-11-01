@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%CD%;%PYTHONPATH%"
py -3.12 -B -m unittest discover -s cp09/tests -v
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%

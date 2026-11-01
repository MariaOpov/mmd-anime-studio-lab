@echo off
setlocal
cd /d "%~dp0"
py -3.12 -B "%~dp0cp03\runner.py" qa
set "RET=%ERRORLEVEL%"
echo EXIT_CODE=%RET%
exit /b %RET%

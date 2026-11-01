@echo off
setlocal EnableExtensions
set "ROOT=D:\MMD\mmd-anime-studio-lab"
cd /d "%ROOT%" || exit /b 4
set "PYTHONPATH=%ROOT%;%ROOT%\src;%PYTHONPATH%"
py -3.12 -B -m cp10.cli audit
exit /b %ERRORLEVEL%

@echo off
setlocal
pushd "%~dp0" || exit /b 4
py -3.12 -V >nul 2>nul
if not errorlevel 1 (
  py -3.12 -B cp02\runner.py gui
) else (
  python -B cp02\runner.py gui
)
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%

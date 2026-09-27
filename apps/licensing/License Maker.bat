@echo off
title Termvera License Maker
rem Double-click to create a customer license key. Needs the signing key in
rem %USERPROFILE%\.termvera and this repository's Python environment.
"%~dp0..\api\.venv\Scripts\python.exe" "%~dp0termvera_license.py" wizard
echo.
pause

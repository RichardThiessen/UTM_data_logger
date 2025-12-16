@echo off
cd /d "%~dp0"
start "" "%~dp0python32\pythonw.exe" "%~dp0app\main.py" %*

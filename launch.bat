@echo off
title 6-Haneli Kod Simulatoru
cd /d "%~dp0"

REM Sanal ortam Python ile masaustu uygulamasini baslat
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" desktop_app.py
) else (
    python desktop_app.py
)

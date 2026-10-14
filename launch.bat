@echo off
title 6-Haneli Kod Simulatoru
cd /d "%~dp0"

echo ======================================================================
echo 6 HANELI KOD ISTATISTIKSEL ANOMALI VE PERIYOT SIMULATORU
echo ======================================================================
echo [*] Masaustu uygulamasi baslatiliyor, lutfen bekleyiniz...

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" desktop_app.py
) else (
    python desktop_app.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Uygulama calisirken bir hata olustu. Hata kodunu yukaridan inceleyebilirsiniz.
    pause
)

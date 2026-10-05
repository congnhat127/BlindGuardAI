@echo off
title BlindGuard AI - System Configurator
echo ====================================================================
echo        KHOI DONG TRINH CAU HINH XE VA 4 CAMERA (CONFIG WIZARD)
echo ====================================================================

cd /d "%~dp0"

if exist "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" (
    echo [OK] Tim thay moi truong Python: ..\1_AI_Processing_Edge\.venv
    "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" system_configurator\run_configurator_gui.py
) else if exist "..\.venv\Scripts\python.exe" (
    echo [OK] Tim thay moi truong Python: ..\.venv
    "..\.venv\Scripts\python.exe" system_configurator\run_configurator_gui.py
) else (
    echo [*] Su dung Python mac dinh cua he thong
    python system_configurator\run_configurator_gui.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Da xay ra loi (Ma loi: %ERRORLEVEL%).
    pause
)

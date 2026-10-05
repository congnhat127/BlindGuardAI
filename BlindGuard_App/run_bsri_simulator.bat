@echo off
title BlindGuard AI - BSRI ^& DHZ Interactive Simulator
echo ====================================================================
echo    KHOI DONG TRINH MO PHONG TRUC QUAN BSRI ^& DHZ (ADAS TESTBENCH)
echo ====================================================================

cd /d "%~dp0"

if exist "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" (
    echo [OK] Tim thay moi truong Python: ..\1_AI_Processing_Edge\.venv
    "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" run_bsri_simulator_gui.py
) else if exist "..\.venv\Scripts\python.exe" (
    echo [OK] Tim thay moi truong Python: ..\.venv
    "..\.venv\Scripts\python.exe" run_bsri_simulator_gui.py
) else (
    echo [*] Su dung Python mac dinh cua he thong
    python run_bsri_simulator_gui.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Da xay ra loi (Ma loi: %ERRORLEVEL%).
    pause
)

@echo off
title BlindGuard AI - Interactive Demo
echo ====================================================================
echo        KHOI DONG TRINH TRINH DIEN BLINDGUARD AI DEMO
echo ====================================================================

cd /d "%~dp0"

if exist "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" (
    echo [OK] Tim thay moi truong Python: ..\1_AI_Processing_Edge\.venv
    "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" run_demo.py
) else if exist "..\.venv\Scripts\python.exe" (
    echo [OK] Tim thay moi truong Python: ..\.venv
    "..\.venv\Scripts\python.exe" run_demo.py
) else (
    echo [*] Su dung Python mac dinh cua he thong
    python run_demo.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Da xay ra loi (Ma loi: %ERRORLEVEL%).
    pause
)

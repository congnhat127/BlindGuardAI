@echo off
title BlindGuard AI - Real Camera & Video Demo
echo ====================================================================
echo    KHOI DONG TRINH KIEM THU CAMERA THUC TE & VIDEO - BLINDGUARD AI
echo ====================================================================
echo.
echo [*] Tip: Ban co the chay truc tiep Camera 0 bang lenh:
echo     run_demo.bat --cam 0
echo.

cd /d "%~dp0"

if exist "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" (
    echo [OK] Su dung moi truong Python: ..\1_AI_Processing_Edge\.venv
    "..\1_AI_Processing_Edge\.venv\Scripts\python.exe" run_demo.py %*
) else if exist "..\.venv\Scripts\python.exe" (
    echo [OK] Su dung moi truong Python: ..\.venv
    "..\.venv\Scripts\python.exe" run_demo.py %*
) else (
    echo [*] Su dung Python mac dinh cua he thong
    python run_demo.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Da xay ra loi (Ma loi: %ERRORLEVEL%).
    pause
)

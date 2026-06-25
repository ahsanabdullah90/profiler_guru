@echo off
title Profile_Guru Launcher
echo =========================================
echo Starting Profile_Guru Application...
echo =========================================
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo An error occurred while starting the application.
    pause
)

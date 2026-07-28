@echo off
chcp 65001 >nul
title OmniVoice Thai
echo ============================================
echo   OmniVoice Thai - Voice Cloning WebApp
echo ============================================
echo.

cd /d E:\AI\Omnivoice
call .\venv\Scripts\activate.bat

echo Starting OmniVoice Thai...
echo.
python App.py

pause

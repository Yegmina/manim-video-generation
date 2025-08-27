@echo off
echo Starting Manim Video Generation FastAPI Backend...
echo.

REM Check if .env file exists
if not exist ".env" (
    echo Creating .env file from template...
    copy env.example .env
    echo.
    echo Please edit .env file with your configuration before running again.
    echo.
    pause
    exit /b 1
)

REM Install dependencies if needed
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting the server...
python run.py

pause

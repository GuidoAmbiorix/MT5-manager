@echo off
title MT5 Manager Launcher
color 0A

echo ============================================
echo        MT5 Manager - Quick Start
echo ============================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

:: Create network if it doesn't exist
echo [1/4] Checking network...
docker network inspect trading_network >nul 2>&1
if %errorlevel% neq 0 (
    echo       Creating trading_network...
    docker network create trading_network
) else (
    echo       Network already exists.
)

:: Build the manager image
echo [2/4] Building MT5 Manager...
docker compose build mt5_manager

:: Start the services
echo [3/4] Starting services...
docker compose up -d

:: Wait a moment for services to start
echo [4/4] Waiting for services to start...
timeout /t 3 /nobreak >nul

:: Show status
echo.
echo ============================================
echo          Services Started!
echo ============================================
echo.
echo   MT5 Manager:  http://localhost:8080
echo   MT5 VNC:      http://localhost:3000
echo.
echo   Default VNC Password: trading
echo.
echo ============================================

:: Open browser
start http://localhost:8080

pause

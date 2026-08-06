@echo off
chcp 936 >nul

:: On first launch, re-run this batch in a minimized window
if /I not "%~1"=="minimized" (
    start /min "" "%~f0" minimized %*
    exit /b 0
)

title Y2 Bridge v2.6.0
setlocal enabledelayedexpansion

set PYTHON=C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe
set PYTHONPATH=E:/python_packages
set SCRIPT_DIR=C:\Users\Administrator\ZCodeProject
set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
set PORT=8765
set HOST=127.0.0.1
set OPEN_BROWSER=1
set EXTRA_ARGS=

:: Parse command line args (skip the "minimized" sentinel)
:parse_args
if "%~1"=="" goto :done_parse
if /I "%~1"=="minimized" (
    shift
    goto :parse_args
)
if /I "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--host" (
    set "HOST=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--no-browser" (
    set OPEN_BROWSER=0
    shift
    goto :parse_args
)
set "EXTRA_ARGS=!EXTRA_ARGS! %1"
shift
goto :parse_args
:done_parse

if not exist "%PYTHON%" (
    echo [ERROR] Python not found: %PYTHON%
    pause
    exit /b 1
)

cd /d "%SCRIPT_DIR%"

:: Kill any stale check_rem (port 8766) so its guardian re-launches it with fresh code
echo [startup] Checking for stale check_rem on port 8766...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8766" ^| findstr "LISTENING"') do (
    if not "%%a"=="0" (
        echo [startup] Killing stale check_rem PID %%a
        taskkill /PID %%a /F >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

:: Check if Bridge is already running —— 若端口被旧进程占用，先强行杀掉再启动（确保加载最新代码）
curl -s http://%HOST%:%PORT%/api/inbox >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] 检测到 %HOST%:%PORT% 已有进程，先杀掉旧进程以确保加载最新代码...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
        if not "%%a"=="0" (
            echo [INFO] Killing stale bridge PID %%a
            taskkill /PID %%a /F >nul 2>&1
        )
    )
    timeout /t 1 /nobreak >nul
)

:: Rotate old log before starting
call :rotate_log

echo ========================================
echo   Y2 Bridge v2.6.0
echo   Panel: http://%HOST%:%PORT%
echo   INBOX: D:\Semems WB\01_INBOX\
echo   Lovart: E:\Claude code\lovart-official\
echo ========================================
echo.
echo Starting Bridge service...

:: Start Bridge in background, redirect output to log
start "" /B "%PYTHON%" lovart_bridge.py --port %PORT% --host %HOST% %EXTRA_ARGS% > bridge.log 2>&1
set BRIDGE_STARTED=1

echo Waiting for service...
timeout /t 3 /nobreak >nul

curl -s http://%HOST%:%PORT%/api/inbox >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Bridge is running!
) else (
    echo [RETRY] Waiting a bit more...
    timeout /t 3 /nobreak >nul
    curl -s http://%HOST%:%PORT%/api/inbox >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Bridge is running!
    ) else (
        echo [WARN] Service not responding, check bridge.log
    )
)

if "%OPEN_BROWSER%"=="1" (
    echo.
    echo Opening Chrome...
    if exist "%CHROME%" (
        start "" cmd /c ""%CHROME%" --new-window --window-size=1400,900 "http://%HOST%:%PORT%" >nul 2>&1"
    ) else (
        start "" cmd /c "start http://%HOST%:%PORT% >nul 2>&1"
    )
)

echo.
echo ========================================
echo  Panel: http://%HOST%:%PORT%
echo  Close this window to stop service
echo  Log: bridge.log
echo ========================================
echo.
pause

:: Stop Bridge when the window is closed
call :stop_bridge
exit /b 0

:: Subroutine: rotate bridge.log to timestamped backup
:rotate_log
if not exist bridge.log exit /b 0
for /f "usebackq tokens=*" %%a in (`powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set "TS=%%a"
copy bridge.log "bridge.log.!TS!.bak" >nul 2>&1
exit /b 0

:: Subroutine: stop Bridge by PID or port
:stop_bridge
if exist bridge.pid (
    set /p BRIDGE_PID=<bridge.pid
    if not "!BRIDGE_PID!"=="" (
        echo Stopping Bridge PID !BRIDGE_PID! ...
        taskkill /PID !BRIDGE_PID! /F >nul 2>&1
    )
    del bridge.pid >nul 2>&1
) else (
    :: Fallback: stop by port
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%"') do (
        if not "%%a"=="0" (
            taskkill /PID %%a /F >nul 2>&1
        )
    )
)
exit /b 0

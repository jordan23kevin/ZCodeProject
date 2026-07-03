@echo off
chcp 936 >nul

:: On first launch, re-run this batch in a minimized window
if /I not "%~1"=="minimized" (
    start /min "" "%~f0" minimized %*
    exit /b 0
)

title Y2 Bridge v2.3.6
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

:: Check if Bridge is already running
curl -s http://%HOST%:%PORT%/api/inbox >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [WARN] Bridge already running at http://%HOST%:%PORT%
    if "%OPEN_BROWSER%"=="1" (
        echo Opening Chrome...
        if exist "%CHROME%" (
            start "" cmd /c ""%CHROME%" --new-window "http://%HOST%:%PORT%" >nul 2>&1"
        ) else (
            start "" cmd /c "start http://%HOST%:%PORT% >nul 2>&1"
        )
    )
    pause
    exit /b 0
)

:: Rotate old log before starting
call :rotate_log

echo ========================================
echo   Y2 Bridge v2.3.6
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
        start "" cmd /c ""%CHROME%" --new-window "http://%HOST%:%PORT%" >nul 2>&1"
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

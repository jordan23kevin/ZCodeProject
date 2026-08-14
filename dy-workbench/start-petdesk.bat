@echo off
setlocal
set "DIR=E:\Kimi Code\dy-workbench"
set "URL=http://127.0.0.1:7100/"

REM --- if server already running, just open the page ---
curl -s -m 2 %URL% 2>nul | findstr /C:"PETDESK" >nul
if %errorlevel%==0 (
  start "" %URL%
  exit /b 0
)

REM --- locate node ---
set "NODE="
where node >nul 2>nul && set "NODE=node"
if not defined NODE if exist "C:\Users\Administrator\AppData\Local\Programs\kimi-desktop\resources\resources\runtime\node.exe" set "NODE=C:\Users\Administrator\AppData\Local\Programs\kimi-desktop\resources\resources\runtime\node.exe"
if not defined NODE if exist "C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\node.exe" set "NODE=C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\node.exe"
if not defined NODE (
  echo [PETDESK] Node.js not found. Please install Node.js first.
  pause
  exit /b 1
)

REM --- start server minimized, wait, then open browser ---
start "PETDESK Server" /min "%NODE%" "%DIR%\server.js" --port 7100
set /a tries=0
:wait
curl -s -m 2 %URL% 2>nul | findstr /C:"PETDESK" >nul
if %errorlevel%==0 goto open
set /a tries+=1
if %tries% geq 15 goto fail
ping -n 2 127.0.0.1 >nul
goto wait
:open
start "" %URL%
exit /b 0
:fail
echo [PETDESK] Server failed to start on port 7100.
pause
exit /b 1

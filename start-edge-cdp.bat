@echo off
REM ============================================================
REM  Edge CDP 一键启动脚本
REM  - 用独立 user-data-dir，不干扰你日常的 Edge
REM  - 参数不会被已有进程吞掉
REM  - 双击即可，命令行调用也行
REM ============================================================
chcp 65001 >nul

set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
set "PORT=9222"
set "PROFILE=C:\edge-cdp-profile"

if not exist "%EDGE%" (
    set "EDGE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)

REM 用 start 启动，脚本不会 hang
start "" "%EDGE%" ^
    --remote-debugging-port=%PORT% ^
    --user-data-dir="%PROFILE%" ^
    --no-first-run ^
    --no-default-browser-check

echo Edge CDP 已在后台启动，端口 %PORT%
echo 检查中...
timeout /t 2 /nobreak >nul

curl -s http://127.0.0.1:%PORT%/json/version
echo.
echo 如果上面输出了 Browser 信息，就成功了。
pause

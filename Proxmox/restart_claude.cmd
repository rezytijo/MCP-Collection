@echo off
REM Script CMD untuk restart Claude Desktop

REM Kill process Claude jika berjalan
taskkill /f /im Claude.exe >nul 2>&1
if %errorlevel%==0 (
    echo Claude Desktop process killed.
) else (
    echo Claude Desktop process not running or failed to kill.
)

REM Start Claude Desktop
REM Path default Claude Desktop
set CLAUDE_PATH=%LOCALAPPDATA%\AnthropicClaude\claude.exe

if exist "%CLAUDE_PATH%" (
    start "" "%CLAUDE_PATH%"
    echo Claude Desktop started.
) else (
    echo Claude Desktop executable not found at %CLAUDE_PATH%. Please check installation path.
    REM Alternative: Try to start via shell (might not work in CMD)
    echo Please start Claude Desktop manually if not started.
)
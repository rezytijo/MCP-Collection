# Kill all Claude processes
Get-Process | Where-Object {$_.Name -like "*Claude*"} | Stop-Process -Force

# Wait
Start-Sleep -Seconds 5

# Start Claude (adjust path if needed)
Start-Process "$env:LOCALAPPDATA\AnthropicClaude\Claude.exe"

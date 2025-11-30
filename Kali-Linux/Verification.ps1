Write-Host "`n=== 1. Checking Project Files ===" -ForegroundColor Cyan
$projectPath = "C:\Users\primall\OneDrive - Kementerian Komunikasi dan Informatika\Documents\Kantor\Program\Kali-Linux-MCP"
if (Test-Path $projectPath) {
    Write-Host "✓ Project directory exists" -ForegroundColor Green
    Get-ChildItem $projectPath | Select-Object Name, Length | Format-Table
} else {
    Write-Host "✗ Project directory NOT found!" -ForegroundColor Red
}

Write-Host "`n=== 2. Checking Docker Image ===" -ForegroundColor Cyan
$image = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String "pentest-mcp-server"
if ($image) {
    Write-Host "✓ Docker image exists: $image" -ForegroundColor Green
} else {
    Write-Host "✗ Docker image NOT found! Run: docker build -t pentest-mcp-server ." -ForegroundColor Red
}

Write-Host "`n=== 3. Checking kali-mcp.yaml ===" -ForegroundColor Cyan
$catalogPath = "$env:USERPROFILE\.docker\mcp\catalogs\kali-mcp.yaml"
if (Test-Path $catalogPath) {
    Write-Host "✓ kali-mcp.yaml exists" -ForegroundColor Green
    $content = Get-Content $catalogPath -Raw
    if ($content -match "pentest:") {
        Write-Host "✓ Contains 'pentest' entry" -ForegroundColor Green
    } else {
        Write-Host "✗ Missing 'pentest' entry!" -ForegroundColor Red
    }
} else {
    Write-Host "✗ kali-mcp.yaml NOT found!" -ForegroundColor Red
}

Write-Host "`n=== 4. Checking registry.yaml ===" -ForegroundColor Cyan
$registryPath = "$env:USERPROFILE\.docker\mcp\registry.yaml"
if (Test-Path $registryPath) {
    Write-Host "✓ registry.yaml exists" -ForegroundColor Green
    $content = Get-Content $registryPath -Raw
    if ($content -match "pentest:") {
        Write-Host "✓ Contains 'pentest' entry" -ForegroundColor Green
    } else {
        Write-Host "✗ Missing 'pentest' entry!" -ForegroundColor Red
    }
} else {
    Write-Host "✗ registry.yaml NOT found!" -ForegroundColor Red
}

Write-Host "`n=== 5. Checking Claude Config ===" -ForegroundColor Cyan
$claudeConfig = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $claudeConfig) {
    Write-Host "✓ Claude config exists" -ForegroundColor Green
    $content = Get-Content $claudeConfig -Raw
    if ($content -match "kali-mcp.yaml") {
        Write-Host "✓ Contains 'kali-mcp.yaml' reference" -ForegroundColor Green
    } else {
        Write-Host "✗ Missing 'kali-mcp.yaml' reference!" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Claude config NOT found!" -ForegroundColor Red
}

Write-Host "`n=== Summary ===" -ForegroundColor Yellow
Write-Host "If all checks show ✓, restart Claude Desktop completely."
Write-Host "If any check shows ✗, fix that issue first."

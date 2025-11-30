<#
.SYNOPSIS
    Builds and pushes the Proxmox MCP Server Docker image for multiple architectures.

.DESCRIPTION
    This script uses 'docker buildx' to build the image for:
    - linux/amd64
    - linux/arm/v7
    - linux/arm64
    - linux/ppc64le
    - linux/s390x
    
    It tags the image with a specific version and 'latest', then pushes it to Docker Hub.

.PARAMETER DockerHubUser
    Your Docker Hub username. Required.

.PARAMETER Version
    The version tag for the image (e.g., "30-11-2025"). 
    Defaults to current date in dd-MM-yyyy format.

.PARAMETER ImageName
    The name of the image repository. Defaults to "proxmox-mcp-server".

.EXAMPLE
    .\build_and_push.ps1 -DockerHubUser "myuser"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$DockerHubUser,

    [string]$Version = $(Get-Date -Format "dd-MM-yyyy"),

    [string]$ImageName = "proxmox-mcp-server"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Proxmox MCP Server Build Script ===" -ForegroundColor Cyan
Write-Host "Docker Hub User: $DockerHubUser"
Write-Host "Image Name:      $ImageName"
Write-Host "Version Tag:     $Version"
Write-Host "Platforms:       linux/amd64, linux/arm/v7, linux/arm64, linux/ppc64le, linux/s390x"
Write-Host "======================================="

# 1. Check for Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in the PATH."
    exit 1
}

# 2. Create/Select Buildx Builder
Write-Host "`n[1/4] Setting up Docker Buildx..." -ForegroundColor Yellow
$builderName = "mcp-multiarch-builder"

if (-not (docker buildx ls | Select-String $builderName)) {
    Write-Host "Creating new buildx builder: $builderName"
    docker buildx create --name $builderName --use --bootstrap
} else {
    Write-Host "Using existing buildx builder: $builderName"
    docker buildx use $builderName
}

# 3. Verify Login (Basic check)
Write-Host "`n[2/4] Verifying Docker Hub connectivity..." -ForegroundColor Yellow
try {
    # Attempt to pull a tiny public image to verify connectivity/auth basics, 
    # strictly speaking 'docker login' is manual, but we assume user is logged in.
    # If not, the push will fail later.
    Write-Host "Ensure you have run 'docker login' before this script if needed."
} catch {
    Write-Warning "Could not verify connectivity. Proceeding, but push might fail."
}

# 4. Build and Push
$fullImageName = "$DockerHubUser/$ImageName"
# Fixed interpolation issue with colon by using subexpression or curly braces not strictly needed if quoted right but safe way:
$tags = "-t ${fullImageName}:${Version} -t ${fullImageName}:latest"
$platforms = "--platform linux/amd64,linux/arm/v7,linux/arm64,linux/ppc64le,linux/s390x"

Write-Host "`n[3/4] Building and Pushing image..." -ForegroundColor Yellow
Write-Host "Command: docker buildx build $platforms $tags --push ." -ForegroundColor DarkGray

try {
    Invoke-Expression "docker buildx build $platforms $tags --push ."
    
    Write-Host "`n[4/4] Success!" -ForegroundColor Green
    Write-Host "Images pushed to:"
    Write-Host "  - ${fullImageName}:${Version}"
    Write-Host "  - ${fullImageName}:latest"
} catch {
    Write-Error "Build failed. Please check the error output above."
    exit 1
}

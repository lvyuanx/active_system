[CmdletBinding()]
param(
    [switch]$Docker
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

function Assert-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Command not found: $Name. $InstallHint"
    }
}

if ($Docker) {
    throw ("请先运行 python deploy/build.py；复制 deploy 到服务器并配置 .env 后，在该目录运行 " +
        "docker compose --env-file .env up -d --build --wait。详见 deploy/README.md。")
}

Assert-Command "pnpm" "Install pnpm first."
Assert-Command "python" "Install Python 3.11+ first."

$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Warning "No .env found. The backend will use built-in defaults; copy .env.example and set SUPERUSER_PASSWORD."
}

$backendTitle = "Active System - FastAPI Backend"
$frontendTitle = "Active System - Vue Frontends"

Start-Process powershell.exe -WorkingDirectory $projectRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$Host.UI.RawUI.WindowTitle = '$backendTitle'; uvicorn app.main:app --app-dir apps/backend --reload"
)

Start-Process powershell.exe -WorkingDirectory $projectRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$Host.UI.RawUI.WindowTitle = '$frontendTitle'; pnpm dev"
)

Write-Host "Backend and frontend process windows started." -ForegroundColor Green
Write-Host "Admin:  http://localhost:5173" -ForegroundColor Gray
Write-Host "Screen: http://localhost:5174" -ForegroundColor Gray
Write-Host "User:   http://localhost:5175" -ForegroundColor Gray
Write-Host "API:    http://localhost:8000/docs" -ForegroundColor Gray

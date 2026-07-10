# ==============================================================================
# DataForge AI - Local Development Startup Script (Windows PowerShell)
# ==============================================================================

# Ensure we execute from the script's directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "             Starting DataForge AI Services               " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify and configure active .env file
if (-not (Test-Path ".env")) {
    Write-Host "[*] Creating active '.env' from example configuration..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
} else {
    Write-Host "[✓] Found active '.env' configuration." -ForegroundColor Green
}

# 2. Check local PostgreSQL status
Write-Host "[*] Scanning for local PostgreSQL service..." -ForegroundColor Gray
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService) {
    if ($pgService.Status -ne "Running") {
        Write-Host "[!] Found PostgreSQL service ($($pgService.Name)) but it is stopped. Attempting to start..." -ForegroundColor Yellow
        Start-Service -Name $pgService.Name -ErrorAction SilentlyContinue
        # Refresh status
        $pgService = Get-Service -Name $pgService.Name
        if ($pgService.Status -eq "Running") {
            Write-Host "[✓] PostgreSQL service started successfully." -ForegroundColor Green
        } else {
            Write-Host "[!] Could not start PostgreSQL service. Ensure you run as Administrator, or the app will fall back to local SQLite." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[✓] Local PostgreSQL service ($($pgService.Name)) is active and running." -ForegroundColor Green
    }
} else {
    Write-Host "[*] No local PostgreSQL service detected. The application will fallback to local SQLite database." -ForegroundColor Yellow
}

# 3. Launch Backend API Server in a separate window
Write-Host "[*] Bootstrapping Backend API (Uvicorn on Port 8000)..." -ForegroundColor Green
Start-Process powershell -WorkingDirectory "$ScriptDir\backend" -ArgumentList "-NoExit", "-Command", "`$host.ui.RawUI.WindowTitle = 'DataForge API Logs'; python -m poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

# 4. Launch Frontend Dev Server in a separate window
Write-Host "[*] Bootstrapping Frontend Next.js (Port 3000)..." -ForegroundColor Green
Start-Process powershell -WorkingDirectory "$ScriptDir\frontend" -ArgumentList "-NoExit", "-Command", "`$host.ui.RawUI.WindowTitle = 'DataForge Frontend Logs'; npm run dev"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[✓] Launch complete. Monitors are starting in new terminals." -ForegroundColor Green
Write-Host "    - API Endpoint:       http://localhost:8000" -ForegroundColor Gray
Write-Host "    - Swagger Docs:       http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "    - Frontend Dashboard: http://localhost:3000" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

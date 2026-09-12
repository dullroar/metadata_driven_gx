<#
.SYNOPSIS
Create/refresh this repo's single virtual environment from requirements.txt.

.DESCRIPTION
Deactivates any currently active virtual environment, creates a .venv next to this
script if one doesn't already exist, activates it, upgrades pip, and installs
requirements.txt.

Useful for setting up a fresh clone, or refreshing after requirements.txt changes.

.EXAMPLE
PS> .\setup_venv.ps1
#>

param()

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

Write-Host "[*] Setting up .venv..." -ForegroundColor Cyan

if ($env:VIRTUAL_ENV) {
    Write-Host "    Deactivating current venv: $env:VIRTUAL_ENV" -ForegroundColor Yellow
    & deactivate 2>$null
}

Push-Location $scriptRoot
try {
    $venvPath = Join-Path $scriptRoot ".venv"
    if (-not (Test-Path $venvPath)) {
        Write-Host "    Creating .venv..." -ForegroundColor Yellow
        python.exe -m venv .venv
    }

    & ".\.venv\Scripts\Activate.ps1"
    python.exe -m pip install --upgrade pip
    python.exe -m pip install -r requirements.txt

    Write-Host ""
    Write-Host "[OK] .venv ready! Activate it in a new shell with:" -ForegroundColor Green
    Write-Host "     .\.venv\Scripts\Activate.ps1"
}
finally {
    Pop-Location
}

# UI Test Launcher - Quick Start Script
# Uruchamia narzędzie do testowania komponentów UI z różnymi motywami

Write-Host "🧪 Uruchamianie UI Test Launcher..." -ForegroundColor Cyan
Write-Host ""

# Przejdź do głównego katalogu projektu
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "📁 Katalog projektu: $projectRoot" -ForegroundColor Yellow
Write-Host ""

# Sprawdź czy Python jest dostępny
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python nie został znaleziony w PATH!" -ForegroundColor Red
    Write-Host "Zainstaluj Python i spróbuj ponownie." -ForegroundColor Red
    pause
    exit 1
}

# Uruchom launcher
Write-Host "🚀 Uruchamianie test launchera..." -ForegroundColor Green
Write-Host ""

python tests/test_ui_launcher.py

Write-Host ""
Write-Host "✅ Test launcher zakończył działanie." -ForegroundColor Green
pause

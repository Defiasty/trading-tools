$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".build-venv\Scripts\python.exe")) {
    python -m venv .build-venv
}
& ".build-venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
& ".build-venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --name TradingTracker --icon "static\img\app-icon.ico" --add-data "templates;templates" --add-data "static\css;static\css" --add-data "static\js;static\js" --add-data "static\img\app-logo.png;static\img" --add-data "static\img\app-icon.ico;static\img" --add-data "static\uploads\.gitkeep;static\uploads" --add-data "VERSION;." --collect-all webview desktop.py

$compiler = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"
if (-not (Test-Path $compiler)) { throw "Inno Setup 7 is required to build the final installer." }
& $compiler "installer.iss"
Write-Host "Installer ready: installer-output\TradingTracker-Setup-6.1.0.exe"

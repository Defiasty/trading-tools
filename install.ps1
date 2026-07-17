$ErrorActionPreference = "Stop"
$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installRoot = Join-Path $env:LOCALAPPDATA "TradingTracker"

Write-Host "Installing Trading Tracker to $installRoot"
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null

$excluded = @("venv", ".venv", "__pycache__", ".git", "trades.db")
Get-ChildItem -LiteralPath $sourceRoot -Force | Where-Object { $excluded -notcontains $_.Name } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $installRoot -Recurse -Force
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python 3 is required. Install it from python.org and run INSTALL.bat again." }
if (-not (Test-Path (Join-Path $installRoot "venv\Scripts\python.exe"))) {
    & $python.Source -m venv (Join-Path $installRoot "venv")
}
& (Join-Path $installRoot "venv\Scripts\python.exe") -m pip install -r (Join-Path $installRoot "requirements.txt")

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Trading Tracker.lnk"))
$shortcut.TargetPath = Join-Path $installRoot "start.bat"
$shortcut.WorkingDirectory = $installRoot
$shortcut.Save()

Write-Host "Installation complete. A desktop shortcut was created."
Start-Process -FilePath (Join-Path $installRoot "start.bat") -WorkingDirectory $installRoot

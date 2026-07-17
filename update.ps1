$ErrorActionPreference = "Stop"
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("trading-tracker-update-" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot "update.zip"
$extractPath = Join-Path $tempRoot "source"

New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
try {
    Write-Host "Downloading the latest clean release..."
    Invoke-WebRequest -Uri "https://github.com/Defiasty/trading-tools/archive/refs/heads/main.zip" -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath
    $source = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
    if (-not $source) { throw "Downloaded update is invalid." }

    $protected = @("trades.db", "static\uploads", "venv", ".venv", "currency.txt", "balance.txt", "profit_target.txt", "max_loss_limit.txt", "daily_loss_limit.txt", "consistency_limit.txt", "account_profile.txt")
    Get-ChildItem -LiteralPath $source.FullName -Force | ForEach-Object {
        if ($protected -notcontains $_.Name) {
            Copy-Item -LiteralPath $_.FullName -Destination $appRoot -Recurse -Force
        }
    }
    Write-Host "Update complete. Local trades, screenshots and settings were preserved."
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}

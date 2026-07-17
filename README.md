# Trading Tracker

Local futures trading journal with a built-in position-size calculator, Topstep risk dashboard, interactive analytics, calendar, trade review, CSV import/export and full local backups.

## Install on Windows

Download `TradingTracker-Setup-6.1.0.exe`, run the installer and launch Trading Tracker from the desktop or Start menu. The installed application includes its own Python runtime and dependencies; Python does not need to be installed separately.

Developers can still run the source version with `start.bat` or reproduce the Windows installer with `build-installer.ps1`.

## Privacy

Trading history is stored locally in `trades.db`. Screenshots are stored in `static/uploads`. Both locations, along with account-setting files, are excluded from Git and are never included in this repository.

## Supported futures

NQ, MNQ, ES, MES, YM, MYM, RTY, M2K, CL, MCL, GC and MGC.

## Backup

Use **Backup** in the app to download a ZIP containing the local database, screenshots and account settings. Keep that archive private.

## Updates

Installing a newer version over the existing installation preserves the database, screenshots, WebView profile and account settings stored under `D:\TradingTrackerData`.

## Highlights

- Topstep 50K, 100K and 150K account profiles
- trailing drawdown and daily-risk monitoring
- CSV imports for common TopstepX, Tradovate and NinjaTrader exports
- setup Playbook with rules, checklists and performance statistics
- position-size calculator connected to the New Trade form
- interactive analytics, calendar and Trade Review

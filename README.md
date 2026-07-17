# Trading Tracker

Local futures trading journal with a built-in position-size calculator, Topstep risk dashboard, interactive analytics, calendar, trade review, CSV import/export and full local backups.

## Install on Windows

1. Download and extract the repository.
2. Double-click `INSTALL.bat` for a local installation and desktop shortcut.

For portable use, run `start.bat` directly. Open `http://127.0.0.1:5000` if the browser does not open automatically.

The launcher creates a Python virtual environment and installs the two dependencies from `requirements.txt`.

## Privacy

Trading history is stored locally in `trades.db`. Screenshots are stored in `static/uploads`. Both locations, along with account-setting files, are excluded from Git and are never included in this repository.

## Supported futures

NQ, MNQ, ES, MES, YM, MYM, RTY, M2K, CL, MCL, GC and MGC.

## Backup

Use **Backup** in the app to download a ZIP containing the local database, screenshots and account settings. Keep that archive private.

## Updates

Run `UPDATE.bat` to download the latest code from the public repository. The updater preserves `trades.db`, screenshots, account settings and the Python environment.

## Highlights

- Topstep 50K, 100K and 150K account profiles
- trailing drawdown and daily-risk monitoring
- CSV imports for common TopstepX, Tradovate and NinjaTrader exports
- setup Playbook with rules, checklists and performance statistics
- position-size calculator connected to the New Trade form
- interactive analytics, calendar and Trade Review

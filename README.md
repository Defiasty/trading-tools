# Trading Tracker

Local futures trading journal with a built-in position-size calculator, Topstep risk dashboard, interactive analytics, calendar, trade review, CSV import/export and full local backups.

## Run on Windows

1. Download and extract the repository.
2. Double-click `start.bat`.
3. Open `http://127.0.0.1:5000` if the browser does not open automatically.

The launcher creates a Python virtual environment and installs the two dependencies from `requirements.txt`.

## Privacy

Trading history is stored locally in `trades.db`. Screenshots are stored in `static/uploads`. Both locations, along with account-setting files, are excluded from Git and are never included in this repository.

## Supported futures

NQ, MNQ, ES, MES, YM, MYM, RTY, M2K, CL, MCL, GC and MGC.

## Backup

Use **Backup** in the app to download a ZIP containing the local database, screenshots and account settings. Keep that archive private.

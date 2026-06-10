# Partner Links Mobile

Automated checks for real links inside mobile tariff cards on production landing pages.

## What it does

- opens all production URLs from config;
- finds visible mobile tariff cards;
- clicks card CTAs;
- records the actual URL after click;
- checks technical availability of the opened page;
- saves an `.xlsx` report in `reports/`.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

All URLs:

```bash
pytest
```

One domain:

```bash
pytest --target domain --domain t2-ru.online
```

One URL:

```bash
pytest --target url --url https://t2-ru.online/mobilnaya-svyaz
```

Pilot mode:

```bash
pytest --run-mode pilot
```

Release mode:

```bash
pytest --run-mode release
```

## Parameters

- `--target all|domain|url`
- `--domain <domain>`
- `--url <url>`
- `--run-mode pilot|release`
- `--headed`
- `--timeout-ms <value>`
- `--report-dir <path>`
- `--playwright-trace off|retain-on-failure|on`
- `--screenshot off|on|only-on-failure`

## Report

The report is saved to `reports/`:

`partner_links_mobile_YYYY-MM-DD_HH-MM.xlsx`

## Jenkins

- weekly trigger: `H H * * 1`;
- `release` mode fails the job if the report contains at least one product error;
- `.xlsx` is archived as a build artifact.

### Jenkins cache

- Playwright browsers reuse shared cache in `JENKINS_HOME\cache\ms-playwright`.
- Python packages reuse shared pip cache in `JENKINS_HOME\cache\pip`.
- Dependencies are installed only when `requirements.txt` changes.
- Existing `.venv` is reused when present.

### Jenkins cleanup

- `ENABLE_PERIODIC_ARTIFACT_PURGE=true` turns on periodic cleanup of old build archives.
- `PERIODIC_PURGE_EVERY` controls how often cleanup runs, default `5`.
- On cleanup runs, old `archive` and `allure-report` folders from previous builds are removed.
- Workspace temp files are cleaned after each run: `artifacts`, `.pytest_cache`, `pytest-cache-files-*`, `__pycache__`.

### Jenkins parameters

- `TARGET`
- `DOMAIN`
- `URL`
- `RUN_MODE`
- `HEADLESS`
- `TRACE`
- `SCREENSHOT`
- `ENABLE_PERIODIC_ARTIFACT_PURGE`
- `PERIODIC_PURGE_EVERY`

## Configuration updates

All URLs and selectors live in `config/landings.py`.

# Partner Links Mobile

Automated checks for partner links in mobile tariff cards on production landing pages.

## What it does

- opens production landing pages from `config/landings.py`;
- finds visible mobile tariff cards;
- clicks the CTA button inside each card;
- captures the URL after the click;
- checks the technical availability of the opened page;
- writes an `.xlsx` report to `reports/`.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## First iteration

Run all configured landings:

```bash
pytest
```

Run one domain:

```bash
pytest --target domain --domain t2-ru.online
```

Run one URL:

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

Useful parameters:

- `--target all|domain|url`
- `--domain <domain>`
- `--url <url>`
- `--run-mode pilot|release`
- `--headed`
- `--timeout-ms <value>`
- `--report-dir <path>`
- `--playwright-trace off|retain-on-failure|on`
- `--screenshot off|on|only-on-failure`

The first iteration report is saved as:

`reports/partner_links_mobile_YYYY-MM-DD_HH-MM.xlsx`

## Second iteration

The second iteration validates the first report against the reference file from Jenkins secret file `Links_mobile_tarriffs`.

Local run:

```bash
python -m src.validate_partner_links \
  --input-report reports/partner_links_mobile_2026-06-11_09-55.xlsx \
  --reference-file path/to/Links_mobile_tarriffs.xlsx \
  --output-report reports/partner_links_mobile_validated.xlsx
```

Optional fallback:

```bash
python -m src.validate_partner_links \
  --input-report reports/partner_links_mobile_2026-06-11_09-55.xlsx \
  --reference-file path/to/Links_mobile_tarriffs.xlsx \
  --output-report reports/partner_links_mobile_validated.xlsx \
  --use-final-url-as-fallback
```

Validation statuses:

- `OK`
- `НЕ OK`
- `НЕТ ЭТАЛОНА`
- `НЕТ ФАКТИЧЕСКОЙ ССЫЛКИ`

Release mode treats `НЕ OK` and `НЕТ ФАКТИЧЕСКОЙ ССЫЛКИ` as product errors. `НЕТ ЭТАЛОНА` is a reference-data issue and does not fail release by itself.

## Jenkins

Pipeline flow:

1. Stage 1 runs the Playwright checks and produces the first `.xlsx` report.
2. Stage 2 reads that report, compares it with `Links_mobile_tarriffs`, writes a validated report, and sends a Telegram alert through the proxy.

Jenkins parameters:

- `TARGET`
- `DOMAIN`
- `URL`
- `RUN_MODE`
- `HEADLESS`
- `TRACE`
- `SCREENSHOT`
- `USE_FINAL_URL_AS_FALLBACK`
- `ENABLE_PERIODIC_ARTIFACT_PURGE`
- `PERIODIC_PURGE_EVERY`

The pipeline uses:

- shared Playwright browser cache in `JENKINS_HOME/cache/ms-playwright`;
- shared pip cache in `JENKINS_HOME/cache/pip`;
- secret file credential `Links_mobile_tarriffs`;
- Telegram proxy credentials:
  - `telegram_proxy_url`
  - `telegram_proxy_auth_secret`
  - `telegram_proxy_global_test`

## Jenkins UI selection

- If `TARGET=domain` and `DOMAIN` is empty, Jenkins shows a dropdown with available domains.
- If `TARGET=url` and `URL` is empty, Jenkins shows a dropdown with available URLs.
- The dropdown values are taken from `config/landings.py`, so new landings appear automatically after a repo update.

## Jenkins cleanup

- `ENABLE_PERIODIC_ARTIFACT_PURGE=true` enables periodic cleanup of old archived build artifacts.
- `PERIODIC_PURGE_EVERY` controls how often cleanup runs. Default: `5`.
- The cleanup step removes old `archive` and `allure-report` folders from older builds.
- After each run the workspace temp files are cleaned: `artifacts`, `.pytest_cache`, `pytest-cache-files-*`, `__pycache__`.

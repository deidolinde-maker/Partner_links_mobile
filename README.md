# Partner Links Mobile

Автоматическая проверка партнерских ссылок в карточках мобильных тарифов на продовых лендингах.

## Что делает

- открывает продовые лендинги из `config/landings.py`;
- находит видимые карточки мобильных тарифов;
- кликает CTA-кнопку внутри карточки;
- фиксирует URL после клика;
- проверяет техническую доступность открытой страницы;
- сохраняет `.xlsx`-отчет в `reports/`.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Первая итерация

Запуск всех настроенных лендингов:

```bash
pytest
```

Запуск одного домена:

```bash
pytest --target domain --domain t2-ru.online
```

Запуск одного URL:

```bash
pytest --target url --url https://t2-ru.online/mobilnaya-svyaz
```

Pilot-режим:

```bash
pytest --run-mode pilot
```

Release-режим:

```bash
pytest --run-mode release
```

Полезные параметры:

- `--target all|domain|url`
- `--domain <domain>`
- `--url <url>`
- `--run-mode pilot|release`
- `--headed`
- `--timeout-ms <value>`
- `--report-dir <path>`
- `--playwright-trace off|retain-on-failure|on`
- `--screenshot off|on|only-on-failure`

Отчет первой итерации сохраняется как:

`reports/partner_links_mobile_YYYY-MM-DD_HH-MM.xlsx`

## Вторая итерация

Вторая итерация проверяет первый отчет по эталонному файлу из Jenkins secret file `Links_mobile_tarriffs`.

Локальный запуск:

```bash
python -m src.validate_partner_links \
  --input-report reports/partner_links_mobile_2026-06-11_09-55.xlsx \
  --reference-file path/to/Links_mobile_tarriffs.xlsx \
  --output-report reports/partner_links_mobile_validated.xlsx
```

Опциональный fallback:

```bash
python -m src.validate_partner_links \
  --input-report reports/partner_links_mobile_2026-06-11_09-55.xlsx \
  --reference-file path/to/Links_mobile_tarriffs.xlsx \
  --output-report reports/partner_links_mobile_validated.xlsx \
  --use-final-url-as-fallback
```

Статусы валидации:

- `OK`
- `НЕ OK`
- `НЕТ ЭТАЛОНА`
- `НЕТ ФАКТИЧЕСКОЙ ССЫЛКИ`

Release-режим считает `НЕ OK` и `НЕТ ФАКТИЧЕСКОЙ ССЫЛКИ` продуктовыми ошибками. `НЕТ ЭТАЛОНА` — это проблема данных эталона, и сама по себе она не валит release.

## Jenkins

Схема пайплайна:

1. Stage 1 запускает Playwright-проверки и создает отчет первой итерации `.xlsx`.
2. Stage 2 читает этот отчет, сравнивает его с `Links_mobile_tarriffs`, создает валидационный отчет и отправляет Telegram-алерт через прокси.
3. Если `VALIDATION_ONLY=true`, Stage 1 пропускается, а Stage 2 валидирует последний отчет, уже лежащий в `reports/`.

Параметры Jenkins:

- `TARGET`
- `VALIDATION_ONLY`
- `DOMAIN`
- `URL`
- `RUN_MODE`
- `HEADLESS`
- `TRACE`
- `SCREENSHOT`
- `USE_FINAL_URL_AS_FALLBACK`
- `ENABLE_PERIODIC_ARTIFACT_PURGE`
- `PERIODIC_PURGE_EVERY`

Пайплайн использует:

- общий кеш браузеров Playwright в `JENKINS_HOME/cache/ms-playwright`;
- общий кеш pip в `JENKINS_HOME/cache/pip`;
- секретный file credential `Links_mobile_tarriffs`;
- Telegram proxy credentials:
  - `telegram_proxy_url`
  - `telegram_proxy_auth_secret`
  - `telegram_proxy_global_test` (в Jenkins привязан к `TELEGRAM_PROXY_CREDS`)

## Выбор лендинга в Jenkins UI

- Если `TARGET=domain`, а `DOMAIN` пустой, Jenkins показывает dropdown со списком доступных доменов.
- Если `TARGET=url`, а `URL` пустой, Jenkins показывает dropdown со списком доступных URL.
- Значения в dropdown берутся из `config/landings.py`, поэтому новые лендинги появляются автоматически после обновления репозитория.
- Если `VALIDATION_ONLY=true`, Jenkins пропускает браузерный прогон и автоматически выбирает самый новый first-iteration `.xlsx` отчет из `reports/`.

## Очистка Jenkins

- `ENABLE_PERIODIC_ARTIFACT_PURGE=true` включает периодическую очистку старых архивированных артефактов сборок.
- `PERIODIC_PURGE_EVERY` задает, как часто выполнять очистку. Значение по умолчанию: `5`.
- Шаг очистки удаляет старые папки `archive` и `allure-report` у предыдущих сборок.
- После каждого прогона workspace temp-файлы очищаются: `artifacts`, `.pytest_cache`, `pytest-cache-files-*`, `__pycache__`.

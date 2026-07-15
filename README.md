# Partner Links Mobile

Автотест для проверки фактических ссылок в карточках мобильных тарифов на prod-лендингах.

## Что делает

- открывает все prod URL из конфига;
- находит видимые карточки мобильных тарифов;
- кликает по CTA;
- фиксирует фактический URL после клика;
- проверяет техническую доступность открывшейся страницы;
- сохраняет `.xlsx` отчет в `reports/`.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Запуск

Все URL:

```bash
pytest
```

Один домен:

```bash
pytest --target domain --domain t2-ru.online
```

Один URL:

```bash
pytest --target url --url https://t2-ru.online/mobilnaya-svyaz
```

Pilot режим:

```bash
pytest --run-mode pilot
```

Release режим:

```bash
pytest --run-mode release
```

## Параметры

- `--target all|domain|url`
- `--domain <domain>`
- `--url <url>`
- `--run-mode pilot|release`
- `--headed`
- `--timeout-ms <value>`
- `--report-dir <path>`
- `--trace off|retain-on-failure|on`
- `--screenshot off|on|only-on-failure`

## Отчет

Файл сохраняется в `reports/`:

`partner_links_mobile_YYYY-MM-DD_HH-MM.xlsx`

## Jenkins

Пайплайн работает в две итерации:

1. Stage 1 запускает Playwright-проверки по prod-лендам и сохраняет отчет первой итерации `.xlsx` в `reports/`.
2. Stage 2 берет этот отчет, валидирует его по `Links_mobile_tarriffs`, формирует валидированный `.xlsx` и отправляет Telegram-алерт через прокси.
3. Если `VALIDATION_ONLY=true`, Stage 1 пропускается, а Stage 2 автоматически валидирует самый свежий first-iteration отчет из `reports/`.

Общая информация:

- еженедельный запуск: `H H * * 1`;
- в `release` режиме job завершается `failed`, если в отчете есть хотя бы одна продуктовая ошибка;
- `.xlsx` отчеты архивируются как artifacts.

Jenkins cache:

- браузеры Playwright переиспользуют общий кэш в `JENKINS_HOME/cache/ms-playwright`;
- пакеты Python переиспользуют общий pip-кэш в `JENKINS_HOME/cache/pip`;
- зависимости устанавливаются только когда меняется `requirements.txt`;
- существующий `.venv` переиспользуется, если он уже есть.

Jenkins cleanup:

- `ENABLE_PERIODIC_ARTIFACT_PURGE=true` включает периодическую очистку старых архивов сборок;
- `PERIODIC_PURGE_EVERY` задает, как часто запускать очистку. Значение по умолчанию: `5`;
- в cleanup-итерации удаляются старые папки `archive` и `allure-report` у прошлых билдов;
- после прогона очищаются временные файлы workspace: `artifacts`, `.pytest_cache`, `pytest-cache-files-*`, `__pycache__`.

Jenkins parameters:

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

- секретный file credential `Links_mobile_tarriffs`;
- Telegram proxy credentials:
  - `telegram_proxy_url`
  - `telegram_proxy_auth_secret`
  - `telegram_proxy_global_test` (в Jenkins привязан к `TELEGRAM_PROXY_CREDS`)

## Обновление конфигурации

Все URL и селекторы живут в `config/landings.py`.

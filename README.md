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

Pilot-режим:

```bash
pytest --run-mode pilot
```

Release-режим:

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
- `--playwright-trace off|retain-on-failure|on`
- `--screenshot off|on|only-on-failure`

## Отчет

Отчет сохраняется в `reports/`:

`partner_links_mobile_YYYY-MM-DD_HH-MM.xlsx`

## Jenkins

- еженедельный запуск: `H H * * 1`;
- в `release`-режиме job должна завершаться `failed`, если в отчете есть хотя бы одна продуктовая ошибка;
- `.xlsx` архивируется как artifact.

### Jenkins cache

- Jenkins job ожидает Linux-агент и использует `sh`, а не `powershell`.
- браузеры Playwright переиспользуют общий кэш в `JENKINS_HOME/cache/ms-playwright`;
- пакеты Python переиспользуют общий pip-кэш в `JENKINS_HOME/cache/pip`;
- зависимости устанавливаются только когда меняется `requirements.txt`;
- существующий `.venv` переиспользуется, если он уже есть.

### Jenkins cleanup

- `ENABLE_PERIODIC_ARTIFACT_PURGE=true` включает периодическую очистку старых архивов сборок;
- `PERIODIC_PURGE_EVERY` задает, как часто запускать очистку, по умолчанию `5`;
- в cleanup-итерации удаляются старые папки `archive` и `allure-report` у прошлых билдов;
- после прогона очищаются временные файлы workspace: `artifacts`, `.pytest_cache`, `pytest-cache-files-*`, `__pycache__`.

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

### Jenkins UI selection

- `DOMAIN` и `URL` в Jenkins отображаются как dropdown-ы, а не как ручной ввод.
- Списки для dropdown собираются из `config/landings.py`, поэтому новые URL и домены подхватываются автоматически после обновления репозитория.
- Значение `Select` считается пустым и не мешает запуску `TARGET=all`.
- Для динамических dropdown-ов в Jenkins нужен плагин Active Choices.

## Обновление конфигурации

Все URL и селекторы живут в `config/landings.py`.

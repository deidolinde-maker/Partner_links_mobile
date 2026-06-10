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

- еженедельный запуск: `H H * * 1`;
- в `release` режиме job должен завершаться `failed`, если в отчете есть хотя бы одна продуктовая ошибка;
- `.xlsx` сохраняется как artifact.

## Обновление конфигурации

Все URL и селекторы живут в `config/landings.py`.


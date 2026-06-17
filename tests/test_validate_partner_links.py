from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from src.alert_sender import build_validation_alert_message, send_validation_alert
from src.link_matcher import ReferenceIndex, evaluate_validation
from src.models import (
    ReportRow,
    VALIDATION_STATUS_NO_FACTUAL_LINK,
    VALIDATION_STATUS_NO_REFERENCE,
    VALIDATION_STATUS_NOT_OK,
    VALIDATION_STATUS_OK,
)
from src.reference_loader import load_reference_links
from src.report_writer import write_validation_report
from src.result_evaluator import summarize_validation_rows


REFERENCE_HEADERS = [
    "Домен",
    "URL проверяемой страницы",
    "Название тарифа",
    "Эталонная часть ссылки",
    "Тип сравнения",
    "Алиасы тарифа",
    "Активен",
]


def _write_xlsx(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def _build_input_row(**overrides: object) -> ReportRow:
    base = dict(
        domain="t2-ru.online",
        checked_page_url="https://t2-ru.online/mobilnaya-svyaz",
        tariff_name="МОЙ ОНЛАЙН",
        click_url="https://krasnodar.t2.ru/tariffs?utm_campaign=tariffs_webdealer_ooo_online_services_t2-ru_online&utm_medium=t2-ru_online&utm_source=webdealer&pageParams=askForRegion%3Dtrue",
        page_load_status="Успешно",
        http_status="200",
        final_url="https://krasnodar.t2.ru/tariffs?utm_campaign=tariffs_webdealer_ooo_online_services_t2-ru_online&utm_medium=t2-ru_online&utm_source=webdealer&pageParams=askForRegion%3Dtrue",
        error="",
        checked_at="2026-06-11 09:55:23",
        operator="T2",
        card_number="6",
        transition_type="new_tab",
        source_href="https://t2.ru/tariffs?utm_source=webdealer&utm_medium=t2-ru_online&utm_campaign=tariffs_webdealer_ooo_online_services_t2-ru_online",
        load_ms="12943",
        environment="run_mode=pilot; target=domain; browser=headless; trace=off; screenshot=off",
        product_error=False,
    )
    base.update(overrides)
    return ReportRow(**base)


def test_reference_loader_supports_aliases_and_inactive_rows(tmp_path: Path) -> None:
    reference_path = tmp_path / "Links_mobile_tarriffs.xlsx"
    _write_xlsx(
        reference_path,
        REFERENCE_HEADERS,
        [
            [
                "t2-ru.online",
                "https://t2-ru.online/mobilnaya-svyaz",
                "Мой Онлайн",
                "krasnodar.t2.ru/tariffs",
                "contains",
                "МОЙ ОНЛАЙН+;МОЙ ОНЛАЙН ПЛЮС",
                True,
            ],
            [
                "t2-ru.online",
                "https://t2-ru.online/mobilnaya-svyaz",
                "BLACK",
                "black",
                "contains",
                "",
                False,
            ],
        ],
    )

    references = load_reference_links(reference_path)
    index = ReferenceIndex.build(references)
    result = evaluate_validation(
        _build_input_row(tariff_name="МОЙ ОНЛАЙН+"),
        index,
    )

    assert result.status == VALIDATION_STATUS_OK
    assert result.reference_part == "krasnodar.t2.ru/tariffs"
    assert result.match_key == "t2-ru.online::https://t2-ru.online/mobilnaya-svyaz::мой онлайн+"


def test_validation_handles_regex_and_fallback(tmp_path: Path) -> None:
    reference_path = tmp_path / "Links_mobile_tarriffs.xlsx"
    _write_xlsx(
        reference_path,
        REFERENCE_HEADERS,
        [
            [
                "t2-ru.online",
                "",
                "ПАРТНЕР М",
                r"t2\.ru/promo/partner-all\?utm_source=webdealer",
                "regex",
                "",
                True,
            ],
        ],
    )

    references = load_reference_links(reference_path)
    index = ReferenceIndex.build(references)

    regex_result = evaluate_validation(
        _build_input_row(
            tariff_name="ПАРТНЕР М",
            click_url="https://t2.ru/promo/partner-all?utm_source=webdealer&utm_medium=t2-ru_online",
        ),
        index,
    )
    assert regex_result.status == VALIDATION_STATUS_OK

    fallback_result = evaluate_validation(
        _build_input_row(
            tariff_name="ПАРТНЕР М",
            click_url="",
            final_url="https://t2.ru/promo/partner-all?utm_source=webdealer&utm_medium=t2-ru_online",
        ),
        index,
        use_final_url_as_fallback=True,
    )
    assert fallback_result.status == VALIDATION_STATUS_OK


def test_validation_statuses_for_missing_reference_and_missing_link() -> None:
    index = ReferenceIndex.build([])

    no_fact_result = evaluate_validation(
        _build_input_row(click_url="", final_url=""),
        index,
    )
    assert no_fact_result.status == VALIDATION_STATUS_NO_FACTUAL_LINK

    no_ref_result = evaluate_validation(
        _build_input_row(click_url="https://example.com/landing"),
        index,
    )
    assert no_ref_result.status == VALIDATION_STATUS_NO_REFERENCE


def test_validation_report_writer_and_summary(tmp_path: Path) -> None:
    reference_path = tmp_path / "Links_mobile_tarriffs.xlsx"
    _write_xlsx(
        reference_path,
        REFERENCE_HEADERS,
        [
            [
                "t2-ru.online",
                "https://t2-ru.online/mobilnaya-svyaz",
                "МОЙ ОНЛАЙН",
                "krasnodar.t2.ru/tariffs",
                "contains",
                "",
                True,
            ],
        ],
    )
    references = load_reference_links(reference_path)
    index = ReferenceIndex.build(references)

    rows = [
        evaluate_validation(_build_input_row(tariff_name="МОЙ ОНЛАЙН"), index).row,
        evaluate_validation(_build_input_row(tariff_name="МОЙ ОНЛАЙН", click_url="https://example.com/other"), index).row,
        evaluate_validation(_build_input_row(tariff_name="BLACK", click_url="https://example.com/other"), index).row,
        evaluate_validation(_build_input_row(tariff_name="PREMIUM", click_url=""), index).row,
    ]

    report_path = write_validation_report(rows, tmp_path / "validated.xlsx")
    assert report_path.exists()

    workbook = load_workbook(report_path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    headers = [cell.value for cell in sheet[1]]
    assert "Эталонная часть ссылки" in headers
    assert "Итог проверки партнерской ссылки" in headers
    assert "Ключ сопоставления" in headers

    summary = summarize_validation_rows(rows, str(report_path), "pilot")
    assert summary.ok_rows == 1
    assert summary.not_ok_rows == 1
    assert summary.no_reference_rows == 1
    assert summary.no_factual_link_rows == 1
    assert summary.product_error_rows == 2


def test_alert_sender_skips_without_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_PROXY_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_PROXY_AUTH_SECRET", raising=False)
    monkeypatch.delenv("TELEGRAM_PROXY_CHAT_CREDENTIAL", raising=False)

    summary = summarize_validation_rows(
        [
            replace(_build_input_row(), validation_status=VALIDATION_STATUS_OK),
            replace(_build_input_row(tariff_name="BLACK"), validation_status=VALIDATION_STATUS_NOT_OK),
            replace(_build_input_row(tariff_name="PREMIUM"), validation_status=VALIDATION_STATUS_NO_REFERENCE),
        ],
        "reports/validated.xlsx",
        "pilot",
    )
    message = build_validation_alert_message(summary, "2026-06-11 09:55:23", "https://jenkins.example/job/1/")
    result = send_validation_alert(message)
    assert result.status == "skipped"

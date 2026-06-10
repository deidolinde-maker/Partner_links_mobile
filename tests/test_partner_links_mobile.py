from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import re

from playwright.sync_api import Page

from config.landings import LandingConfig
from src.availability_checker import check_url_availability
from src.click_resolver import click_card_cta
from src.models import (
    ReportRow,
    STATUS_CARDS_NOT_FOUND,
    STATUS_BUTTON_NOT_FOUND,
    STATUS_LOAD_ERROR,
    STATUS_URL_NOT_OPENED,
)
from src.page_loader import open_landing_page
from src.popup_handler import close_common_popups
from src.tariff_parser import detect_cards


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_error(status: str, error: str) -> str:
    if not error:
        return ""
    return f"{status}: {error}"


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _landing_artifact_prefix(landing: LandingConfig) -> str:
    parsed = urlparse(landing.url)
    path = parsed.path.strip("/") or "root"
    return _slugify(f"{landing.domain}_{path}")


def _capture_screenshot(page: Page, artifacts_dir: Path, name: str) -> None:
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts_dir / f"{name}.png"), full_page=True)
    except Exception:
        pass


def _build_row(
    landing: LandingConfig,
    tariff_name: str,
    click_url: str,
    page_load_status: str,
    http_status: str,
    final_url: str,
    error: str,
    card_number: str,
    transition_type: str,
    source_href: str,
    load_ms: str,
    environment: str,
    product_error: bool,
) -> ReportRow:
    return ReportRow(
        domain=landing.domain,
        checked_page_url=landing.url,
        tariff_name=tariff_name,
        click_url=click_url,
        page_load_status=page_load_status,
        http_status=http_status,
        final_url=final_url,
        error=error,
        checked_at=_timestamp(),
        operator=landing.operator,
        card_number=card_number,
        transition_type=transition_type,
        source_href=source_href,
        load_ms=load_ms,
        environment=environment,
        product_error=product_error,
    )


def _restore_landing(page: Page, landing: LandingConfig, timeout_ms: int) -> None:
    ok, _ = open_landing_page(page, landing.url, timeout_ms)
    if ok:
        close_common_popups(page, timeout_ms=min(timeout_ms, 2_000))


def _process_landing(
    page: Page,
    context,
    landing: LandingConfig,
    timeout_ms: int,
    environment: str,
    artifacts_dir: Path,
    screenshot_mode: str,
    artifact_prefix: str,
) -> list[ReportRow]:
    rows: list[ReportRow] = []

    opened, load_error = open_landing_page(page, landing.url, timeout_ms)
    if not opened:
        rows.append(
            _build_row(
                landing=landing,
                tariff_name="Название не определено",
                click_url="",
                page_load_status=STATUS_LOAD_ERROR,
                http_status="",
                final_url=(page.url or "").strip(),
                error=load_error,
                card_number="",
                transition_type="landing",
                source_href="",
                load_ms="0",
                environment=environment,
                product_error=True,
            )
        )
        if screenshot_mode != "off":
            _capture_screenshot(page, artifacts_dir, f"{artifact_prefix}_landing_open_failed")
        return rows

    close_common_popups(page, timeout_ms=min(timeout_ms, 2_000))

    cards = detect_cards(page, landing)
    if not cards:
        rows.append(
            _build_row(
                landing=landing,
                tariff_name="Название не определено",
                click_url="",
                page_load_status=STATUS_CARDS_NOT_FOUND,
                http_status="",
                final_url=(page.url or "").strip(),
                error="No visible tariff cards found",
                card_number="",
                transition_type="cards",
                source_href="",
                load_ms="0",
                environment=environment,
                product_error=True,
            )
        )
        if screenshot_mode != "off":
            _capture_screenshot(page, artifacts_dir, f"{artifact_prefix}_no_cards")
        return rows

    index = 0
    while index < len(cards):
        card = cards[index]
        cta = card.cta_locator
        title = card.title or "Название не определено"
        source_href = card.source_href

        if cta is None:
            rows.append(
                _build_row(
                    landing=landing,
                    tariff_name=title,
                    click_url="",
                    page_load_status=STATUS_BUTTON_NOT_FOUND,
                    http_status="",
                    final_url=(page.url or "").strip(),
                    error="CTA not found in card",
                    card_number=str(card.index),
                    transition_type="card",
                    source_href=source_href,
                    load_ms="0",
                    environment=environment,
                    product_error=True,
                )
            )
            if screenshot_mode != "off":
                _capture_screenshot(page, artifacts_dir, f"{artifact_prefix}_card_{card.index}_button_missing")
            index += 1
            continue

        click_result = click_card_cta(page, context, cta, timeout_ms)
        clicked_url = click_result.clicked_url
        error = click_result.error
        product_error = click_result.product_error
        load_ms = "0"
        http_status = ""
        final_url = ""
        page_load_status = click_result.status

        if clicked_url:
            availability = check_url_availability(context, clicked_url, timeout_ms)
            load_ms = str(availability.load_ms)
            http_status = availability.http_status
            final_url = availability.final_url
            page_load_status = availability.status
            error = availability.error or error
            product_error = availability.product_error or product_error
        else:
            final_url = ""
            if not error:
                error = STATUS_URL_NOT_OPENED

        rows.append(
            _build_row(
                landing=landing,
                tariff_name=title,
                click_url=clicked_url,
                page_load_status=page_load_status,
                http_status=http_status,
                final_url=final_url,
                error=_normalize_error(page_load_status, error),
                card_number=str(card.index),
                transition_type=click_result.transition_type,
                source_href=source_href,
                load_ms=load_ms,
                environment=environment,
                product_error=product_error,
            )
        )

        if screenshot_mode == "on" or (screenshot_mode == "only-on-failure" and product_error):
            safe_name = f"{artifact_prefix}_card_{card.index}_{click_result.transition_type}"
            _capture_screenshot(page, artifacts_dir, safe_name)

        if click_result.transition_type == "same_tab":
            _restore_landing(page, landing, timeout_ms)
            cards = detect_cards(page, landing)

        index += 1

    return rows


def test_partner_links_mobile(
    landing,
    browser_context,
    run_settings,
    report_sink,
) -> None:
    artifacts_dir = Path(run_settings.report_dir).parent / "artifacts"
    environment = run_settings.environment_label
    page = browser_context.new_page()
    artifact_prefix = _landing_artifact_prefix(landing)

    try:
        rows = _process_landing(
            page=page,
            context=browser_context,
            landing=landing,
            timeout_ms=run_settings.timeout_ms,
            environment=environment,
            artifacts_dir=artifacts_dir,
            screenshot_mode=run_settings.screenshot,
            artifact_prefix=artifact_prefix,
        )
        report_sink.rows.extend(rows)
    except Exception as exc:
        report_sink.rows.append(
            _build_row(
                landing=landing,
                tariff_name="Название не определено",
                click_url="",
                page_load_status=STATUS_LOAD_ERROR,
                http_status="",
                final_url=(page.url or "").strip(),
                error=f"{STATUS_LOAD_ERROR}: {exc}",
                card_number="",
                transition_type="landing",
                source_href="",
                load_ms="0",
                environment=environment,
                product_error=True,
            )
        )
        if run_settings.screenshot != "off":
            _capture_screenshot(page, artifacts_dir, f"{artifact_prefix}_infra_error")
        raise
    finally:
        try:
            page.close()
        except Exception:
            pass

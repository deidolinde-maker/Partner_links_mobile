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


class _FakePopupPage:
    def __init__(self, url: str = "about:blank") -> None:
        self._urls = [url]
        self._access_count = 0
        self.closed = False

    @property
    def url(self) -> str:
        index = min(self._access_count, len(self._urls) - 1)
        value = self._urls[index]
        self._access_count += 1
        return value

    def wait_for_load_state(self, *_args, **_kwargs) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class _FakePopupContext:
    def __init__(self, page: _FakePopupPage) -> None:
        self.pages = [page]


class _FakePopupLocator:
    def __init__(self, attributes: dict[str, str]) -> None:
        self._attributes = attributes
        self.clicked = False

    def get_attribute(self, name: str) -> str | None:
        return self._attributes.get(name)

    def scroll_into_view_if_needed(self, *_args, **_kwargs) -> None:
        return None

    def click(self, *_args, **_kwargs) -> None:
        self.clicked = True


def test_click_card_cta_uses_data_href_for_popup_button() -> None:
    page = _FakePopupPage()
    context = _FakePopupContext(page)
    cta = _FakePopupLocator(
        {
            "class": "card-new__button card-new__button--promocode button-mobile-application popup-promocode__trigger",
            "data-href": "https://t2.ru/tariffs?utm_source=webdealer&utm_medium=piter-online&utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2",
        }
    )

    result = click_card_cta(page, context, cta, timeout_ms=1_000)

    assert cta.clicked is True
    assert result.status == "Успешно"
    assert result.transition_type == "popup"
    assert result.clicked_url == "https://t2.ru/tariffs?utm_source=webdealer&utm_medium=piter-online&utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2"
    assert result.product_error is False


class _FakeDelayedPopupLocator(_FakePopupLocator):
    def __init__(self, attributes: dict[str, str], context: _FakePopupContext, popup_page: _FakePopupPage) -> None:
        super().__init__(attributes)
        self._context = context
        self._popup_page = popup_page

    def click(self, *_args, **_kwargs) -> None:
        self.clicked = True
        self._context.pages.append(self._popup_page)


def test_click_card_cta_waits_for_new_tab_url() -> None:
    main_page = _FakePopupPage("https://t2-ru.online/mobilnaya-svyaz")
    popup_page = _FakePopupPage()
    popup_page._urls = [
        "about:blank",
        "about:blank",
        "https://krasnodar.t2.ru/tariffs?utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2&utm_medium=piter-online&utm_source=webdealer&pageParams=askForRegion%3Dtrue",
    ]
    context = _FakePopupContext(main_page)
    cta = _FakeDelayedPopupLocator(
        {
            "class": "card-new__button button-mobile-application",
            "href": "https://t2.ru/tariffs?utm_source=webdealer&utm_medium=piter-online&utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2",
            "target": "_blank",
        },
        context=context,
        popup_page=popup_page,
    )

    result = click_card_cta(main_page, context, cta, timeout_ms=500)

    assert cta.clicked is True
    assert result.status == "Успешно"
    assert result.transition_type == "new_tab"
    assert result.clicked_url == "https://krasnodar.t2.ru/tariffs?utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2&utm_medium=piter-online&utm_source=webdealer&pageParams=askForRegion%3Dtrue"
    assert popup_page.closed is True


class _FakeAvailabilityResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class _FakeAvailabilityPage:
    def __init__(self, url: str, status: int) -> None:
        self.url = url
        self._status = status
        self.closed = False

    def on(self, *_args, **_kwargs) -> None:
        return None

    def goto(self, *_args, **_kwargs) -> _FakeAvailabilityResponse:
        return _FakeAvailabilityResponse(self._status)

    def wait_for_load_state(self, *_args, **_kwargs) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class _FakeAvailabilityContext:
    def __init__(self, page: _FakeAvailabilityPage) -> None:
        self._page = page

    def new_page(self) -> _FakeAvailabilityPage:
        return self._page


def test_check_url_availability_treats_t2_503_as_ok() -> None:
    from src.availability_checker import check_url_availability

    page = _FakeAvailabilityPage(
        url="https://t2.ru/tariffs?utm_source=webdealer&utm_medium=piter-online&utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2",
        status=503,
    )
    context = _FakeAvailabilityContext(page)

    result = check_url_availability(
        context,
        "https://t2.ru/tariffs?utm_source=webdealer&utm_medium=piter-online&utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2",
        timeout_ms=1_000,
    )

    assert result.status == "Успешно"
    assert result.http_status == "503"
    assert page.closed is True

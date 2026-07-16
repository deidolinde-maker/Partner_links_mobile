from __future__ import annotations

from contextlib import contextmanager
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
    STATUS_OK,
    STATUS_LOAD_ERROR,
    STATUS_URL_NOT_OPENED,
)
from src.page_loader import open_landing_page
from src.popup_handler import close_common_popups
from src.tariff_parser import detect_cards
from config.landings import LANDINGS


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


def _wait_for_card_shell(page: Page, landing: LandingConfig, timeout_ms: int) -> None:
    selector = ", ".join(landing.card_selectors)
    try:
        page.wait_for_selector(selector, state="visible", timeout=min(timeout_ms, 7_000))
    except Exception:
        pass


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
    click_timeout_ms = landing.click_timeout_ms or timeout_ms

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
    _wait_for_card_shell(page, landing, timeout_ms)

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

        click_result = click_card_cta(page, context, cta, click_timeout_ms)
        clicked_url = click_result.clicked_url
        error = click_result.error
        product_error = click_result.product_error
        load_ms = "0"
        http_status = ""
        final_url = ""
        page_load_status = click_result.status

        if clicked_url:
            availability = check_url_availability(context, clicked_url, click_timeout_ms)
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


class _FakeAvailabilityResponse:
    def __init__(self, status: int):
        self.status = status


class _FakeAvailabilityPage:
    def __init__(self, final_url: str, status: int, page_error: str | None = None):
        self.url = "about:blank"
        self._final_url = final_url
        self._response = _FakeAvailabilityResponse(status)
        self._page_error = page_error
        self._pageerror_handler = None

    def on(self, event: str, handler):
        if event == "pageerror":
            self._pageerror_handler = handler

    def goto(self, url: str, wait_until: str, timeout: int):
        self.url = self._final_url
        if self._page_error and self._pageerror_handler is not None:
            self._pageerror_handler(RuntimeError(self._page_error))
        return self._response

    def wait_for_load_state(self, state: str, timeout: int):
        return None

    def close(self):
        return None


class _FakeAvailabilityContext:
    def __init__(self, page: _FakeAvailabilityPage):
        self._page = page

    def new_page(self):
        return self._page


class _FakeCardNode:
    def __init__(
        self,
        *,
        text: str = "",
        href: str = "",
        visible: bool = True,
        box: dict[str, float] | None = None,
        selector_map: dict[str, list["_FakeCardNode"]] | None = None,
    ):
        self._text = text
        self._href = href
        self._visible = visible
        self._box = box or {"x": 0.0, "y": 0.0, "width": 100.0, "height": 100.0}
        self._selector_map = selector_map or {}

    def locator(self, selector: str):
        return _FakeCardLocator(self._selector_map.get(selector, []))

    def is_visible(self):
        return self._visible

    def inner_text(self, timeout: int = 0):
        return self._text

    def get_attribute(self, name: str):
        if name == "href":
            return self._href
        return None

    def bounding_box(self):
        return self._box


class _FakeCardLocator:
    def __init__(self, nodes: list[_FakeCardNode]):
        self._nodes = nodes

    def all(self):
        return self._nodes


class _FakeCardPage:
    def __init__(self, cards: list[_FakeCardNode]):
        self._cards = cards

    def locator(self, selector: str):
        if selector in {
            ".card-block",
            ".card-block__body",
            ".card-block[class*=' T']",
            ".tariff-block.uc-BLOCK-MOBILE-1 .card-block",
        }:
            return _FakeCardLocator(self._cards)
        return _FakeCardLocator([])


class _FakePopupPage:
    def __init__(self, final_url: str):
        self.url = "about:blank"
        self._final_url = final_url
        self.closed = False

    def wait_for_url(self, predicate, timeout: int):
        self.url = self._final_url
        return None

    def wait_for_load_state(self, state: str, timeout: int):
        return None

    def close(self):
        self.closed = True


class _FakePopupPageHost:
    def __init__(self, popup_page: _FakePopupPage):
        self.url = "https://t2-ru.online/mobilnaya-svyaz"
        self._popup_page = popup_page

    @contextmanager
    def expect_popup(self, timeout: int):
        class _PopupInfo:
            def __init__(self, value):
                self.value = value

        yield _PopupInfo(self._popup_page)


class _FakePopupContext:
    def __init__(self, page: _FakePopupPageHost):
        self.pages = [page]


class _FakePopupLocator:
    def __init__(self, href: str, target: str = "_blank"):
        self._href = href
        self._target = target

    def get_attribute(self, name: str):
        if name == "href":
            return self._href
        if name == "target":
            return self._target
        return None

    def scroll_into_view_if_needed(self, timeout: int):
        return None

    def click(self, timeout: int):
        return None


def test_detect_cards_prefers_beeline_connect_link_over_hidden_button() -> None:
    landing = next(
        item
        for item in LANDINGS
        if item.operator == "Beeline" and item.domain == "beeline-internet.online" and item.url.endswith("/tariffs-mobile")
    )

    title_node = _FakeCardNode(text="bee HIT")
    connect_link = _FakeCardNode(
        href="https://beeline.ru/customers/products/toptariffs/?utm_source=mobideal&utm_medium=cpa&utm_campaign=landing",
        text="Подключить",
    )
    hidden_button = _FakeCardNode(
        href="",
        text="Подключить",
        visible=False,
    )
    card = _FakeCardNode(
        text="bee HIT Подключить",
        selector_map={
            ".card-block__header-main [itemprop='name']": [title_node],
            ".card-block__header-main .card-block__title": [title_node],
            ".card-block__header [itemprop='name']": [title_node],
            ".card-block__header .card-block__title": [title_node],
            ".card-block__header": [title_node],
            "[itemprop='name'].card-block__title": [title_node],
            ".card-block__title": [title_node],
            "[itemprop='name']": [title_node],
            "[class*='title']": [title_node],
            "[class*='name']": [title_node],
            "[class*='tariff']": [title_node],
            ".card-block__button.button-mobile-application.popup-mobile-beeline": [connect_link],
            ".card-block__button.button-mobile-application": [connect_link],
            ".card-block__button": [connect_link, hidden_button],
            "a.card-block__button.button-mobile-application": [connect_link],
            "a[href]": [connect_link],
            "button": [hidden_button],
        },
    )

    cards = detect_cards(_FakeCardPage([card]), landing)

    assert len(cards) == 1
    assert cards[0].title == "bee HIT"
    assert cards[0].source_href == "https://beeline.ru/customers/products/toptariffs/?utm_source=mobideal&utm_medium=cpa&utm_campaign=landing"


def test_click_card_cta_uses_new_tab_for_target_blank_links() -> None:
    popup_page = _FakePopupPage(
        final_url="https://krasnodar.t2.ru/tariffs?utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2&utm_medium=piter-online&utm_source=webdealer&pageParams=askForRegion%3Dtrue"
    )
    page = _FakePopupPageHost(popup_page)
    context = _FakePopupContext(page)
    cta = _FakePopupLocator(
        href="https://t2.ru/tariffs?utm_source=webdealer&utm_medium=piter-online&utm_campaign=tariffs_webdealer_ooo_online_services_piter-online_operatory_t2"
    )

    result = click_card_cta(page, context, cta, timeout_ms=20_000)

    assert result.status == "Успешно"
    assert result.transition_type == "new_tab"
    assert result.clicked_url == popup_page.url
    assert result.clicked_url.startswith("https://krasnodar.t2.ru/tariffs")


def test_detect_cards_supports_beeline_body_card_container() -> None:
    landing = next(
        item
        for item in LANDINGS
        if item.operator == "Beeline" and item.domain == "beeline-internet.online" and item.url.endswith("/tariffs-mobile")
    )

    title_node = _FakeCardNode(text="bee SUPER START")
    connect_link = _FakeCardNode(
        href="https://beeline.ru/customers/products/toptariffs/?utm_source=mobideal&utm_medium=cpa&utm_campaign=landing",
        text="Подключить",
    )
    card = _FakeCardNode(
        text="bee SUPER START Подключить",
        selector_map={
            ".card-block__header-main [itemprop='name']": [title_node],
            ".card-block__header-main .card-block__title": [title_node],
            ".card-block__header [itemprop='name']": [title_node],
            ".card-block__header .card-block__title": [title_node],
            ".card-block__header": [title_node],
            "[itemprop='name'].card-block__title": [title_node],
            ".card-block__title": [title_node],
            "[itemprop='name']": [title_node],
            "[class*='title']": [title_node],
            "[class*='name']": [title_node],
            "[class*='tariff']": [title_node],
            ".card-block__button.button-mobile-application.popup-mobile-beeline": [connect_link],
            ".card-block__button.button-mobile-application": [connect_link],
            ".card-block__button": [connect_link],
            "a.card-block__button.button-mobile-application": [connect_link],
            "a[href]": [connect_link],
            "button": [connect_link],
        },
    )

    cards = detect_cards(_FakeCardPage([card]), landing)

    assert len(cards) == 1
    assert cards[0].title == "bee SUPER START"
    assert cards[0].source_href == "https://beeline.ru/customers/products/toptariffs/?utm_source=mobideal&utm_medium=cpa&utm_campaign=landing"


def test_check_url_availability_treats_t2_503_as_success() -> None:
    page = _FakeAvailabilityPage(
        final_url="https://spb.t2.ru/promo/partner-all?utm_campaign=partner_m_webdealer_ooo_online_services_t2-ru_online&utm_medium=t2-ru_online&utm_source=webdealer&pageParams=askForRegion%3Dtrue",
        status=503,
    )
    context = _FakeAvailabilityContext(page)

    result = check_url_availability(
        context,
        "https://t2.ru/promo/partner-all?utm_source=webdealer&utm_medium=t2-ru_online&utm_campaign=partner_m_webdealer_ooo_online_services_t2-ru_online",
        timeout_ms=1000,
    )

    assert result.status == STATUS_OK
    assert result.http_status == "503"
    assert result.final_url.startswith("https://spb.t2.ru/promo/partner-all")


def test_check_url_availability_ignores_beeline_js_errors() -> None:
    page = _FakeAvailabilityPage(
        final_url="https://moskva.beeline.ru/customers/products/toptariffs/?utm_source=mobideal&utm_medium=cpa&utm_campaign=landing",
        status=200,
        page_error="ReferenceError: banner is not defined",
    )
    context = _FakeAvailabilityContext(page)

    result = check_url_availability(
        context,
        "https://beeline-internet.online/tariffs-mobile",
        timeout_ms=1000,
    )

    assert result.status == STATUS_OK
    assert result.error == ""


def test_check_url_availability_reports_js_error_for_other_domains() -> None:
    page = _FakeAvailabilityPage(
        final_url="https://moskva.mts.ru/personal/mobilnaya-svyaz/tarifi/vse-tarifi/red/?utm_source=mtspn&utm_medium=cpa&utm_content=",
        status=200,
        page_error="ReferenceError: banner is not defined",
    )
    context = _FakeAvailabilityContext(page)

    result = check_url_availability(
        context,
        "https://mts-home.online/mobilnaya-svyaz",
        timeout_ms=1000,
    )

    assert result.status == "JS error"
    assert result.error == "ReferenceError: banner is not defined"

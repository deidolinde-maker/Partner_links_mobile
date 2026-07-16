from __future__ import annotations

import time

from playwright.sync_api import BrowserContext, Error, Locator, Page, TimeoutError as PlaywrightTimeoutError

from src.models import ClickResult, STATUS_BUTTON_NOT_CLICKABLE, STATUS_URL_NOT_OPENED


def _safe_attr(locator: Locator | None, attr: str) -> str:
    if locator is None:
        return ""
    try:
        return (locator.get_attribute(attr) or "").strip()
    except Exception:
        return ""


def _safe_target_url(locator: Locator | None) -> str:
    for attr in ("href", "data-href", "data-url"):
        value = _safe_attr(locator, attr)
        if value:
            return value
    return ""


def _wait_for_new_page(context: BrowserContext, before_pages: set[Page], timeout_ms: int) -> Page | None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        extra_pages = [candidate for candidate in context.pages if candidate not in before_pages]
        if extra_pages:
            return extra_pages[-1]
        time.sleep(0.1)
    return None


def _wait_for_destination_page(
    context: BrowserContext,
    before_pages: set[Page],
    before_url: str,
    timeout_ms: int,
) -> Page | None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        pages = list(context.pages)

        for candidate in reversed(pages):
            if candidate in before_pages:
                continue
            current_url = (candidate.url or "").strip()
            if current_url and current_url != "about:blank" and current_url != before_url:
                return candidate

        for candidate in reversed(pages):
            if candidate not in before_pages:
                continue
            current_url = (candidate.url or "").strip()
            if current_url and current_url != "about:blank" and current_url != before_url:
                return candidate

        time.sleep(0.1)
    return None


def click_card_cta(
    page: Page,
    context: BrowserContext,
    cta: Locator | None,
    timeout_ms: int,
) -> ClickResult:
    source_href = _safe_target_url(cta)
    target_blank = _safe_attr(cta, "target").lower() == "_blank"
    data_href = _safe_attr(cta, "data-href")

    if cta is None:
        return ClickResult(
            status=STATUS_BUTTON_NOT_CLICKABLE,
            error="CTA not found",
            clicked_url="",
            transition_type="none",
            source_href=source_href,
            product_error=True,
        )

    try:
        cta.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass

    before_url = page.url
    before_pages = set(context.pages)
    destination_page = None

    try:
        cta.click(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        destination_page = _wait_for_destination_page(context, before_pages, before_url, timeout_ms)
    except Error as exc:
        return ClickResult(
            status=STATUS_BUTTON_NOT_CLICKABLE,
            error=str(exc),
            clicked_url="",
            transition_type="none",
            source_href=source_href,
            product_error=True,
        )

    if destination_page is None:
        destination_page = _wait_for_destination_page(context, before_pages, before_url, timeout_ms)

    if destination_page is None and target_blank and source_href:
        return ClickResult(
            status="Успешно",
            error="",
            clicked_url=source_href,
            transition_type="new_tab",
            source_href=source_href,
            product_error=False,
        )

    if destination_page is None and data_href:
        return ClickResult(
            status="Успешно",
            error="",
            clicked_url=data_href,
            transition_type="popup",
            source_href=source_href,
            product_error=False,
        )

    if destination_page is not None:
        try:
            destination_page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        clicked_url = (destination_page.url or "").strip()
        try:
            if destination_page is not page:
                destination_page.close()
        except Exception:
            pass
        if not clicked_url:
            return ClickResult(
                status=STATUS_URL_NOT_OPENED,
                error="New tab opened without URL",
                clicked_url="",
                transition_type="new_tab" if destination_page is not page else "same_tab",
                source_href=source_href,
                product_error=True,
            )
        return ClickResult(
            status="Успешно",
            error="",
            clicked_url=clicked_url,
            transition_type="new_tab" if destination_page is not page else "same_tab",
            source_href=source_href,
            product_error=False,
        )

    try:
        page.wait_for_load_state("domcontentloaded", timeout=min(timeout_ms, 3_000))
    except Exception:
        pass

    after_url = (page.url or "").strip()
    if after_url and after_url != before_url:
        return ClickResult(
            status="Успешно",
            error="",
            clicked_url=after_url,
            transition_type="same_tab",
            source_href=source_href,
            product_error=False,
        )

    return ClickResult(
        status=STATUS_URL_NOT_OPENED,
        error="No navigation after click",
        clicked_url="",
        transition_type="none",
        source_href=source_href,
        product_error=True,
    )

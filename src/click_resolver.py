from __future__ import annotations

import time

from playwright.sync_api import BrowserContext, Error, Locator, Page, TimeoutError as PlaywrightTimeoutError

from src.models import ClickResult, STATUS_BUTTON_NOT_CLICKABLE, STATUS_URL_NOT_OPENED


def _safe_href(locator: Locator | None) -> str:
    if locator is None:
        return ""
    try:
        return (locator.get_attribute("href") or "").strip()
    except Exception:
        return ""


def _safe_attr(locator: Locator | None, name: str) -> str:
    if locator is None:
        return ""
    try:
        return (locator.get_attribute(name) or "").strip()
    except Exception:
        return ""


def _nav_wait_ms(timeout_ms: int, target_blank: bool) -> int:
    if target_blank:
        return timeout_ms
    return min(timeout_ms, 10_000)


def _page_wait_ms(timeout_ms: int, target_blank: bool) -> int:
    if target_blank:
        return timeout_ms
    return min(timeout_ms, 5_000)


def _wait_for_new_page(context: BrowserContext, before_pages: set[Page], timeout_ms: int) -> Page | None:
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        extra_pages = [candidate for candidate in context.pages if candidate not in before_pages]
        if extra_pages:
            return extra_pages[-1]
        time.sleep(0.2)
    extra_pages = [candidate for candidate in context.pages if candidate not in before_pages]
    return extra_pages[-1] if extra_pages else None


def click_card_cta(
    page: Page,
    context: BrowserContext,
    cta: Locator | None,
    timeout_ms: int,
) -> ClickResult:
    source_href = _safe_href(cta)

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

    target_blank = _safe_attr(cta, "target").lower() == "_blank"
    before_url = page.url
    before_pages = set(context.pages)
    new_page = None
    nav_wait_ms = _nav_wait_ms(timeout_ms, target_blank)
    page_wait_ms = _page_wait_ms(timeout_ms, target_blank)

    try:
        expect_popup = page.expect_popup if target_blank else context.expect_page
        with expect_popup(timeout=page_wait_ms) as new_page_info:
            cta.click(timeout=timeout_ms)
        new_page = new_page_info.value
    except PlaywrightTimeoutError:
        new_page = _wait_for_new_page(context, before_pages, nav_wait_ms)
    except Error as exc:
        return ClickResult(
            status=STATUS_BUTTON_NOT_CLICKABLE,
            error=str(exc),
            clicked_url="",
            transition_type="none",
            source_href=source_href,
            product_error=True,
        )

    if new_page is not None:
        try:
            new_page.wait_for_url(
                lambda current_url: bool(current_url.strip()) and current_url.strip() != "about:blank",
                timeout=nav_wait_ms,
            )
        except Exception:
            pass
        try:
            new_page.wait_for_load_state("domcontentloaded", timeout=nav_wait_ms)
        except Exception:
            pass
        clicked_url = (new_page.url or "").strip()
        try:
            new_page.close()
        except Exception:
            pass
        if not clicked_url:
            return ClickResult(
                status=STATUS_URL_NOT_OPENED,
                error="New tab opened without URL",
                clicked_url="",
                transition_type="new_tab",
                source_href=source_href,
                product_error=True,
            )
        return ClickResult(
            status="Успешно",
            error="",
            clicked_url=clicked_url,
            transition_type="new_tab",
            source_href=source_href,
            product_error=False,
        )

    try:
        page.wait_for_url(
            lambda current_url: bool(current_url.strip())
            and current_url.strip() != before_url
            and current_url.strip() != "about:blank",
            timeout=nav_wait_ms,
        )
    except Exception:
        pass

    try:
        page.wait_for_load_state("domcontentloaded", timeout=nav_wait_ms)
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

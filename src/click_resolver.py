from __future__ import annotations

from playwright.sync_api import BrowserContext, Error, Locator, Page, TimeoutError as PlaywrightTimeoutError

from src.models import ClickResult, STATUS_BUTTON_NOT_CLICKABLE, STATUS_URL_NOT_OPENED


def _safe_href(locator: Locator | None) -> str:
    if locator is None:
        return ""
    try:
        return (locator.get_attribute("href") or "").strip()
    except Exception:
        return ""


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

    before_url = page.url
    before_pages = set(context.pages)
    new_page = None

    try:
        with context.expect_page(timeout=min(timeout_ms, 1_500)) as new_page_info:
            cta.click(timeout=timeout_ms)
        new_page = new_page_info.value
    except PlaywrightTimeoutError:
        extra_pages = [candidate for candidate in context.pages if candidate not in before_pages]
        if extra_pages:
            new_page = extra_pages[-1]
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
            new_page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
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


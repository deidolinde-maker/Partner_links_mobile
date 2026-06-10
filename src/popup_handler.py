from __future__ import annotations

from playwright.sync_api import Page


POPUP_CLOSE_SELECTORS = (
    "#cookieAccept",
    "#yesButton",
    ".popup__close",
    ".modal__close",
    "button[aria-label*='close' i]",
    "button[title*='close' i]",
)

COOKIE_ACCEPT_SELECTORS = (
    "button:has-text('Принять')",
    "button:has-text('Соглас')",
    "#cookieAccept",
)


def _click_first_visible(page: Page, selectors: tuple[str, ...], timeout_ms: int) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if not locator.count():
                continue
            if not locator.is_visible():
                continue
            locator.click(timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def close_common_popups(page: Page, timeout_ms: int = 2_000) -> None:
    _click_first_visible(page, POPUP_CLOSE_SELECTORS, timeout_ms)
    _click_first_visible(page, COOKIE_ACCEPT_SELECTORS, timeout_ms)
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


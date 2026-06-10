from __future__ import annotations

from playwright.sync_api import Error, Page, TimeoutError as PlaywrightTimeoutError


def open_landing_page(page: Page, url: str, timeout_ms: int) -> tuple[bool, str]:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        return True, ""
    except PlaywrightTimeoutError as exc:
        return False, f"Timeout: {exc}"
    except Error as exc:
        return False, f"Browser error: {exc}"

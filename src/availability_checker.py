from __future__ import annotations

from time import perf_counter

from playwright.sync_api import BrowserContext, Error, Page, TimeoutError as PlaywrightTimeoutError

from src.models import (
    AvailabilityResult,
    STATUS_ABOUT_BLANK,
    STATUS_BROWSER_ERROR,
    STATUS_EMPTY_URL,
    STATUS_HTTP_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
)


def check_url_availability(
    context: BrowserContext,
    url: str,
    timeout_ms: int,
) -> AvailabilityResult:
    clean_url = (url or "").strip()
    if not clean_url:
        return AvailabilityResult(
            url=url,
            final_url="",
            http_status="",
            status=STATUS_EMPTY_URL,
            error="Empty URL",
            load_ms=0,
        )
    if clean_url == "about:blank":
        return AvailabilityResult(
            url=url,
            final_url="about:blank",
            http_status="",
            status=STATUS_ABOUT_BLANK,
            error="about:blank",
            load_ms=0,
        )

    page = context.new_page()
    captured_errors: list[str] = []
    page.on("pageerror", lambda exc: captured_errors.append(str(exc)))
    start = perf_counter()
    try:
        response = page.goto(clean_url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 10_000))
        except Exception:
            pass
        load_ms = int((perf_counter() - start) * 1000)
        final_url = (page.url or "").strip()
        http_status = str(response.status) if response is not None else ""

        if final_url == "about:blank":
            return AvailabilityResult(
                url=clean_url,
                final_url=final_url,
                http_status=http_status,
                status=STATUS_ABOUT_BLANK,
                error="Final URL is about:blank",
                load_ms=load_ms,
            )

        if response is not None and response.status >= 400:
            return AvailabilityResult(
                url=clean_url,
                final_url=final_url,
                http_status=http_status,
                status=STATUS_HTTP_ERROR,
                error=f"HTTP {response.status}",
                load_ms=load_ms,
            )

        if captured_errors:
            return AvailabilityResult(
                url=clean_url,
                final_url=final_url,
                http_status=http_status,
                status="JS error",
                error=captured_errors[0],
                load_ms=load_ms,
            )

        return AvailabilityResult(
            url=clean_url,
            final_url=final_url,
            http_status=http_status,
            status=STATUS_OK,
            error="",
            load_ms=load_ms,
        )
    except PlaywrightTimeoutError as exc:
        load_ms = int((perf_counter() - start) * 1000)
        return AvailabilityResult(
            url=clean_url,
            final_url=(page.url or "").strip(),
            http_status="",
            status=STATUS_TIMEOUT,
            error=str(exc),
            load_ms=load_ms,
        )
    except Error as exc:
        load_ms = int((perf_counter() - start) * 1000)
        return AvailabilityResult(
            url=clean_url,
            final_url=(page.url or "").strip(),
            http_status="",
            status=STATUS_BROWSER_ERROR,
            error=str(exc),
            load_ms=load_ms,
        )
    finally:
        page.close()


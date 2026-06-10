from __future__ import annotations

import re
from typing import Iterable

from playwright.sync_api import Locator, Page

from config.landings import LandingConfig
from src.models import DetectedCard


ROOT_FALLBACK_SELECTORS = (
    "article",
    "[class*='card']",
    "[class*='tariff']",
    "[class*='plan']",
    "[class*='offer']",
)

NON_TITLE_TEXTS = {
    "подключить",
    "подключение",
    "buy",
    "купить",
    "узнать больше",
    "выбрать",
    "заказать",
}


def _unique_key(locator: Locator, selector: str) -> str:
    try:
        box = locator.bounding_box() or {}
    except Exception:
        box = {}
    try:
        text = (locator.inner_text(timeout=250) or "").strip()
    except Exception:
        text = ""
    try:
        href = (locator.get_attribute("href") or "").strip()
    except Exception:
        href = ""
    return "|".join(
        [
            href,
            text[:120],
            str(round(float(box.get("x", 0.0)), 1)),
            str(round(float(box.get("y", 0.0)), 1)),
            str(round(float(box.get("width", 0.0)), 1)),
            str(round(float(box.get("height", 0.0)), 1)),
        ]
    )


def _is_visible(locator: Locator) -> bool:
    try:
        return locator.is_visible()
    except Exception:
        return False


def _first_visible_descendant(container: Locator, selectors: Iterable[str]) -> Locator | None:
    for selector in selectors:
        try:
            matches = container.locator(selector).all()
        except Exception:
            continue
        for match in matches:
            if _is_visible(match):
                return match
    return None


def _extract_title(container: Locator, fallback_selectors: Iterable[str]) -> str:
    for selector in fallback_selectors:
        try:
            matches = container.locator(selector).all()
        except Exception:
            continue
        for match in matches:
            if not _is_visible(match):
                continue
            try:
                text = (match.inner_text(timeout=250) or "").strip()
            except Exception:
                text = ""
            if text:
                return text

    try:
        text = (container.inner_text(timeout=250) or "").strip()
    except Exception:
        text = ""
    if text:
        for line in re.split(r"[\r\n]+", text):
            candidate = line.strip()
            if candidate and len(candidate) > 2 and candidate.lower() not in NON_TITLE_TEXTS:
                return candidate
    return "Название не определено"


def detect_cards(page: Page, landing: LandingConfig) -> list[DetectedCard]:
    seen: set[str] = set()
    detected: list[DetectedCard] = []

    def _collect(selectors: Iterable[str]) -> None:
        for selector in selectors:
            try:
                candidates = page.locator(selector).all()
            except Exception:
                continue
            for candidate in candidates:
                if not _is_visible(candidate):
                    continue
                key = _unique_key(candidate, selector)
                if key in seen:
                    continue
                seen.add(key)

                title = _extract_title(candidate, landing.title_selectors)
                cta = _first_visible_descendant(candidate, landing.cta_selectors)
                if cta is None and _is_visible(candidate):
                    cta = candidate

                source_href = ""
                for probe in (cta, candidate):
                    if probe is None:
                        continue
                    try:
                        source_href = (probe.get_attribute("href") or "").strip()
                    except Exception:
                        source_href = ""
                    if source_href:
                        break

                detected.append(
                    DetectedCard(
                        index=len(detected) + 1,
                        locator=candidate,
                        cta_locator=cta,
                        title=title,
                        source_selector=selector,
                        source_href=source_href,
                    )
                )

    _collect(landing.card_selectors)
    if not detected:
        _collect(ROOT_FALLBACK_SELECTORS)

    return detected

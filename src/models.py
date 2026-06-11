from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STATUS_OK = "Успешно"
STATUS_CARDS_NOT_FOUND = "Карточки не найдены"
STATUS_BUTTON_NOT_FOUND = "Кнопка не найдена"
STATUS_BUTTON_NOT_CLICKABLE = "Кнопка не кликабельна"
STATUS_URL_NOT_OPENED = "URL не открылся"
STATUS_EMPTY_URL = "Пустой URL"
STATUS_ABOUT_BLANK = "about:blank"
STATUS_LOAD_ERROR = "Ошибка загрузки"
STATUS_HTTP_ERROR = "HTTP error"
STATUS_TIMEOUT = "Timeout"
STATUS_BROWSER_ERROR = "Browser error"
STATUS_JS_ERROR = "JS error"
STATUS_UNKNOWN_ERROR = "Unknown error"


@dataclass(frozen=True, slots=True)
class RunSettings:
    target: str
    domain: str | None
    url: str | None
    run_mode: str
    headed: bool
    timeout_ms: int
    report_dir: str
    trace: str
    screenshot: str

    @property
    def environment_label(self) -> str:
        mode = "headed" if self.headed else "headless"
        return (
            f"run_mode={self.run_mode}; target={self.target}; "
            f"browser={mode}; trace={self.trace}; screenshot={self.screenshot}"
        )


@dataclass(slots=True)
class DetectedCard:
    index: int
    locator: Any
    cta_locator: Any | None
    title: str
    source_selector: str
    source_href: str


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    url: str
    final_url: str
    http_status: str
    status: str
    error: str
    load_ms: int

    @property
    def product_error(self) -> bool:
        return self.status not in {STATUS_OK, STATUS_JS_ERROR}


@dataclass(frozen=True, slots=True)
class ReportRow:
    domain: str
    checked_page_url: str
    tariff_name: str
    click_url: str
    page_load_status: str
    http_status: str
    final_url: str
    error: str
    checked_at: str
    operator: str = ""
    card_number: str = ""
    transition_type: str = ""
    source_href: str = ""
    load_ms: str = ""
    environment: str = ""
    product_error: bool = False


@dataclass(frozen=True, slots=True)
class RunSummary:
    total_rows: int
    product_error_rows: int
    successful_rows: int
    report_path: str
    run_mode: str


@dataclass(frozen=True, slots=True)
class ClickResult:
    status: str
    error: str
    clicked_url: str
    transition_type: str
    source_href: str
    product_error: bool

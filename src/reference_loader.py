from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from openpyxl import load_workbook

from src.models import ReferenceLink


_WHITESPACE_RE = re.compile(r"\s+")
_ALIAS_SPLIT_RE = re.compile(r"[;\n,|]+")


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_domain(value: object) -> str:
    text = normalize_text(value).lower()
    if not text:
        return ""

    parsed = urlsplit(text if "://" in text else f"https://{text}")
    host = parsed.netloc or parsed.path
    host = host.split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    return host.strip().lower()


def normalize_page_url(value: object) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    parsed = urlsplit(text if "://" in text else f"https://{text}")
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def normalize_tariff_name(value: object) -> str:
    return normalize_text(value).lower()


def split_aliases(value: object) -> tuple[str, ...]:
    text = normalize_text(value)
    if not text:
        return ()
    aliases = [normalize_text(part) for part in _ALIAS_SPLIT_RE.split(text)]
    return tuple(alias for alias in aliases if alias)


def parse_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = normalize_text(value).lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "да", "on"}:
        return True
    if text in {"0", "false", "no", "n", "нет", "off"}:
        return False
    return default


def _normalize_header(value: object) -> str:
    return normalize_text(value).lower()


def _header_map(headers: Iterable[object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, header in enumerate(headers):
        key = _normalize_header(header)
        if key and key not in result:
            result[key] = index
    return result


def _first_header_index(header_map: dict[str, int], aliases: tuple[str, ...]) -> int | None:
    for alias in aliases:
        index = header_map.get(_normalize_header(alias))
        if index is not None:
            return index
    return None


def _load_xlsx_rows(path: Path) -> list[tuple[object, ...]]:
    workbook = load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    return [tuple(row) for row in sheet.iter_rows(values_only=True)]


def _load_csv_rows(path: Path) -> list[tuple[object, ...]]:
    encodings = ("utf-8-sig", "utf-8", "cp1251")
    raw_text = None
    for encoding in encodings:
        try:
            raw_text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if raw_text is None:
        raw_text = path.read_text(encoding="utf-8", errors="replace")

    sample = raw_text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.get_dialect("excel")

    reader = csv.reader(raw_text.splitlines(), dialect)
    return [tuple(row) for row in reader]


def _build_reference_link(
    header_map: dict[str, int],
    row: tuple[object, ...],
    row_number: int,
) -> ReferenceLink | None:
    def get_cell(*aliases: str, default: object = "") -> object:
        index = _first_header_index(header_map, aliases)
        if index is None or index >= len(row):
            return default
        value = row[index]
        return default if value is None else value

    active = parse_bool(get_cell("Активен", "Active"), default=True)
    if not active:
        return None

    domain = normalize_domain(get_cell("Домен", "Domain"))
    page_url = normalize_page_url(get_cell("URL проверяемой страницы", "Page URL", "URL", "page_url"))
    tariff_name = normalize_tariff_name(get_cell("Название тарифа", "Tariff Name", "tariff_name"))
    expected_url_part = normalize_text(
        get_cell("Эталонная часть ссылки", "Expected URL Part", "Expected Part", "expected_url_part")
    )
    match_type = normalize_text(get_cell("Тип сравнения", "Match Type", "match_type")) or "contains"
    comment = normalize_text(get_cell("Комментарий", "Comment", "comment"))
    aliases = split_aliases(get_cell("Алиасы тарифа", "Tariff Aliases", "Aliases", "aliases"))

    if not domain:
        raise ValueError(f"Row {row_number}: domain is required")
    if not tariff_name:
        raise ValueError(f"Row {row_number}: tariff name is required")
    if not expected_url_part:
        raise ValueError(f"Row {row_number}: expected URL part is required")
    if match_type not in {"contains", "regex"}:
        raise ValueError(f"Row {row_number}: unsupported match type {match_type!r}")

    return ReferenceLink(
        domain=domain,
        page_url=page_url,
        tariff_name=tariff_name,
        expected_url_part=expected_url_part,
        match_type=match_type,
        comment=comment,
        active=active,
        aliases=aliases,
    )


def load_reference_links(reference_file: str | Path) -> list[ReferenceLink]:
    path = Path(reference_file)
    if not path.exists():
        raise FileNotFoundError(f"Reference file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        rows = _load_xlsx_rows(path)
    elif suffix == ".csv":
        rows = _load_csv_rows(path)
    else:
        raise ValueError(f"Unsupported reference file format: {path.suffix}")

    if not rows:
        return []

    header_map = _header_map(rows[0])
    parsed: list[ReferenceLink] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(cell is not None and normalize_text(cell) for cell in row):
            continue
        reference = _build_reference_link(header_map, row, row_number)
        if reference is not None:
            parsed.append(reference)

    return parsed

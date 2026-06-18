from __future__ import annotations

import re
from dataclasses import dataclass, replace
from urllib.parse import unquote
from urllib.parse import urlsplit

from src.reference_loader import (
    normalize_domain,
    normalize_tariff_name,
    normalize_text,
)
from src.models import (
    ReferenceLink,
    ReportRow,
    VALIDATION_STATUS_NO_FACTUAL_LINK,
    VALIDATION_STATUS_NO_REFERENCE,
    VALIDATION_STATUS_NOT_OK,
    VALIDATION_STATUS_OK,
)

# Landing numbers change between runs, so we compare the stable part only.
_LANDING_NUMBER_RE = re.compile("(\u041b\u0435\u043d\u0434\u0438\u043d\u0433\\s*)\\d+", re.IGNORECASE)


def _url_variants(value: object) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []

    variants = [text]
    for _ in range(2):
        decoded = unquote(variants[-1])
        if decoded == variants[-1]:
            break
        variants.append(decoded)

    unique: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        cleaned = normalize_text(variant)
        if not cleaned:
            continue

        for normalized_variant in (cleaned, _LANDING_NUMBER_RE.sub(r"\1", cleaned)):
            if normalized_variant and normalized_variant not in seen:
                seen.add(normalized_variant)
                unique.append(normalized_variant)
    return unique


def _normalize_page_url_key(value: object) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    # Regional subdomains should not split the same landing into different keys.
    url_match = re.search(r"https?://\S+", text, re.IGNORECASE)
    candidate = url_match.group(0) if url_match is not None else text
    parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
    path = parsed.path.rstrip("/") or parsed.path
    if not path or path == "/":
        return ""
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def build_lookup_key(domain: object, page_url: object, tariff_name: object) -> str:
    domain_part = normalize_domain(domain)
    page_part = _normalize_page_url_key(page_url)
    tariff_part = normalize_tariff_name(tariff_name)
    if page_part:
        return f"{domain_part}::{page_part}::{tariff_part}"
    return f"{domain_part}::{tariff_part}"


def build_expected_key(domain: str, page_url: str, tariff_name: str) -> str:
    if page_url:
        return f"{domain}::{page_url}::{tariff_name}"
    return f"{domain}::{tariff_name}"


@dataclass(frozen=True, slots=True)
class ReferenceMatch:
    reference: ReferenceLink
    matched_tariff_name: str
    key: str


@dataclass(frozen=True, slots=True)
class MatchResult:
    row: ReportRow
    status: str
    error: str
    reference_part: str
    match_key: str
    comparison_type: str
    product_error: bool


@dataclass(frozen=True, slots=True)
class ReferenceIndex:
    by_full_key: dict[str, ReferenceMatch]
    by_domain_wildcard_key: dict[str, ReferenceMatch]
    by_fallback_key: dict[str, ReferenceMatch]

    @classmethod
    def build(cls, references: list[ReferenceLink]) -> "ReferenceIndex":
        by_full_key: dict[str, ReferenceMatch] = {}
        by_domain_wildcard_key: dict[str, ReferenceMatch] = {}
        by_fallback_key: dict[str, ReferenceMatch] = {}

        for reference in references:
            tariff_variants = (reference.tariff_name,) + reference.aliases
            for tariff_name in tariff_variants:
                normalized_domain = normalize_domain(reference.domain)
                normalized_page_url = _normalize_page_url_key(reference.page_url)
                normalized_tariff = normalize_tariff_name(tariff_name)

                if normalized_page_url:
                    key = build_expected_key(normalized_domain, normalized_page_url, normalized_tariff)
                    if key in by_full_key:
                        raise ValueError(f"Duplicate reference key: {key}")
                    by_full_key[key] = ReferenceMatch(
                        reference=reference,
                        matched_tariff_name=normalized_tariff,
                        key=key,
                    )
                else:
                    key = build_expected_key(normalized_domain, "", normalized_tariff)
                    if key in by_fallback_key:
                        raise ValueError(f"Duplicate fallback reference key: {key}")
                    by_fallback_key[key] = ReferenceMatch(
                        reference=reference,
                        matched_tariff_name=normalized_tariff,
                        key=key,
                    )

            if _is_general_page_reference(reference):
                wildcard_domain_key = normalize_domain(reference.domain)
                wildcard_match_key = build_expected_key(wildcard_domain_key, "*", normalize_tariff_name(reference.tariff_name))
                if wildcard_domain_key in by_domain_wildcard_key:
                    raise ValueError(f"Duplicate general-page reference key: {wildcard_domain_key}")
                by_domain_wildcard_key[wildcard_domain_key] = ReferenceMatch(
                    reference=reference,
                    matched_tariff_name=normalize_tariff_name(reference.tariff_name),
                    key=wildcard_match_key,
                )

        return cls(by_full_key=by_full_key, by_domain_wildcard_key=by_domain_wildcard_key, by_fallback_key=by_fallback_key)

    def lookup(self, domain: object, page_url: object, tariff_name: object) -> ReferenceMatch | None:
        normalized_domain = normalize_domain(domain)
        normalized_page_url = _normalize_page_url_key(page_url)
        normalized_tariff = normalize_tariff_name(tariff_name)

        if normalized_page_url:
            full_key = build_expected_key(normalized_domain, normalized_page_url, normalized_tariff)
            match = self.by_full_key.get(full_key)
            if match is not None:
                return match

        fallback_key = build_expected_key(normalized_domain, "", normalized_tariff)
        match = self.by_fallback_key.get(fallback_key)
        if match is not None:
            return match

        return self.by_domain_wildcard_key.get(normalized_domain)


def _is_general_page_reference(reference: ReferenceLink) -> bool:
    comment = normalize_text(reference.comment).lower()
    tariff_name = normalize_tariff_name(reference.tariff_name)
    if "\u043d\u0435\u0442 \u043d\u0430 \u043e\u0431\u0449\u0435\u0439 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0435" in comment:
        return False
    return "\u043e\u0431\u0449\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430" in comment or tariff_name in {"\u0432\u0441\u0435 \u0442\u0430\u0440\u0438\u0444\u044b", "\u043e\u0431\u0449\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430"}


def _comparison_passes(expected: str, actual_variants: list[str], comparison_type: str) -> bool:
    if comparison_type == "regex":
        pattern = normalize_text(expected)
        return any(re.search(pattern, actual_variant) is not None for actual_variant in actual_variants)

    expected_variants = _url_variants(expected)
    if not expected_variants:
        return False

    lowered_expected = [variant.lower() for variant in expected_variants]
    lowered_actual = [variant.lower() for variant in actual_variants]
    return any(expected_part in actual_part for actual_part in lowered_actual for expected_part in lowered_expected)


def evaluate_validation(
    row: ReportRow,
    reference_index: ReferenceIndex,
    use_final_url_as_fallback: bool = False,
) -> MatchResult:
    lookup_key = build_lookup_key(row.domain, row.checked_page_url, row.tariff_name)
    click_url = normalize_text(row.click_url)
    final_url = normalize_text(row.final_url)
    actual_url = click_url
    if not actual_url and use_final_url_as_fallback:
        actual_url = final_url

    if not actual_url:
        return MatchResult(
            row=replace(
                row,
                validation_status=VALIDATION_STATUS_NO_FACTUAL_LINK,
                validation_error="Ссылка после клика не собрана",
                match_key=lookup_key,
                comparison_type="",
                reference_part="",
            ),
            status=VALIDATION_STATUS_NO_FACTUAL_LINK,
            error="Ссылка после клика не собрана",
            reference_part="",
            match_key=lookup_key,
            comparison_type="",
            product_error=True,
        )

    reference_match = reference_index.lookup(row.domain, row.checked_page_url, row.tariff_name)
    if reference_match is None:
        return MatchResult(
            row=replace(
                row,
                validation_status=VALIDATION_STATUS_NO_REFERENCE,
                validation_error="Эталонная строка не найдена",
                match_key=lookup_key,
                comparison_type="",
                reference_part="",
            ),
            status=VALIDATION_STATUS_NO_REFERENCE,
            error="Эталонная строка не найдена",
            reference_part="",
            match_key=lookup_key,
            comparison_type="",
            product_error=False,
        )

    expected_part = normalize_text(reference_match.reference.expected_url_part)
    comparison_type = normalize_text(reference_match.reference.match_type).lower() or "contains"
    actual_variants = _url_variants(actual_url)
    if final_url and final_url != actual_url and _is_related_url(actual_url, final_url):
        actual_variants.extend(variant for variant in _url_variants(final_url) if variant not in actual_variants)
    if _comparison_passes(expected_part, actual_variants, comparison_type):
        return MatchResult(
            row=replace(
                row,
                validation_status=VALIDATION_STATUS_OK,
                validation_error="",
                reference_part=expected_part,
                match_key=reference_match.key,
                comparison_type=comparison_type,
            ),
            status=VALIDATION_STATUS_OK,
            error="",
            reference_part=expected_part,
            match_key=reference_match.key,
            comparison_type=comparison_type,
            product_error=False,
        )

    return MatchResult(
        row=replace(
            row,
            validation_status=VALIDATION_STATUS_NOT_OK,
            validation_error="Фактическая ссылка не содержит эталонную часть",
            reference_part=expected_part,
            match_key=reference_match.key,
            comparison_type=comparison_type,
        ),
        status=VALIDATION_STATUS_NOT_OK,
        error="Фактическая ссылка не содержит эталонную часть",
        reference_part=expected_part,
        match_key=reference_match.key,
        comparison_type=comparison_type,
        product_error=True,
    )


def _is_related_url(source_url: str, candidate_url: str) -> bool:
    source_host = (urlsplit(source_url).netloc or "").lower()
    candidate_host = (urlsplit(candidate_url).netloc or "").lower()
    if not source_host or not candidate_host:
        return False
    if source_host == candidate_host:
        return True
    return candidate_host.endswith(f".{source_host}") or source_host.endswith(f".{candidate_host}")

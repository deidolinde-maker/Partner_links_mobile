from __future__ import annotations

from collections.abc import Iterable

from config.landings import LandingConfig


def _normalize_filter_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"select", "select:selected"}:
        return None
    return cleaned


def select_landings(
    landings: Iterable[LandingConfig],
    target: str,
    domain: str | None,
    url: str | None,
) -> list[LandingConfig]:
    domain = _normalize_filter_value(domain)
    url = _normalize_filter_value(url)
    landings_list = list(landings)
    selected = landings_list

    if target == "domain":
        if not domain:
            raise ValueError("DOMAIN is required when TARGET=domain")
        selected = [landing for landing in selected if landing.domain == domain]
    elif target == "url":
        if not url:
            raise ValueError("URL is required when TARGET=url")
        selected = [landing for landing in selected if landing.url == url]
    elif target != "all":
        raise ValueError("TARGET must be one of: all, domain, url")

    if domain and target != "domain":
        selected = [landing for landing in selected if landing.domain == domain]
    if url and target != "url":
        selected = [landing for landing in selected if landing.url == url]

    if not selected:
        criteria = ", ".join(
            part for part in [f"target={target}", f"domain={domain}", f"url={url}"] if part
        )
        raise ValueError(f"No landings matched the filter: {criteria}")

    return selected

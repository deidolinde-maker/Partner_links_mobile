from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from urllib import error as urlerror
from urllib import request as urlrequest

from src.models import ValidationSummary


@dataclass(frozen=True, slots=True)
class AlertSendResult:
    sent: bool
    status: str
    detail: str


def _format_checked_at(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%d.%m.%Y %H:%M")

    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            continue
    return value


def _build_report_url(build_url: str | None, report_path: str | None) -> str | None:
    if not build_url:
        return None

    build_url = build_url.rstrip("/")
    if not report_path:
        return build_url

    report_path = str(report_path).strip().lstrip("/")
    if not report_path:
        return build_url

    return f"{build_url}/artifact/{report_path}"


def build_validation_alert_message(
    summary: ValidationSummary,
    checked_at: str | None = None,
    build_url: str | None = None,
    report_path: str | None = None,
) -> str:
    report_url = _build_report_url(build_url, report_path)
    lines = [
        "Партнерские ссылки на лендах",
        "",
        f"Дата проверки: {_format_checked_at(checked_at)}",
        "",
        f"Всего проверено тарифов: {summary.total_rows}",
        "",
        f"OK: {summary.ok_rows}",
        f"НЕ OK: {summary.not_ok_rows}",
        f"Нет эталона: {summary.no_reference_rows}",
        f"Нет фактической ссылки: {summary.no_factual_link_rows}",
    ]
    if report_url:
        lines.extend(["", f"Отчет: {report_url}"])
    return "\n".join(lines)


def send_validation_alert(message: str) -> AlertSendResult:
    proxy_url = (os.getenv("TELEGRAM_PROXY_URL") or "").strip()
    proxy_auth_secret = (os.getenv("TELEGRAM_PROXY_AUTH_SECRET") or "").strip()
    chat_credential = (os.getenv("TELEGRAM_PROXY_CHAT_CREDENTIAL") or "").strip()

    if not proxy_url or not proxy_auth_secret or not chat_credential:
        detail = "Telegram proxy env is not configured"
        print(detail)
        return AlertSendResult(sent=False, status="skipped", detail=detail)

    payload = json.dumps(
        {
            "chat_credential": chat_credential,
            "chat": chat_credential,
            "message": message,
            "text": message,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urlrequest.Request(
        proxy_url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {proxy_auth_secret}",
            "X-Auth-Secret": proxy_auth_secret,
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace").strip()
            status = getattr(response, "status", 200)
            detail = body or f"HTTP {status}"
            print(f"[ALERT] sent status={status}")
            return AlertSendResult(sent=True, status="sent", detail=detail)
    except (urlerror.HTTPError, urlerror.URLError, TimeoutError, OSError) as exc:
        detail = str(exc)
        print(f"[ALERT] failed: {detail}")
        return AlertSendResult(sent=False, status="failed", detail=detail)

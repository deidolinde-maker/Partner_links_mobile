from __future__ import annotations

from collections.abc import Iterable

from src.models import ReportRow, RunSummary


def summarize_rows(rows: Iterable[ReportRow], report_path: str, run_mode: str) -> RunSummary:
    rows_list = list(rows)
    product_error_rows = sum(1 for row in rows_list if row.product_error)
    successful_rows = len(rows_list) - product_error_rows
    return RunSummary(
        total_rows=len(rows_list),
        product_error_rows=product_error_rows,
        successful_rows=successful_rows,
        report_path=report_path,
        run_mode=run_mode,
    )


def build_release_failure_message(summary: RunSummary) -> str:
    return (
        f"Product errors found: {summary.product_error_rows}. "
        f"Report saved to: {summary.report_path}"
    )


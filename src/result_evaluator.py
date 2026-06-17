from __future__ import annotations

from collections.abc import Iterable

from src.models import (
    ReportRow,
    RunSummary,
    ValidationSummary,
    VALIDATION_STATUS_NO_FACTUAL_LINK,
    VALIDATION_STATUS_NO_REFERENCE,
    VALIDATION_STATUS_NOT_OK,
    VALIDATION_STATUS_OK,
)


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


def summarize_validation_rows(
    rows: Iterable[ReportRow],
    report_path: str,
    run_mode: str,
) -> ValidationSummary:
    rows_list = list(rows)
    ok_rows = sum(1 for row in rows_list if row.validation_status == VALIDATION_STATUS_OK)
    not_ok_rows = sum(1 for row in rows_list if row.validation_status == VALIDATION_STATUS_NOT_OK)
    no_reference_rows = sum(1 for row in rows_list if row.validation_status == VALIDATION_STATUS_NO_REFERENCE)
    no_factual_link_rows = sum(
        1 for row in rows_list if row.validation_status == VALIDATION_STATUS_NO_FACTUAL_LINK
    )
    return ValidationSummary(
        total_rows=len(rows_list),
        ok_rows=ok_rows,
        not_ok_rows=not_ok_rows,
        no_reference_rows=no_reference_rows,
        no_factual_link_rows=no_factual_link_rows,
        report_path=report_path,
        run_mode=run_mode,
    )


def build_validation_release_failure_message(summary: ValidationSummary) -> str:
    return (
        f"Validation product errors found: {summary.product_error_rows}. "
        f"Report saved to: {summary.report_path}"
    )

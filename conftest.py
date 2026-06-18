from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext, sync_playwright

from config.landings import LANDINGS
from src.landing_filter import select_landings
from src.models import ReportRow, RunSettings
from src.report_writer import write_report
from src.result_evaluator import build_release_failure_message, summarize_rows


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--target", action="store", default="all", choices=("all", "domain", "url"))
    parser.addoption("--domain", action="store", default=None)
    parser.addoption("--url", action="store", default=None)
    parser.addoption("--run-mode", action="store", default="release", choices=("pilot", "release"))
    parser.addoption("--headed", action="store_true", default=False)
    parser.addoption("--timeout-ms", action="store", type=int, default=30_000)
    parser.addoption("--report-dir", action="store", default="reports")
    parser.addoption(
        "--playwright-trace",
        action="store",
        dest="playwright_trace",
        default="retain-on-failure",
        choices=("off", "retain-on-failure", "on"),
    )
    parser.addoption(
        "--screenshot",
        action="store",
        default="only-on-failure",
        choices=("off", "on", "only-on-failure"),
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "partner_links_mobile: partner links mobile checks")


def _landing_test_id(landing) -> str:
    parsed = urlparse(landing.url)
    path_part = parsed.path.strip("/").replace("/", "_") or "root"
    return f"{landing.operator.lower()}_{landing.domain.replace('.', '_')}_{path_part}"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "landing" not in metafunc.fixturenames:
        return

    target = metafunc.config.getoption("--target")
    domain = metafunc.config.getoption("--domain")
    url = metafunc.config.getoption("--url")
    selected_landings = select_landings(LANDINGS, target, domain, url)
    metafunc.parametrize("landing", selected_landings, ids=[_landing_test_id(landing) for landing in selected_landings])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(scope="session")
def run_settings(pytestconfig: pytest.Config) -> RunSettings:
    return RunSettings(
        target=pytestconfig.getoption("--target"),
        domain=pytestconfig.getoption("--domain"),
        url=pytestconfig.getoption("--url"),
        run_mode=pytestconfig.getoption("--run-mode"),
        headed=pytestconfig.getoption("--headed"),
        timeout_ms=int(pytestconfig.getoption("--timeout-ms")),
        report_dir=str(pytestconfig.getoption("--report-dir")),
        trace=pytestconfig.getoption("playwright_trace"),
        screenshot=pytestconfig.getoption("--screenshot"),
    )


@dataclass
class ReportSink:
    rows: list[ReportRow]


@pytest.fixture(scope="session")
def report_sink(run_settings: RunSettings, tmp_path_factory: pytest.TempPathFactory):
    sink = ReportSink(rows=[])
    yield sink

    report_dir = tmp_path_factory.mktemp("partner_links_reports")
    report_path = write_report(sink.rows, report_dir)
    summary = summarize_rows(sink.rows, str(report_path), run_settings.run_mode)

    print(
        f"[SUMMARY] rows={summary.total_rows} product_errors={summary.product_error_rows} "
        f"report={summary.report_path}"
    )

    if run_settings.run_mode == "release" and summary.product_error_rows > 0:
        pytest.fail(build_release_failure_message(summary))


@pytest.fixture(scope="session")
def browser_instance(playwright_instance, run_settings: RunSettings):
    browser = playwright_instance.chromium.launch(
        headless=not run_settings.headed,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="function")
def browser_context(
    browser_instance,
    run_settings: RunSettings,
    request: pytest.FixtureRequest,
):
    context: BrowserContext = browser_instance.new_context(
        viewport={"width": 390, "height": 844},
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
            "Mobile/15E148 Safari/604.1"
        ),
        is_mobile=True,
        has_touch=True,
        ignore_https_errors=True,
    )
    context.set_default_timeout(run_settings.timeout_ms)
    context.set_default_navigation_timeout(run_settings.timeout_ms)

    if run_settings.trace != "off":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield context

    try:
        should_keep_trace = run_settings.trace == "on"
        if run_settings.trace == "retain-on-failure":
            rep_call = getattr(request.node, "rep_call", None)
            should_keep_trace = bool(rep_call and rep_call.failed)

        if run_settings.trace != "off":
            traces_dir = Path(run_settings.report_dir).parent / "artifacts"
            traces_dir.mkdir(parents=True, exist_ok=True)
            trace_name = f"partner_links_mobile_trace_{request.node.name}.zip"
            trace_path = traces_dir / trace_name
            if should_keep_trace:
                context.tracing.stop(path=str(trace_path))
            else:
                context.tracing.stop()
    finally:
        context.close()

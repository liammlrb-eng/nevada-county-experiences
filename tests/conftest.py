"""
Pytest fixtures shared across the test suite.

The frontend is a single static index.html plus some JSON / GeoJSON data
files. Tests need:
  • a local HTTP server serving the project root (file:// URLs break
    fetch() calls to /data/, /feeds/, etc.)
  • a way to capture any uncaught JavaScript errors so smoke tests can
    assert "no console errors" cheaply
  • a `page_url` helper that returns the right URL for the local server

Fixtures here are session-scoped where possible so the server only
spins up once per test run.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Project root — one level up from this tests/ directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Pin to a high port so we don't collide with a developer's running
# server.py (which uses 5000) or other local services. Override via env
# if the chosen port is busy.
DEFAULT_TEST_PORT = int(os.environ.get("NCEXP_TEST_PORT", "8765"))


def _wait_for_port(host: str, port: int, timeout: float = 8.0) -> None:
    """Block until a TCP port accepts connections, or raise on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(
        f"Local test server never opened {host}:{port} within {timeout}s"
    )


@pytest.fixture(scope="session")
def static_server():
    """
    Spin up `python -m http.server` rooted at the project so the frontend
    can serve index.html + /data/* + /feeds/*. Yields the base URL.
    Killed on session teardown.
    """
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(DEFAULT_TEST_PORT),
         "--bind", "127.0.0.1"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port("127.0.0.1", DEFAULT_TEST_PORT)
        yield f"http://127.0.0.1:{DEFAULT_TEST_PORT}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture()
def page_url(static_server) -> str:
    """The URL of the project's root page on the local test server."""
    return f"{static_server}/index.html"


# (External-resource route blocker removed — it accumulated overhead
# across tests and slowed Chromium past goto timeout. Instead, tests
# use `wait_until="commit"` on page.goto so they return as soon as
# navigation commits, then wait on specific selectors that prove the
# part of the page they care about has rendered. The external
# resources are allowed to load in the background and tests don't
# block on them.)


@pytest.fixture()
def loaded_page(page, page_url):
    """
    Convenience fixture: navigate to the page AND wait until the
    inline-script init has actually rendered something.

    The original failure mode this guards against: `page.goto(...,
    wait_until="commit")` returns as soon as navigation commits, but
    the giant inline <script> at the end of index.html hasn't parsed
    yet. A `page.click()` that fires immediately triggers an `onclick`
    handler referencing functions that don't exist yet — caught only
    as a swallowed pageerror, leaving tests to time out on stale state.

    We wait for at least one `.exp-card` to land in `#expGrid` — the
    venue grid only populates after `renderExperiences()` has executed,
    which only happens after the inline script has fully parsed and
    run its bootstrap. So a real card existing is proof the JS layer
    is alive.

    ~100ms extra per test, prevents every flake in this category.
    """
    page.goto(page_url, wait_until="commit")
    # 45s timeout is generous on purpose — the index.html is ~3MB and
    # under cold-start Chromium on Windows + Python's single-threaded
    # http.server the long-tail tests in a parametrize can take 10–20s
    # before the inline script finishes parsing + rendering. Smoke
    # tests should be reliable, not fast.
    page.wait_for_selector("#expGrid .exp-card", timeout=45000)
    return page


# Expected console-error patterns that we deliberately filter out of
# the `console_errors` fixture. These are byproducts of the test
# environment (external resources occasionally fail without network)
# — meaningless for smoke checks. Real JS errors still surface.
_EXPECTED_CONSOLE_NOISE = (
    "Failed to load resource",   # any subresource fetch that didn't make it
    "net::ERR_",                 # browser-level network errors of any kind
)


@pytest.fixture()
def console_errors(page):
    """
    Capture uncaught JavaScript errors + console.error() calls into a
    list that tests can assert against. Yielded list is mutated in-place
    by the Playwright event listeners; tests typically read it after
    triggering whatever flow they're checking.

    Expected noise (subresource fetches aborted by our route blocker)
    is filtered out so it doesn't drown signal. Real JavaScript errors
    — uncaught exceptions, fetch() rejections from app code — still
    surface.
    """
    errors: list[str] = []

    def _is_real_error(text: str) -> bool:
        return not any(noise in text for noise in _EXPECTED_CONSOLE_NOISE)

    def on_console_msg(msg):
        if msg.type == "error" and _is_real_error(msg.text):
            errors.append(f"console.error: {msg.text}")

    def on_page_error(err):
        errors.append(f"pageerror: {err}")

    page.on("console", on_console_msg)
    page.on("pageerror", on_page_error)
    yield errors

"""
Error-surfacing tier (Phase 0 Day 4) — capture + visitor pill + diag banner.

The error-capture script is the FIRST <script> in <body>, so it must be
alive on any loaded page. These tests prove:

  1. an uncaught (async) error lands in window.__ncexpErrors and raises
     the quiet visitor pill,
  2. ?diag=1 flips the device into diagnostic mode where the same error
     raises the loud banner including the actual error message.

Async errors (setTimeout-thrown) are used on purpose: they're invisible
to try/catch around the trigger, which is exactly the class of failure
this tier exists to surface.
"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.smoke


def test_visitor_pill_on_uncaught_error(loaded_page):
    page = loaded_page
    # Sanity: capture is installed and clean after a normal load.
    assert page.evaluate("() => Array.isArray(window.__ncexpErrors)")
    assert page.evaluate("() => window.__ncexpErrors.length") == 0, (
        "page load itself produced captured errors — see bug_log.md"
    )

    page.evaluate("() => setTimeout(() => { throw new Error('qa-probe-error') }, 0)")
    page.wait_for_function("() => window.__ncexpErrors.length > 0", timeout=5000)

    msgs = page.evaluate("() => window.__ncexpErrors.map(e => e.msg).join(' | ')")
    assert "qa-probe-error" in msgs

    pill = page.wait_for_selector("#ncexpErrUi", state="visible", timeout=5000)
    text = pill.inner_text()
    # Visitor mode: friendly wording, no raw error message leakage.
    assert "glitched" in text.lower()
    assert "qa-probe-error" not in text

    # Dismiss works and stays dismissed for further errors.
    pill.query_selector("button:has-text('×')").click()
    page.wait_for_selector("#ncexpErrUi", state="detached", timeout=3000)
    page.evaluate("() => setTimeout(() => { throw new Error('second-probe') }, 0)")
    page.wait_for_function("() => window.__ncexpErrors.length >= 2", timeout=5000)
    assert page.query_selector("#ncexpErrUi") is None


def test_diag_banner_shows_error_detail(page, page_url):
    page.goto(page_url + "?diag=1", wait_until="commit")
    page.wait_for_selector("#expGrid .exp-card", timeout=45000)
    assert page.evaluate("() => window.NCEXP_DIAG.isOn()")

    page.evaluate("() => setTimeout(() => { throw new Error('qa-diag-probe') }, 0)")
    banner = page.wait_for_selector("#ncexpErrUi", state="visible", timeout=5000)
    text = banner.inner_text()
    assert "DIAGNOSTICS" in text
    assert "qa-diag-probe" in text  # diag mode shows the real message

    # console.error is captured into the buffer too.
    page.evaluate("() => console.error('qa-console-probe')")
    page.wait_for_function(
        "() => window.__ncexpErrors.some(e => e.kind === 'console' && e.msg.includes('qa-console-probe'))",
        timeout=3000,
    )

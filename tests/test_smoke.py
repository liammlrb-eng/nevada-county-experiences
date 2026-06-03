"""
Smoke tests for the Nevada County Experience frontend.

Day-1 scope (intentionally small):
  • Page loads with HTTP 200 and no JS console errors
  • Each visitor lane tab (Explore, Suggested, Help Me Plan, Local Guides)
    is present and clicking it activates that tab panel
  • Help modal opens and closes cleanly
  • Search input accepts text
  • At least one experience card renders in the default grid

These are the things that should *always* be true. If any of them break,
something fundamental has regressed and we want to know within a couple
of minutes of pushing.

Later phases will add:
  • State-combination tests (every vibe × every pill)
  • Visual regression snapshots
  • Mobile-viewport variants
  • Modal interaction (suggest, itinerary, share, etc.)
  • Feed validation (ICS / RSS / JSON parse cleanly)

Add new smoke tests sparingly. Anything that's flaky or slow doesn't
belong here — it belongs in a separate suite. The smoke run should
finish in under 30 seconds total so the CI loop stays tight.

Most tests use the `loaded_page` fixture (from conftest.py) which waits
for the inline-script initialization to finish — see its docstring for
why that matters.
"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.smoke


def test_page_loads_without_console_errors(loaded_page, console_errors):
    """The most basic possible check: site loads cleanly. The
    `loaded_page` fixture already navigated + waited for script init."""
    loaded_page.wait_for_selector("#expGrid .exp-card", timeout=8000)
    assert loaded_page.title(), "Page <title> is empty"
    assert not console_errors, (
        f"JS errors during load:\n  - " + "\n  - ".join(console_errors)
    )


def test_all_four_lane_tabs_present(loaded_page):
    """Each visitor lane has a button on the tab row."""
    for lane in ("experiences", "itineraries", "plan", "localguides"):
        # Each tab is wired via `switchTab('<lane>', this)` onclick. We
        # match the onclick attribute instead of label so renames don't
        # silently break this assertion.
        btn = loaded_page.locator(f"button.tab-btn[onclick*=\"'{lane}'\"]")
        assert btn.count() == 1, f"Lane tab missing for {lane!r}"


@pytest.mark.parametrize(
    "lane,panel_id",
    [
        ("experiences", "tab-experiences"),
        ("itineraries", "tab-itineraries"),
        ("plan",        "tab-plan"),
        ("localguides", "tab-localguides"),
    ],
)
def test_clicking_lane_tab_activates_panel(loaded_page, lane, panel_id):
    """Clicking each lane button should add the .active class to the
    matching tab panel (and remove it from the others)."""
    loaded_page.click(f"button.tab-btn[onclick*=\"'{lane}'\"]")
    loaded_page.wait_for_function(
        f"document.getElementById('{panel_id}')?.classList.contains('active')",
        timeout=5000,
    )
    panel = loaded_page.locator(f"#{panel_id}")
    assert "active" in (panel.get_attribute("class") or "")


def test_help_modal_opens_and_closes(loaded_page):
    """Clicking the Help button surfaces #helpOverlay; the close button
    hides it again."""
    loaded_page.click(".tab-help-btn")
    overlay = loaded_page.locator("#helpOverlay")
    loaded_page.wait_for_function(
        "document.getElementById('helpOverlay')?.classList.contains('open')",
        timeout=5000,
    )
    assert "open" in (overlay.get_attribute("class") or "")
    # Close via the modal's × button.
    loaded_page.click("#helpOverlay .modal-close")
    loaded_page.wait_for_function(
        "!document.getElementById('helpOverlay')?.classList.contains('open')",
        timeout=5000,
    )


def test_search_input_accepts_text(loaded_page):
    """The Explore search field on the filter bar takes input."""
    loaded_page.fill("#expSearch", "blacksmithing")
    assert loaded_page.input_value("#expSearch") == "blacksmithing"


def test_experience_card_renders(loaded_page):
    """At least one .exp-card lands in #expGrid by the time the page
    settles. Without any data, the page is broken in a way visitors
    would notice immediately."""
    loaded_page.wait_for_selector("#expGrid .exp-card", timeout=8000)
    cards = loaded_page.locator("#expGrid .exp-card")
    assert cards.count() >= 1, (
        "No experience cards rendered — venue grid is empty. "
        "Either EXPERIENCES is empty or renderExperiences() failed."
    )

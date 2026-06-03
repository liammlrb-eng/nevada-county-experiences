"""
Visual-regression baseline snapshots — desktop + mobile.

OPT-IN. This suite is marked `visual` and is deselected by the default
`pytest` run (see pytest.ini's `-m "not visual"`), so it does NOT gate CI.
Run it deliberately:

    pytest -m visual

Why it's opt-in rather than a CI gate
-------------------------------------
Pixel snapshots are hostage to the OS that renders them — font hinting,
sub-pixel anti-aliasing and emoji glyphs differ between Windows (where the
committed baselines were generated) and the Linux CI runner. A baseline
captured here would diff ~everywhere on CI for reasons that have nothing to
do with a real regression. So this tier is a *local* safety net: run it on
the same OS that owns `tests/__snapshots__/` before a visual change to
confirm you only moved what you meant to move.

What it does to stay deterministic
----------------------------------
The homepage is full of moving parts that would wreck a naive snapshot:
  • external Unsplash photos that load (or don't) over the network
  • a date-dependent editorial strip ("In Season Now")
  • CSS transitions / animations
So before each shot we:
  1. Fulfil every image request with one flat placeholder PNG, so every
     photo slot renders identically regardless of network.
  2. Hide the date-dependent editorial band (its content changes with the
     calendar) — using visibility:hidden so it still reserves its layout
     box and everything below stays put.
  3. Disable animations/transitions and freeze the caret.
We then screenshot the *viewport* (not the full 200-card page): the chrome
at the top — header, nav lanes, filter band, vibe tiles — is where CSS /
layout regressions actually show, and it's stable no matter how many venues
the data grows to.

Baseline lifecycle
------------------
First run for a given (page, viewport): the baseline PNG doesn't exist yet,
so we write it and SKIP. Commit the generated baseline. Every later run
compares against it with a tolerance; a mismatch fails the test and drops
the current shot + a diff image into tests/__snapshots__/_diffs/ (gitignored)
so you can eyeball what moved.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest


pytestmark = pytest.mark.visual

SNAP_DIR = Path(__file__).parent / "__snapshots__"
DIFF_DIR = SNAP_DIR / "_diffs"

# (label, width, height). Mobile height is iPhone-12-ish; desktop is a
# common laptop logical width.
VIEWPORTS = [
    ("desktop", 1280, 800),
    ("mobile", 390, 844),
]

# Injected just before each shot. visibility:hidden (not display:none) on the
# editorial band keeps its box so the layout below doesn't shift.
_FREEZE_CSS = """
*, *::before, *::after {
  animation: none !important;
  transition: none !important;
  caret-color: transparent !important;
}
.editorial-band, #manageBanner { visibility: hidden !important; }
::-webkit-scrollbar { display: none !important; }
"""

# Run after render. Removes the one source of run-to-run nondeterminism that
# matters here — external photo content — WITHOUT touching layout. Every
# photo box on this page is CSS-sized, so hiding the <img> pixels / flattening
# url() backgrounds leaves the boxes exactly where they were; only the photo
# inside goes flat. Crucially this needs no network interception (routing
# every image through the Python bridge is what timed Chromium out), so the
# shot doesn't even depend on images having loaded. Gradients are left intact
# — they're deterministic and part of the design we want to regression-test.
_NEUTRALIZE_JS = """
() => {
  for (const el of document.querySelectorAll('*')) {
    if (el.tagName === 'IMG') { el.style.visibility = 'hidden'; continue; }
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg.includes('url(')) {
      el.style.backgroundImage = 'none';
      el.style.backgroundColor = '#d8d8d8';
    }
  }
}
"""

# Match per-channel: any pixel whose strongest channel moved more than this
# is counted as "changed". Absorbs anti-alias jitter without going blind.
PIXEL_TOLERANCE = 24
# Fraction of changed pixels above which we call it a regression. ~1.5% is
# loose enough to tolerate a couple of jittery glyph edges, tight enough to
# catch a shifted band or a restyled button.
MISMATCH_THRESHOLD = 0.015


def _capture(page, page_url, width, height) -> bytes:
    """Navigate fresh, freeze + neutralize the page, return viewport PNG."""
    page.set_viewport_size({"width": width, "height": height})
    # commit + wait-for-card mirrors the loaded_page fixture: prove the inline
    # script booted and rendered before we shoot.
    page.goto(page_url, wait_until="commit")
    page.wait_for_selector("#expGrid .exp-card", timeout=45000)
    # Let webfonts settle so glyph metrics are final, then freeze + flatten
    # photos + top-align.
    page.evaluate("async () => { try { await document.fonts.ready; } catch (e) {} }")
    page.add_style_tag(content=_FREEZE_CSS)
    page.evaluate(_NEUTRALIZE_JS)
    page.evaluate("() => window.scrollTo(0, 0)")
    return page.screenshot(animations="disabled")


def _compare(baseline: bytes, current: bytes):
    """Return (mismatch_fraction, diff_png_bytes_or_None). Raises on size
    mismatch. Uses Pillow; the test importorskips it."""
    from PIL import Image, ImageChops

    a = Image.open(BytesIO(baseline)).convert("RGB")
    b = Image.open(BytesIO(current)).convert("RGB")
    if a.size != b.size:
        raise AssertionError(
            f"snapshot size changed: baseline {a.size} vs current {b.size}"
        )
    diff = ImageChops.difference(a, b)
    r, g, bl = diff.split()
    # per-pixel max channel difference
    mx = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    mask = mx.point(lambda p: 255 if p > PIXEL_TOLERANCE else 0)
    changed = mask.histogram()[255]
    total = a.size[0] * a.size[1]
    fraction = changed / total if total else 0.0

    diff_png = None
    if fraction > MISMATCH_THRESHOLD:
        # Build a heatmap: current shot with changed pixels tinted red.
        heat = b.copy()
        red = Image.new("RGB", b.size, (255, 0, 0))
        heat.paste(red, (0, 0), mask.convert("L"))
        buf = BytesIO()
        heat.save(buf, format="PNG")
        diff_png = buf.getvalue()
    return fraction, diff_png


@pytest.mark.parametrize("label,width,height", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_home_snapshot(page, page_url, label, width, height):
    """Homepage chrome must match its committed baseline at this viewport."""
    pytest.importorskip("PIL", reason="Pillow needed for visual diffing")
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

    baseline_path = SNAP_DIR / f"home-{label}.png"
    current = _capture(page, page_url, width, height)

    if not baseline_path.exists():
        baseline_path.write_bytes(current)
        pytest.skip(f"baseline created: {baseline_path.name} — commit it, then re-run")

    fraction, diff_png = _compare(baseline_path.read_bytes(), current)
    if diff_png is not None:
        DIFF_DIR.mkdir(parents=True, exist_ok=True)
        (DIFF_DIR / f"home-{label}-current.png").write_bytes(current)
        (DIFF_DIR / f"home-{label}-diff.png").write_bytes(diff_png)

    assert fraction <= MISMATCH_THRESHOLD, (
        f"home-{label} drifted {fraction:.2%} from baseline "
        f"(threshold {MISMATCH_THRESHOLD:.2%}). "
        f"See tests/__snapshots__/_diffs/home-{label}-diff.png"
    )

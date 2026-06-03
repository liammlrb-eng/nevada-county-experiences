# Testing — Day-to-day reference

This project has a Playwright smoke-test suite that runs on every push
via GitHub Actions. Locally, you can run the same suite in about 30
seconds before pushing changes.

## Why this exists

Through the first ~350 commits of this project the dev loop was "ship,
catch bugs in actual use, fix." That stops scaling once feature
combinations explode (vibes × pills × areas × dates × view modes …).
The smoke suite catches the regressions we'd otherwise find by
accident a week later.

## Install (one-time)

```powershell
pip install -r requirements-test.txt
python -m playwright install --with-deps chromium
```

The `--with-deps` flag pulls in the OS-level Chromium dependencies on
Linux. On Windows + macOS it's a no-op but harmless to leave on.

## Run the suite

From the project root:

```powershell
pytest
```

That's it. The suite:

  1. Starts `python -m http.server 8765` rooted at the project (so
     `fetch('/data/trails.geojson')` and friends actually resolve).
  2. Opens `http://127.0.0.1:8765/index.html` in headless Chromium.
  3. Walks through the smoke checks in `tests/test_smoke.py`.
  4. Tears the server down on exit.

If port 8765 is busy on your machine, override it:

```powershell
$env:NCEXP_TEST_PORT = "8766"; pytest
```

## What the suite covers today

### Smoke (`tests/test_smoke.py`, marker `smoke`)

  • Page loads with no JavaScript console errors
  • All four lane tabs (Explore / Suggested / Help Me Plan / Local
    Guides) are present
  • Clicking each lane tab activates the matching tab panel
  • Help modal opens and closes cleanly
  • Search input accepts text
  • At least one experience card renders in the default grid

These are the "if any of this is broken, the site is broken" checks.

### State combinations (`tests/test_filters.py`, marker `combo`)

One test loads the page once and, from inside the browser, walks the
**entire vibe × pill filter space** — every vibe on its own and every
vibe paired with each of its editorial pills (~66 combinations as of
this writing). For each it asserts:

  • no combination throws while applying + rendering
  • no async window error / unhandled rejection fires during the sweep
  • `#expGrid` stays present and queryable for every combo
  • every vibe renders at least one card in *some* state (no dead tiles)

This is the tier that catches "a specific vibe+pill breaks its regex /
render path" — the kind of thing nobody clicks through by hand before a
release. It runs in CI alongside the smoke tests and finishes in ~6s.

### Visual regression (`tests/test_visual.py`, marker `visual`) — opt-in

Pixel-diff snapshots of the homepage chrome at desktop (1280×800) and
mobile (390×844) widths, compared against committed baselines in
`tests/__snapshots__/`.

**This suite is deselected by default and does NOT gate CI** (pytest.ini
carries `-m "not visual"`). Pixel snapshots depend on the rendering OS —
font hinting and emoji glyphs differ between Windows and the Linux CI
runner — so the baselines are only valid on the machine that generated
them. Run it deliberately, on that machine:

```powershell
pytest -m visual
```

To make the shots deterministic the suite freezes animations, hides the
date-dependent editorial band, and flattens every external photo to a
solid color (no network interception — that's both faster and means the
shot doesn't depend on which images loaded). A mismatch drops the current
shot + a red-tinted diff into `tests/__snapshots__/_diffs/` (gitignored).

If you intentionally change the look of the page chrome, regenerate the
baselines: delete the relevant `tests/__snapshots__/home-*.png`, run
`pytest -m visual` once (it recreates them and skips), eyeball the new
PNGs, and commit them.

Higher tiers still to come don't cover deep modal chains, admin features,
or feeds — those arrive in later phases.

## How CI uses this

`.github/workflows/test.yml` runs `pytest` on every push and PR to
`main`. If anything fails:

  • The push gets a red X next to the commit on GitHub
  • Playwright failure artifacts (screenshots + traces) upload to the
    Actions run for 7 days so you can inspect what broke without
    re-running locally

If a test fails on CI but passes locally, the artifacts are the first
place to look.

## Adding a new smoke test

A good smoke test is:

  • **Fast** — under a few seconds. Anything slower belongs in a
    different suite.
  • **Deterministic** — no time-of-day dependencies, no flakey waits.
    Use `page.wait_for_function(...)` instead of `time.sleep(...)`.
  • **Independent** — should not assume any other test ran before it.
  • **Visible-bug-shaped** — covers something a visitor would actually
    notice if it broke.

Add the test to `tests/test_smoke.py` with the `@pytest.mark.smoke`
marker via the file-level `pytestmark = pytest.mark.smoke`.

## Bug log + QA checklist

Two companion files in this folder feed back into the test suite:

  • **`docs/bug_log.md`** — drop one-liners as you find them in normal
    use. Reviewed in batches. Cleared bugs typically get a new
    regression test added here.
  • **`docs/qa_checklist.md`** — manual scenarios for human runs
    before a substantial release. Test what the smoke suite can't
    practically cover: visual judgment, mobile feel, modal interaction
    chains.

Both arrive in Day 3 of the Phase 0 test rollout.

## Roadmap for the suite

| Phase | Coverage | Status |
|---|---|---|
| Day 1 | Smoke tests, CI wired up | ✅ done |
| Day 2 | State-combination sweep (CI) + visual regression baseline (opt-in) | ✅ done |
| Day 3 | `bug_log.md` + `qa_checklist.md` artifacts | next |
| Day 4 | Error-surfacing tier (loud caught-error banner, console capture, Report-bug button) | |
| Later | Feed validation, mobile snapshots, admin-flow tests | |

## Troubleshooting

**`playwright install` fails on Windows**: re-run the command without
`--with-deps`. The flag is only meaningful on Linux.

**Smoke tests fail locally but the site looks fine in the browser**:
look for hardcoded `http://localhost:5000` references; tests use port
8765. Anything that expects the Flask `server.py` to be running won't
work in the test environment — split it out into its own suite.

**Tests time out waiting for `networkidle`**: the page is making
indefinite XHR calls. Usually means a fetch failed silently and is
retrying. Check the browser network panel in headed mode by setting
`--headed` in pytest's command line.

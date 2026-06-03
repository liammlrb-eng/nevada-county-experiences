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

## What the suite covers today (Day 1)

  • Page loads with no JavaScript console errors
  • All four lane tabs (Explore / Suggested / Help Me Plan / Local
    Guides) are present
  • Clicking each lane tab activates the matching tab panel
  • Help modal opens and closes cleanly
  • Search input accepts text
  • At least one experience card renders in the default grid

These are the "if any of this is broken, the site is broken" checks.
They intentionally don't cover deep filter logic, modals beyond Help,
or admin features — those live in higher-tier suites that come in
later phases.

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

| Phase | Coverage |
|---|---|
| Day 1 (this file) | Smoke tests, CI wired up |
| Day 2 | State-combination tests + visual regression baseline |
| Day 3 | `bug_log.md` + `qa_checklist.md` artifacts |
| Day 4 | Error-surfacing tier (loud caught-error banner, console capture, Report-bug button) |
| Later | Feed validation, mobile snapshots, admin-flow tests |

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

# Bug log

Drop one-liners here the moment you notice something off — in normal use,
on your phone, mid-demo, wherever. No triage required at write time; that
happens in batches later. The goal is that nothing relies on memory.

**Format:** one line per bug under Open. When a bug is fixed, move the
line to Cleared with the commit/fix note — and ask whether a regression
test should pin it (most deserve one; that's how the test suite grows
teeth). See [testing.md](testing.md) for the suite layout.

```
- [YYYY-MM-DD] where · what you saw · how to reproduce if known
```

## Open

- [2026-06-12] index.html · clicking a lane tab during initial load throws
  `switchTab is not defined` — the 3MB inline script hasn't parsed yet.
  Planned fix: "still loading" overlay until the script is live.
- [2026-06-12] scraper · Wild Eye Pub: 2 events flagged 404 by the link
  checker (Velvy Appleton & Rebecca Chourré; Barbara Higbie & Teresa Trull
  NC PRIDE Benefit). Possibly the same Wix detail-path rename that hit
  NC Winery — check before dismissing.
- [2026-06-12] scraper/site_scrapers/base.py · `_PACIFIC` is a fixed -7
  offset, so UTC-stamped ICS events parsed in winter (PST) will be 1h off.
  Known crudeness, documented in the code; fix is a real tz database.
- [2026-06-12] server.py:327 · `datetime.utcnow()` DeprecationWarning on
  /feed.rss. Cosmetic until a Python upgrade makes it fatal.

## Cleared

- [2026-06-12] scrape crashed instantly on this laptop —
  `SessionNotCreatedException: cannot find Chrome binary`. Fixed: Chrome→Edge
  fallback in `make_driver()` (f1c293a) + per-source timeouts (245427f).
- [2026-06-12] all 7 approved NC Winery event links 404'd — Wix renamed
  `/event-details/` → `/events-1/`. Fixed: prefix now detected from the page
  (a4a5ab8); queue URLs repaired in place.
- [2026-06-12] NC Winery shows a few days past were reborn as next-year
  events (year-less dates + naive roll-forward). Fixed: only roll >60 days
  past (a4a5ab8).
- [2026-06-12] Gold Vibe trivia night showed as 1:30 AM on the wrong day —
  UTC ICS stamps weren't converted to Pacific. Fixed in parse_ical
  (25b2276); 3 approved queue entries corrected.
- [2026-06-12] "Update Now" gave no acknowledgement and raw tracebacks on
  failure. Fixed: instant disabled "Scraping…" state + condensed one-line
  errors with full trace on hover (f1c293a).

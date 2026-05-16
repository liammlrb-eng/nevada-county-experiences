#!/usr/bin/env python3
"""
Nevada County Experience — Event Scraper
=========================================
Scrapes dynamic event listings using headless Chrome (Selenium).
One browser instance is shared across all Selenium-based scrapers.
Static-HTML scrapers (e.g. Nevada City Chamber) use requests directly.

Usage:
  python event_scraper.py                      # run all scrapers
  python event_scraper.py --discover           # save rendered HTML snapshots
  python event_scraper.py --site "Eventbrite Nevada"  # run one scraper

Output:
  scraper_output/events.json          — scraped events (pending review)
  scraper_output/snapshots/*.html     — rendered HTML for selector inspection

Deployment:
  This script is designed to run as a standalone Python process on any
  traditional server (Linux/Apache, systemd, cron). No cloud services needed.
"""

import os, sys, json, argparse
from datetime import datetime

# Force UTF-8 stdout/stderr. On Windows the console defaults to cp1252,
# which cannot encode characters like '->' (U+2192) that appear in scraper
# log lines — printing one raises UnicodeEncodeError and kills that source's
# entire run. reconfigure() makes every print() in this process (and in the
# imported site_scrapers) UTF-8 safe; errors='replace' is a belt-and-braces
# fallback for any other exotic glyph.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass  # reconfigure() is Python 3.7+; older interpreters skip silently

from site_scrapers.base              import make_driver
from site_scrapers.the_union         import TheUnionScraper
from site_scrapers.go_nevada         import GoNevadaScraper
from site_scrapers.eventbrite_nevada import EventbriteNevadaScraper
from site_scrapers.nevada_city_chamber import NevadaCityChamberScraper
from site_scrapers.kvmr              import KVMRScraper
from site_scrapers.gv_chamber        import GVChamberScraper
from site_scrapers.center_for_arts   import CenterForTheArtsScraper
from site_scrapers.miners_foundry    import MinersFoundryScraper
from site_scrapers.ncac_calendar     import NCACCalendarScraper
from site_scrapers.go_nevada_festivals import GoNevadaFestivalsScraper
from site_scrapers.woocommerce       import CuriousForgeScraper
from site_scrapers.shopify           import WolfCraftScraper
from auto_tagger                     import tag_events
# Future scrapers — uncomment as they're built:
# from site_scrapers.nevada_theatre  import NevadaTheatreScraper
# from site_scrapers.syrcl           import SyrclScraper

# ── Register scrapers here ────────────────────────────────────────────────────
#
# STATIC scrapers (requests-based, no Selenium) are listed first so they
# complete quickly before Selenium starts for the JS-rendered sites.
#
ALL_SCRAPERS = [
    NevadaCityChamberScraper(),     # static HTML — no Selenium
    GVChamberScraper(),             # static HTML — Elementor page
    KVMRScraper(),                  # RSS — Tribe Events feed
    TheUnionScraper(),              # RSS first, Selenium fallback
    CenterForTheArtsScraper(),      # requests first, Selenium fallback (~20 concerts)
    GoNevadaScraper(),              # Selenium — Smart Post Show JS (Cloudflare blocked)
    EventbriteNevadaScraper(),      # Selenium — React-rendered cards
    MinersFoundryScraper(),         # Selenium — site 403s direct requests
    NCACCalendarScraper(),          # Trumba JSON feed (~180 western county events)
    CuriousForgeScraper(),          # WooCommerce Store API — maker classes, one event per session
    WolfCraftScraper(),             # Shopify products.json — craft workshops, one event per class
    # ── Disabled (calendar pages exist but are unreachable) ──
    # GoNevadaFestivalsScraper(),   # Cloudflare 403s even via Selenium
    # NevadaTheatreScraper(),
    # SyrclScraper(),
]

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR  = os.path.join(ROOT_DIR, "scraper_output")
EVENTS_FILE = os.path.join(OUTPUT_DIR, "events.json")


# ── Merge / dedup ─────────────────────────────────────────────────────────────

def load_existing() -> list:
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def event_key(e: dict) -> str:
    return f"{e.get('source','').lower()}|{e.get('title','').lower().strip()}|{e.get('date','')}"

def assign_id(event: dict) -> dict:
    """Add a stable scraper_id (URL-safe hash of the event key)."""
    import hashlib
    key = event_key(event)
    event["scraper_id"] = hashlib.md5(key.encode()).hexdigest()[:12]
    return event

def prune_expired(events: list) -> tuple:
    """
    Remove events that are past their useful life:

    • pending / approved   — pruned the day after their event date
    • dismissed            — pruned 60 days after their event date
                             (60 days is enough to prevent same-cycle re-import;
                              annual recurring events have different dates each year
                              so the blocklist wouldn't help them anyway)
    • no / non-ISO date    — kept (can't judge)

    Returns (kept_events, pruned_count).
    """
    from datetime import timedelta
    today      = datetime.now().date()
    cutoff_dis = today - timedelta(days=60)   # dismissed older than 60 days → gone

    kept, pruned = [], 0
    for ev in events:
        date   = ev.get('date', '')
        status = ev.get('status', 'pending')

        if not date or len(date) < 10:         # no parseable date → keep
            kept.append(ev)
            continue

        try:
            ev_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            kept.append(ev)                    # unparseable → keep
            continue

        if status == 'dismissed':
            if ev_date >= cutoff_dis:          # dismissed but recent enough → keep
                kept.append(ev)
            else:
                pruned += 1                    # dismissed + old → drop
        elif ev_date >= today:                 # future / today → keep
            kept.append(ev)
        else:
            pruned += 1                        # pending/approved + past → drop

    return kept, pruned


def merge(existing: list, fresh: list) -> tuple:
    by_key    = {event_key(e): e for e in existing}
    dismissed = {event_key(e) for e in existing if e.get("status") == "dismissed"}
    merged    = list(existing)
    added     = 0
    for ev in fresh:
        k = event_key(ev)
        if k in dismissed or k in by_key:
            continue
        assign_id(ev)
        merged.append(ev)
        by_key[k] = ev
        added += 1
    merged.sort(key=lambda e: (0 if e.get("status") == "pending" else 1, e.get("date", "9999")))
    return merged, added


# ── Determine which scrapers need Selenium ────────────────────────────────────

def _needs_selenium(scraper) -> bool:
    """Returns True if the scraper's scrape() method actually uses the driver."""
    # Static scrapers override scrape() and ignore the driver; they still
    # receive it but don't call driver.get(). We detect them by checking
    # for the `_HEADERS` or `requests` attribute set on the module.
    import inspect
    src = inspect.getsource(scraper.__class__.scrape) if hasattr(scraper.__class__, 'scrape') else ""
    return "requests.get" not in src or "super().scrape" in src


# ── Main ──────────────────────────────────────────────────────────────────────

def run(scrapers, discover=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 56)
    print("  Nevada County -- Event Scraper")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if discover:
        print("  MODE: DISCOVER  (HTML snapshots will be saved)")
    print("=" * 56)

    all_fresh = []

    # Determine if we need a Selenium driver at all
    selenium_scrapers = [s for s in scrapers if _needs_selenium(s)]
    needs_driver = len(selenium_scrapers) > 0

    driver = None
    if needs_driver:
        print("\nStarting headless Chrome...")
        driver = make_driver()

    try:
        for scraper in scrapers:
            print(f"\n-- {scraper.name} --")
            try:
                events = scraper.scrape(driver, discover=discover)
                all_fresh.extend(events)
            except Exception as e:
                print(f"  ERROR: {e}")
    finally:
        if driver:
            driver.quit()

    # Auto-tag all freshly scraped events before merging
    tag_events(all_fresh)

    existing             = load_existing()
    existing, pruned_cnt = prune_expired(existing)   # drop past events first
    merged, added        = merge(existing, all_fresh)

    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # ── Verify every event URL and flag the dead ones ───────────────────────
    # Runs as the last step of the nightly scrape. Events whose URL doesn't
    # resolve get url_ok=False, surfaced in the admin Events Queue for
    # human follow-up. Re-reads/writes events.json itself.
    link_summary = {"checked": 0, "flagged": 0}
    try:
        from check_event_links import check_all
        link_summary = check_all()
    except Exception as e:
        print(f"  Link check skipped: {e}")

    print(f"\n{'=' * 56}")
    print(f"  Scraped this run   : {len(all_fresh)}")
    print(f"  New (added)        : {added}")
    print(f"  Expired (pruned)   : {pruned_cnt}")
    print(f"  Total in queue     : {len(merged)}")
    print(f"  Links checked      : {link_summary['checked']}")
    print(f"  Links flagged      : {link_summary['flagged']}")
    print(f"  Saved -> scraper_output/events.json")
    if discover:
        print(f"  HTML -> scraper_output/snapshots/")
    print(f"{'=' * 56}")
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true",
                    help="Save rendered HTML for selector debugging")
    ap.add_argument("--site", type=str, default=None,
                    help="Run only one scraper by name")
    args = ap.parse_args()

    scrapers = ALL_SCRAPERS
    if args.site:
        scrapers = [s for s in ALL_SCRAPERS if s.name.lower() == args.site.lower()]
        if not scrapers:
            names = ", ".join(f'"{s.name}"' for s in ALL_SCRAPERS)
            print(f"ERROR: No scraper named '{args.site}'. Available: {names}")
            sys.exit(1)

    run(scrapers, discover=args.discover)


if __name__ == "__main__":
    main()

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

import os, sys, json, argparse, threading
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
from site_scrapers.tribe_events      import CrazyHorseScraper
from site_scrapers.squarespace_events import GoldenEraScraper
from site_scrapers.fairgrounds     import FairgroundsScraper
from site_scrapers.nevadacity_rocks import NevadaCityRocksScraper
from site_scrapers.friar_tucks      import FriarTucksScraper
from site_scrapers.nc_winery        import NevadaCityWineryScraper
from site_scrapers.alibi_truckee    import AlibiTruckeeScraper
from site_scrapers.gold_vibe        import GoldVibeScraper
from site_scrapers.wild_eye_pub     import WildEyePubScraper
from site_scrapers.bylt             import BYLTScraper
# NevadaTheatreScraper — built but disabled (see ALL_SCRAPERS note below)
from auto_tagger                     import tag_events
# Future scrapers — uncomment as they're built:
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
    CrazyHorseScraper(),            # The Events Calendar REST API — live music, DJs, trivia
    GoldenEraScraper(),             # Squarespace events JSON — Golden Era Lounge live music
    FairgroundsScraper(),           # Saffire JSONP — Nevada County Fairgrounds featured events
    NevadaCityRocksScraper(),       # static HTML — nevadacity.rocks live-music calendar (400+ events)
    FriarTucksScraper(),            # static HTML — Friar Tuck's Shopify calendar (~10 shows, ~2 wks)
    NevadaCityWineryScraper(),      # Wix Events JSON inline — ~12 winery concerts
    AlibiTruckeeScraper(),          # static HTML paginated — Alibi Truckee Events Manager (~150)
    GoldVibeScraper(),              # Google Calendar ICS — taproom music/dance/trivia
    WildEyePubScraper(),            # Wix Events JSON — Wild Eye Pub ticketed concerts
    BYLTScraper(),                  # Event Organiser iCal — Bear Yuba Land Trust hikes/art/trail events
    # ── Disabled ──────────────────────────────────────────────────────────
    # NevadaTheatreScraper()        # MEC plugin: REST list is post-date-ordered
    #   so upcoming events are scattered through hundreds of historical
    #   posts; getting them all means fetching every event page (10+ min,
    #   still incomplete) and the MEC archive is AJAX-lazy-loaded. KVMR
    #   already covers Nevada Theatre well (~11 events) — not worth a slow,
    #   brittle, incomplete direct scraper. Revisit only with Selenium
    #   against the AJAX archive if direct coverage becomes important.
    # GoNevadaFestivalsScraper(),   # Cloudflare 403s even via Selenium
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


# ── Per-source timeout ────────────────────────────────────────────────────────
#
# Each source is scraped one at a time with its own hard wall-clock budget, so a
# single hung site (a stalled socket, a wedged Selenium command, an infinite
# JS wait) can't eat the whole run and sink every other source's results. The
# scrape runs in a *daemon* thread we join() with a timeout: if it overruns we
# stop waiting and move on. The thread is a daemon precisely because a hung
# blocking call can't be killed from Python — making it a daemon means it can
# never keep the process alive past the run.
#
# Override the default with the NCEXP_SOURCE_TIMEOUT env var (seconds).
PER_SOURCE_TIMEOUT = int(os.environ.get("NCEXP_SOURCE_TIMEOUT", "120"))


class SourceTimeout(Exception):
    """Raised when a single source exceeds its per-source time budget."""


def _scrape_one(scraper, driver, discover, timeout):
    """Run scraper.scrape() under a hard timeout.

    Returns the event list on success. Re-raises whatever the scraper raised.
    Raises SourceTimeout if it runs longer than `timeout` seconds.
    """
    holder = {}

    def _work():
        try:
            holder["result"] = scraper.scrape(driver, discover=discover)
        except Exception as e:  # propagate to the main thread via the holder
            holder["error"] = e

    t = threading.Thread(target=_work, name=f"scrape:{scraper.name}", daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise SourceTimeout(f"exceeded {timeout}s")
    if "error" in holder:
        raise holder["error"]
    return holder.get("result", []) or []


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
                events = _scrape_one(scraper, driver, discover, PER_SOURCE_TIMEOUT)
                all_fresh.extend(events)
            except SourceTimeout as e:
                print(f"  TIMEOUT: {e} -- skipping {scraper.name}, moving on")
                # If a Selenium source timed out, the shared browser may be
                # wedged mid-command; the abandoned daemon thread might still
                # be holding it, so don't quit it (that could deadlock) -- just
                # drop the reference and spin up a fresh driver for the rest.
                if driver is not None and _needs_selenium(scraper):
                    try:
                        driver = make_driver()
                        print("  Restarted browser after timeout.")
                    except Exception as de:
                        print(f"  Could not restart browser: {de}")
                        driver = None
            except Exception as e:
                print(f"  ERROR: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

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

    # ── Refresh outbound public feeds (ICS / RSS / JSON / venues) ───────────
    # Partners subscribe to feeds/events.{ics,rss,json} on the GitHub Pages
    # site. Regenerate on every scrape so the feeds reflect the freshly
    # approved queue + the latest curated experiences.
    try:
        from generate_feeds import build as build_feeds
        build_feeds()
    except Exception as e:
        print(f"  Feed generation skipped: {e}")

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

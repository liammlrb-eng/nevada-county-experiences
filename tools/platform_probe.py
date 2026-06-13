"""
platform_probe.py — detect what platform an organizer's website runs on
========================================================================
Part of the consolidator-independence strategy (see docs/scraper_buildout.md):
KVMR's REST data gives us a census of who really organizes the county's
events and where their websites live. This tool answers the next question —
*how hard would a direct scraper be?* — by detecting the site's platform
and pointing at the existing scraper class to subclass.

Usage:
    python tools/platform_probe.py https://offbroadstreet.com/ [more urls...]
    python tools/platform_probe.py --census     # probe top uncovered KVMR organizers

The scraper library is platform-based, so detection ≈ effort estimate:

    platform          subclass / pattern to copy
    ----------------  ------------------------------------------------------
    tribe_rest        site_scrapers/tribe_events.py (Tribe Events REST API)
    events_manager    site_scrapers/alibi_truckee.py (paginated .em-event HTML)
    event_organiser   site_scrapers/bylt.py (?feed=eo-events iCal)
    wix_events        site_scrapers/nc_winery.py / wild_eye_pub.py (inline JSON)
    squarespace       site_scrapers/squarespace_events.py (?format=json)
    shopify           site_scrapers/shopify.py / friar_tucks.py
    woocommerce       site_scrapers/woocommerce.py (Store API)
    gcal_ics          site_scrapers/gold_vibe.py (public Google Calendar ICS)
    ics_feed          base EventScraper.parse_ical via a direct ICS URL
    wordpress         base EventScraper RSS autodiscovery may work as-is
    hosted:<name>     external hosted platform (Facebook, Mobilize, Momence…)
                      — no site to scrape; keep coverage via KVMR
"""
from __future__ import annotations
import re
import sys
import time
from collections import Counter
from urllib.parse import urlparse

import requests

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT = 15

# Hosted platforms recognizable by domain — no independent site to scrape.
_HOSTED = {
    "facebook.com": "Facebook events (auth-walled — keep via KVMR)",
    "instagram.com": "Instagram (no event API — keep via KVMR)",
    "eventbrite.com": "Eventbrite (covered by EventbriteNevadaScraper)",
    "mobilize.us": "Mobilize (political org platform — keep via KVMR)",
    "momence.com": "Momence booking platform — keep via KVMR",
    "wetravel.com": "WeTravel retreat bookings — keep via KVMR",
    "meetup.com": "Meetup (API requires key) — keep via KVMR",
    "calendar.google.com": "bare Google Calendar — try gold_vibe.py ICS pattern",
}

PLATFORM_SCRAPER = {
    "tribe_rest":      "subclass tribe_events.py (Tribe REST API) — ~20 min",
    "events_manager":  "subclass alibi_truckee.py (.em-event HTML) — ~30 min",
    "event_organiser": "subclass bylt.py (?feed=eo-events iCal) — ~20 min",
    "wix_events":      "subclass nc_winery.py / wild_eye_pub.py (Wix JSON) — ~30 min",
    "squarespace":     "subclass squarespace_events.py (?format=json) — ~30 min",
    "shopify":         "subclass shopify.py / friar_tucks.py — ~30 min",
    "woocommerce":     "subclass woocommerce.py (Store API) — ~30 min",
    "gcal_ics":        "subclass gold_vibe.py (public ICS) — ~20 min",
    "ics_feed":        "base parse_ical with the ICS URL — ~20 min",
    "wordpress":       "try base RSS autodiscovery first — may be ~10 min",
    "static":          "custom parse() over static HTML — effort varies",
}


def _get(url: str) -> requests.Response | None:
    try:
        return requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True)
    except Exception:
        return None


def probe(url: str) -> dict:
    """Detect the platform behind `url`. Returns {url, platform, evidence, next_step}."""
    out = {"url": url, "platform": "unreachable", "evidence": "", "next_step": ""}
    host = urlparse(url if "//" in url else "https://" + url).netloc.replace("www.", "").lower()

    for dom, note in _HOSTED.items():
        if host.endswith(dom):
            out.update(platform=f"hosted:{dom.split('.')[0]}", evidence=host, next_step=note)
            return out
    if host.endswith(".squarespace.com"):
        out.update(platform="squarespace", evidence="*.squarespace.com domain",
                   next_step=PLATFORM_SCRAPER["squarespace"])
        return out

    base = f"https://{host}"
    r = _get(base)
    if r is None or not r.ok:
        r = _get("http://" + host)
    if r is None:
        return out
    html = r.text[:400_000].lower()
    server = (r.headers.get("server") or "").lower()
    origin = f"{urlparse(r.url).scheme}://{urlparse(r.url).netloc}"

    def found(platform, evidence):
        out.update(platform=platform, evidence=evidence,
                   next_step=PLATFORM_SCRAPER.get(platform, ""))
        return out

    # WordPress event plugins (check before generic WP)
    if "tribe-events" in html or "the-events-calendar" in html:
        t = _get(f"{origin}/wp-json/tribe/events/v1/events?per_page=1")
        if t is not None and t.ok and "events" in (t.text[:200] or ""):
            return found("tribe_rest", "open Tribe REST API")
        return found("tribe_rest", "Tribe markup (REST may need probing)")
    if "events-manager" in html or re.search(r'class="[^"]*em-(?:event|item)', html):
        return found("events_manager", "Events Manager markup")
    eo = _get(f"{origin}/?feed=eo-events")
    if eo is not None and eo.ok and "text/calendar" in (eo.headers.get("content-type") or ""):
        return found("event_organiser", "?feed=eo-events serves iCal")

    # Site builders
    if "squarespace" in server or "squarespace" in html:
        return found("squarespace", f"server={server or 'markup'}")
    if "x-wix-request-id" in {k.lower() for k in r.headers} or "wixstatic.com" in html:
        return found("wix_events", "Wix headers/CDN")
    if "cdn.shopify.com" in html or "shopify" in server:
        p = _get(f"{origin}/products.json")
        ev = "products.json open" if (p is not None and p.ok) else "Shopify CDN markers"
        return found("shopify", ev)
    if "woocommerce" in html:
        return found("woocommerce", "WooCommerce markup")

    # Calendars + feeds
    if "calendar.google.com/calendar" in html:
        return found("gcal_ics", "embedded Google Calendar (public ICS likely)")
    m = re.search(r'href="([^"]+\.ics[^"]*)"', html)
    if m:
        return found("ics_feed", f"ICS link: {m.group(1)[:60]}")

    if "wp-content" in html or "wordpress" in html:
        return found("wordpress", "generic WordPress")
    return found("static", f"no platform markers (server={server or '?'})")


# ── Census mode ───────────────────────────────────────────────────────────────

# Organizers already covered by a direct scraper (substring match, lowercase).
_COVERED = {
    "bear yuba land trust", "crazy horse", "nevada city winery",
    "miners foundry", "center for the arts", "kvmr", "fairgrounds",
    "gold vibe", "wild eye", "friar tuck", "golden era", "curious forge",
    "wolf craft", "alibi", "chamber",
}


def census(top_n: int = 14) -> list[dict]:
    """Aggregate KVMR's organizer data, probe each uncovered organizer's site."""
    sys.path.insert(0, "scraper")
    from site_scrapers.kvmr import KVMRScraper

    events = KVMRScraper().scrape(None)
    by_org: dict[str, dict] = {}
    for e in events:
        org = (e.get("organizer") or "").strip()
        if not org or any(c in org.lower() for c in _COVERED):
            continue
        rec = by_org.setdefault(org, {"organizer": org, "count": 0,
                                      "hosts": Counter(), "categories": Counter()})
        rec["count"] += 1
        rec["categories"][e.get("category") or "?"] += 1
        host = urlparse(e.get("url", "")).netloc.replace("www.", "")
        if host and "kvmr.org" not in host:
            rec["hosts"][host] += 1

    ranked = sorted(by_org.values(), key=lambda r: -r["count"])[:top_n]
    for rec in ranked:
        host = rec["hosts"].most_common(1)
        rec["site"] = host[0][0] if host else ""
        rec["category"] = rec["categories"].most_common(1)[0][0]
        if rec["site"]:
            print(f"  probing {rec['organizer'][:40]} -> {rec['site']}", flush=True)
            rec["probe"] = probe(rec["site"])
            time.sleep(0.5)
        else:
            rec["probe"] = {"platform": "none", "evidence": "no website on any event",
                            "next_step": "KVMR-only coverage"}
    return ranked


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1

    if args[0] == "--census":
        ranked = census()
        print()
        print(f"{'#':>3} {'org':<42} {'evts':>4}  {'platform':<18} next step")
        for i, rec in enumerate(ranked, 1):
            p = rec["probe"]
            print(f"{i:>3} {rec['organizer'][:40]:<42} {rec['count']:>4}  "
                  f"{p['platform']:<18} {p['next_step'][:60]}")
        return 0

    for url in args:
        p = probe(url)
        print(f"\n{url}\n  platform : {p['platform']}\n  evidence : {p['evidence']}"
              f"\n  next step: {p['next_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

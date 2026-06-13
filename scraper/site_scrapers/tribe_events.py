"""
The Events Calendar (Tribe) REST API scraper.

"The Events Calendar" is one of the most common WordPress event
plugins. Any site running it exposes a public, read-only REST API:

    /wp-json/tribe/events/v1/events

It returns fully structured JSON — title, start_date, end_date,
cost, categories, venue, image, url — paginated. No auth, no HTML
scraping, no site changes. Far cleaner than the plugin's RSS feed.

ADDING ANOTHER TRIBE-EVENTS VENUE
=================================
Subclass TribeEventsScraper, set name / url / store_root / area.
The API shape is identical across every site running the plugin —
the existing KVMR scraper uses the same plugin's RSS path; this
class uses the richer JSON API.
"""
from __future__ import annotations
import re, html, requests
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS

_PER_PAGE  = 50
_MAX_PAGES = 12
_MAX_FUTURE_DAYS = 480

# Tribe category name (lowercased) -> our internal category + extra tags
_CAT_MAP = {
    "live music": ("Music event", ["Music"]),
    "music":      ("Music event", ["Music"]),
    "concert":    ("Music event", ["Music"]),
    "dj":         ("Music event", ["Music", "Nightlife"]),
    "trivia":     ("Community",   ["Social"]),
    "comedy":     ("Theatre",     ["Social"]),
    "dance":      ("Dance",       ["Dance"]),
    "karaoke":    ("Music event", ["Music", "Social"]),
}

# Western Nevada County cities — used by region-filtered (multi-venue /
# statewide) Tribe sources to keep only in-area events. Single-venue sources
# leave keep_cities=None and skip filtering entirely.
_NEVCO_CITIES = {
    "nevada city", "grass valley", "penn valley", "north san juan",
    "rough and ready", "rough & ready", "cedar ridge", "alta sierra",
    "lake of the pines", "lake wildwood", "washington", "chicago park",
    "smartsville", "north columbia", "camptonville",
}


def _venue_dict(ev: dict) -> dict:
    """Tribe's `venue` is usually a dict, sometimes a list, sometimes absent."""
    v = ev.get("venue")
    if isinstance(v, list):
        v = v[0] if v else None
    return v if isinstance(v, dict) else {}


def _area_from_city(city: str) -> str:
    c = (city or "").lower()
    if "nevada city" in c:  return "Nevada City"
    if "grass valley" in c: return "Grass Valley"
    if "penn valley" in c:  return "Penn Valley"
    if "north san juan" in c: return "North San Juan"
    return "Nevada County"


def _clean_description(raw: str) -> str:
    """Tribe descriptions often carry page-builder shortcodes
    ([et_pb_section ...]) and HTML. Strip both, return a short teaser."""
    if not raw:
        return ""
    txt = re.sub(r"\[[^\]]*\]", " ", raw)            # drop [shortcodes]
    txt = html.unescape(BeautifulSoup(txt, "html.parser").get_text(" ", strip=True))
    txt = re.sub(r"\s+", " ", txt).strip()
    return (txt[:397] + "...") if len(txt) > 400 else txt


class TribeEventsScraper(EventScraper):
    """Generic 'The Events Calendar' REST API scraper. Subclass + configure.

    Single-venue sources (a bar, a shopping center) just set name/url/
    store_root/area — every event is at that venue, no filtering.

    Multi-venue or statewide sources (e.g. an association that lists events
    all over California) set `keep_cities` to a city allowlist; events are
    then region-filtered by their venue city and each event's location/area
    comes from its own venue rather than the source name.
    """
    name          = "Tribe Events"
    url           = ""             # human-facing events page
    store_root    = ""             # site root, e.g. "https://crazyhorsenc.com"
    area          = "Nevada County"
    keep_cities   = None           # None = single-venue (no filter); set = region-filter
    default_music = True           # single music venues default uncategorized events to Music
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        api = f"{self.store_root.rstrip('/')}/wp-json/tribe/events/v1/events"
        today = date.today()
        print(f"  [{self.name}] -> {api}  (The Events Calendar REST API)")

        raw = []
        for page in range(1, _MAX_PAGES + 1):
            try:
                resp = requests.get(
                    api, headers=_REQUESTS_HEADERS, timeout=25,
                    params={"per_page": _PER_PAGE, "page": page,
                            "start_date": today.strftime("%Y-%m-%d")},
                )
                if resp.status_code == 400:
                    break          # Tribe returns 400 past the last page
                resp.raise_for_status()
                batch = (resp.json() or {}).get("events", [])
            except Exception as e:
                print(f"  [{self.name}] page {page} fetch failed: {e}")
                break
            if not batch:
                break
            raw.extend(batch)
            print(f"  [{self.name}] page {page}: {len(batch)} event(s)")
            if len(batch) < _PER_PAGE:
                break

        if not raw:
            print(f"  [{self.name}] 0 events returned")
            return []

        if discover:
            import os, json
            from .base import SNAPSHOT_DIR
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            fn = self.name.lower().replace(" ", "_") + "_events.json"
            with open(os.path.join(SNAPSHOT_DIR, fn), "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
            print(f"  [{self.name}] Snapshot saved -> snapshots/{fn}")

        events = []
        seen   = set()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)

        for ev in raw:
            title = html.unescape((ev.get("title") or "").strip())
            if not title:
                continue

            # ── Region filter (multi-venue / statewide sources only) ────────
            venue = _venue_dict(ev)
            if self.keep_cities is not None:
                city = (venue.get("city") or "").strip().lower()
                if not city or not any(c in city for c in self.keep_cities):
                    continue   # no in-area city → drop (conservative for wide sources)
                ev_location = html.unescape(venue.get("venue") or "") or self.name
                ev_area     = _area_from_city(city)
            else:
                ev_location = self.name
                ev_area     = self.area

            # ── Date / time (start_date is local venue time) ────────────────
            start = ev.get("start_date") or ""
            date_str, time_str = "", ""
            try:
                dt = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
                if dt.date() < today or dt.date() > cutoff:
                    continue
                date_str = dt.strftime("%Y-%m-%d")
                if not ev.get("all_day") and (dt.hour or dt.minute):
                    time_str = dt.strftime("%I:%M %p").lstrip("0")
            except Exception:
                continue

            end_time = ""
            try:
                de = datetime.strptime((ev.get("end_date") or "")[:19],
                                       "%Y-%m-%d %H:%M:%S")
                if de.date().isoformat() == date_str and (de.hour or de.minute):
                    end_time = de.strftime("%I:%M %p").lstrip("0")
            except Exception:
                pass

            # ── Category / tags from Tribe categories ───────────────────────
            category, tags = "Event", []
            for c in (ev.get("categories") or []):
                cname = (c.get("name") or "").strip().lower()
                if cname in _CAT_MAP:
                    category, extra = _CAT_MAP[cname]
                    tags = list(dict.fromkeys(tags + extra))
            if not tags and self.default_music:   # single music venues lean Music
                category, tags = "Music event", ["Music"]

            # ── Cost into the description note ──────────────────────────────
            desc = _clean_description(ev.get("description") or ev.get("excerpt") or "")
            cost = html.unescape((ev.get("cost") or "").strip())
            if cost:
                desc = f"{cost} · {desc}" if desc else cost

            image = ""
            img = ev.get("image")
            if isinstance(img, dict):
                image = img.get("url", "") or ""

            key = f"{title.lower()}|{date_str}"
            if key in seen:
                continue
            seen.add(key)

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                end_time=end_time,
                location=ev_location,
                area=ev_area,
                description=desc,
                category=category,
                tags=tags,
                url=ev.get("url") or self.url,
                image=image,
            ))

        print(f"  [{self.name}] {len(events)} event(s) from "
              f"{len(raw)} API record(s)")
        return events

    def parse(self, soup) -> list[dict]:
        return []


class CrazyHorseScraper(TribeEventsScraper):
    """Crazy Horse Saloon & Grill — historic Nevada City live-music venue
    and restaurant. Bands, DJs, trivia and dance nights via The Events
    Calendar plugin."""
    name       = "Crazy Horse Saloon"
    url        = "https://crazyhorsenc.com/events/"
    store_root = "https://crazyhorsenc.com"
    area       = "Nevada City"


class McKnightCrossingScraper(TribeEventsScraper):
    """McKnight Crossing — Grass Valley shopping center. Single-venue Tribe
    calendar (markets, community days, seasonal events). Found via the
    chamber-directory build-out; not music-leaning, so no Music default."""
    name          = "McKnight Crossing"
    url           = "https://mcknightcrossing.net/events/"
    store_root    = "https://mcknightcrossing.net"
    area          = "Grass Valley"
    default_music = False


class CaliforniaBluegrassScraper(TribeEventsScraper):
    """California Bluegrass Association — statewide bluegrass org whose Tribe
    calendar lists events across CA. Region-filtered to western Nevada County
    by venue city (the CBA Father's Day Festival and local jams/concerts)."""
    name          = "California Bluegrass Association"
    url           = "https://californiabluegrass.org/events/"
    store_root    = "https://californiabluegrass.org"
    keep_cities   = _NEVCO_CITIES
    default_music = True   # bluegrass org — uncategorized events are music

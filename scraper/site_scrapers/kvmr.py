"""
KVMR Community Radio — Event Scraper
=====================================
KVMR (kvmr.org) uses The Events Calendar (Tribe Events) WordPress
plugin, whose REST API is open:

    https://www.kvmr.org/wp-json/tribe/events/v1/events

We read that instead of the RSS feed (which this scraper used through
2026-06). The API gives us, per event, what RSS flattened away:

    start_date   real event date+time, already site-local (Pacific) —
                 no more parsing dates out of URL paths
    venue        structured: name, address, CITY, venue website
                 (usually a dict; occasionally a list — handle both)
    organizer    the actual presenter ("Bear Yuba Land Trust", ...)
    website      the event's ORIGINAL page on the organizer's own site

KVMR is a *consolidator* — it republishes events that venues/organizers
also publish themselves (Miners Foundry, BYLT, Center for the Arts...).
The `website` field is therefore used as the event URL when present:
it points visitors at the original source, and it lets the merge step
in event_scraper.py dedupe a KVMR repost against the same event scraped
directly from its source (matched on normalized URL + date). The KVMR
listing page is kept on the event as `listing_url`.

Location filter: KVMR broadcasts regionally and lists events in
Sacramento, the Bay Area, even Mendocino. With a structured city field
we filter by city allowlist (western Nevada County + the San Juan
Ridge / Yuba foothill communities + the few neighbors the old filter
always passed). Known-distant cities are rejected outright. Events with
no city fall back to the old keyword heuristic over title + venue name
(assume local unless a distant place is named).
"""

import html as html_mod
import re
import time as time_mod
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS


_API = "https://www.kvmr.org/wp-json/tribe/events/v1/events"
_MAX_PAGES = 12          # 50/page; ~10 pages covers 180 days of KVMR listings
_PAGE_DELAY_SEC = 0.4    # courtesy to the host
_WINDOW_DAYS = 180       # how far ahead to ingest

# Cities that count as in-region (case-insensitive exact match on the
# venue's city field). Western Nevada County plus the San Juan Ridge /
# Yuba foothill communities in BYLT's orbit, plus Truckee/Auburn/Colfax
# which the previous keyword filter always passed.
_LOCAL_CITIES = {
    "nevada city", "grass valley", "penn valley", "north san juan",
    "rough and ready", "rough & ready", "chicago park", "cedar ridge",
    "alta sierra", "washington", "lake wildwood", "lake of the pines",
    "french corral", "north columbia", "camptonville", "dobbins",
    "oregon house", "smartsville", "truckee", "auburn", "colfax",
}

# Venue keywords for the no-city fallback (same spirit as the old RSS
# filter). NOTE: no "kvmr" — too generic on this feed.
_LOCAL_PLACES = {
    "nevada city", "grass valley", "nevada county", "truckee",
    "penn valley", "north san juan", "rough and ready", "chicago park",
    "cedar ridge", "washington", "auburn", "colfax",
    "miners foundry", "center for the arts", "nevada theatre",
    "briarpatch", "broad street", "downtown nevada", "downtown grass",
}

# Known-distant places — rejected whether they appear as the venue city
# or in the title/venue text of a city-less event.
_DISTANT_PLACES = {
    # Sacramento basin
    "sacramento", "san francisco", "oakland", "berkeley", "san jose",
    "reno", "tahoe city", "south lake tahoe", "los angeles", "portland",
    "seattle", "phoenix", "stockton", "modesto", "fresno", "davis",
    "folsom", "elk grove", "roseville", "rocklin", "lincoln",
    # Sacramento / Bay venues that show up in KVMR calendar
    "capital stage", "r street", "harris center", "crocker art",
    "music circus", "sacramento state", "sac state",
    # North-state foothills outside the region
    "chico", "oroville", "paradise", "quincy", "downieville",
    "marysville", "yuba city", "beale air", "laytonville", "willits",
    "ukiah",
    # Amador / El Dorado (south of Nevada County)
    "sutter creek", "jackson square", "plymouth", "ione",
    "placerville", "coloma", "lotus", "cameron park", "shingle springs",
    "el dorado hills",
    # Wine country / coast
    "napa", "sonoma", "calistoga", "healdsburg", "santa rosa",
    "vacaville", "fairfield", "vallejo",
    # Eastern Sierra / Nevada
    "carson city", "minden", "gardnerville", "incline village",
    "kings beach", "crystal bay", "mammoth", "bishop",
    # Far north
    "redding", "red bluff", "weaverville", "mount shasta",
}

_LOCAL_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _LOCAL_PLACES) + r")\b", re.I)
_DISTANT_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _DISTANT_PLACES) + r")\b", re.I)


def _venue_dict(rec: dict) -> dict:
    """rec['venue'] is usually a dict, occasionally a list, sometimes
    absent/False. Normalize to a (possibly empty) dict."""
    v = rec.get("venue")
    if isinstance(v, list):
        v = v[0] if v else None
    return v if isinstance(v, dict) else {}


def _is_local(rec: dict) -> bool:
    venue = _venue_dict(rec)
    city = (venue.get("city") or "").strip().lower()
    if city:
        if city in _LOCAL_CITIES:
            return True
        if _DISTANT_RE.search(city):
            return False
        # City present but unrecognized: KVMR typed a real city and it
        # isn't one of ours — almost always outside the region.
        return False
    # No city on the venue — fall back to keywords over title + venue
    # name (the pre-REST behavior: assume local unless distant-named).
    text = html_mod.unescape(rec.get("title") or "") + " " + (venue.get("venue") or "")
    if _DISTANT_RE.search(text):
        return False
    return True


class KVMRScraper(EventScraper):
    """KVMR Community Radio events via the Tribe Events REST API."""

    name          = "KVMR"
    url           = "https://www.kvmr.org/events/"
    wait_css      = "body"
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver, discover: bool = False) -> list[dict]:
        start = datetime.now().strftime("%Y-%m-%d")
        end   = (datetime.now() + timedelta(days=_WINDOW_DAYS)).strftime("%Y-%m-%d")
        events: list[dict] = []
        skipped_distant = 0
        page = 1

        while page <= _MAX_PAGES:
            url = (f"{_API}?start_date={start}&end_date={end}"
                   f"&per_page=50&page={page}&status=publish")
            print(f"  [{self.name}] page {page} → REST API")
            try:
                resp = requests.get(url, headers=_REQUESTS_HEADERS, timeout=25)
                if resp.status_code != 200:
                    print(f"  [{self.name}] HTTP {resp.status_code} — stopping")
                    break
                data = resp.json()
            except Exception as e:
                print(f"  [{self.name}] API error: {e} — stopping")
                break

            recs = data.get("events", [])
            if not recs:
                break

            for rec in recs:
                if rec.get("hide_from_listings"):
                    continue
                if not _is_local(rec):
                    skipped_distant += 1
                    continue
                ev = self._build_event(rec)
                if ev:
                    events.append(ev)

            if page >= int(data.get("total_pages") or 1):
                break
            page += 1
            time_mod.sleep(_PAGE_DELAY_SEC)

        print(f"  [{self.name}] {len(events)} kept, {skipped_distant} outside region")
        return events

    def _build_event(self, rec: dict) -> dict | None:
        title = html_mod.unescape((rec.get("title") or "")).strip()
        if not title:
            return None

        # start_date is site-local ("2026-06-14 19:00:00")
        date_str, time_str = "", ""
        try:
            dt = datetime.strptime(rec.get("start_date", ""), "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
            if not rec.get("all_day"):
                time_str = dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return None

        venue = _venue_dict(rec)
        venue_name = html_mod.unescape(venue.get("venue") or "").strip()
        city       = (venue.get("city") or "").strip()
        address    = (venue.get("address") or "").strip()
        loc_bits = [b for b in (venue_name, address, city) if b]
        if len(loc_bits) > 1:
            location = loc_bits[0] + " · " + ", ".join(loc_bits[1:])
        else:
            location = loc_bits[0] if loc_bits else ""

        organizers = rec.get("organizer") or []
        if isinstance(organizers, dict):
            organizers = [organizers]
        organizer = ", ".join(
            html_mod.unescape(o.get("organizer") or "").strip()
            for o in organizers if isinstance(o, dict) and o.get("organizer")
        )

        # Original-source URL: prefer the organizer's own event page so
        # visitors land at the source and the merge step can dedupe this
        # against the same event scraped directly. Keep KVMR's page as
        # listing_url either way.
        kvmr_url = (rec.get("url") or "").strip()
        website  = (rec.get("website") or "").strip()
        event_url = website if website.startswith("http") and "kvmr.org" not in website else kvmr_url

        desc_html = rec.get("description") or rec.get("excerpt") or ""
        description = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)[:400]

        image = ""
        img = rec.get("image")
        if isinstance(img, dict):
            image = img.get("url") or ""

        cats = [c.get("name") for c in (rec.get("categories") or []) if c.get("name")]
        category = cats[0] if cats else "Event"

        area = city if city.lower() in ("nevada city", "grass valley", "penn valley", "truckee") \
               else "Nevada County"

        ev = self.make_event(
            title=title,
            date=date_str,
            time=time_str,
            location=location,
            description=description,
            url=event_url or self.url,
            category=category,
            image=image,
            area=area,
        )
        # Consolidator provenance — not part of make_event's core schema.
        if organizer:
            ev["organizer"] = organizer
        if kvmr_url and kvmr_url != ev["url"]:
            ev["listing_url"] = kvmr_url
        return ev

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """Unused — scrape() reads the REST API directly."""
        return []

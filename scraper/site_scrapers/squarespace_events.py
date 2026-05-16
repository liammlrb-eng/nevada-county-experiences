"""
Squarespace Events-collection scraper.

Squarespace exposes any page as JSON by appending ?format=json. For a
page backed by an *Events collection* the JSON includes an `upcoming`
array — each entry a fully structured event (title, startDate /
endDate as epoch-milliseconds, fullUrl, body, location).

    https://venue.com/events?format=json   ->   { "upcoming": [ ... ] }

No auth, no HTML scraping, no site changes. This is the Squarespace
equivalent of the WooCommerce Store API / Tribe Events REST API.

NOTE — not every Squarespace page is an Events collection. A plain
page or a folder returns ?format=json with no `upcoming` array; those
venues need a different approach (ASiF, for example, has no events
collection). Check the JSON has `upcoming` before relying on this.

ADDING ANOTHER SQUARESPACE-EVENTS VENUE
=======================================
Subclass SquarespaceEventsScraper, set name / url / store_root /
events_path / area.
"""
from __future__ import annotations
import html, requests
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS

_MAX_FUTURE_DAYS = 480


def _strip_html(s: str) -> str:
    if not s:
        return ""
    return html.unescape(BeautifulSoup(s, "html.parser").get_text(" ", strip=True))


def _epoch_ms_to_local(ms) -> datetime | None:
    """Squarespace stores event start/end as epoch milliseconds.
    fromtimestamp() yields the scraper machine's local time — correct
    on the intended Pacific-time deployment."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000)
    except Exception:
        return None


class SquarespaceEventsScraper(EventScraper):
    """Generic Squarespace Events-collection scraper. Subclass + configure."""
    name          = "Squarespace Events"
    url           = ""             # human-facing events page
    store_root    = ""             # site root, e.g. "https://www.goldeneralounge.com"
    events_path   = "/events"      # path of the Events collection
    area          = "Nevada County"
    default_category = "Event"
    default_tags     = []
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        api = f"{self.store_root.rstrip('/')}{self.events_path}?format=json"
        print(f"  [{self.name}] -> {api}  (Squarespace events JSON)")

        try:
            resp = requests.get(api, headers=_REQUESTS_HEADERS, timeout=25)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [{self.name}] fetch failed: {e}")
            return []

        upcoming = data.get("upcoming")
        if not isinstance(upcoming, list):
            print(f"  [{self.name}] no 'upcoming' array — not an Events collection")
            return []
        if not upcoming:
            print(f"  [{self.name}] 0 upcoming events")
            return []

        if discover:
            import os, json
            from .base import SNAPSHOT_DIR
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            fn = self.name.lower().replace(" ", "_") + "_events.json"
            with open(os.path.join(SNAPSHOT_DIR, fn), "w", encoding="utf-8") as f:
                json.dump(upcoming, f, indent=2, ensure_ascii=False)
            print(f"  [{self.name}] Snapshot saved -> snapshots/{fn}")

        events = []
        seen   = set()
        today  = date.today()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)

        for it in upcoming:
            title = html.unescape((it.get("title") or "").strip())
            if not title:
                continue

            dt = _epoch_ms_to_local(it.get("startDate"))
            if not dt:
                continue
            if dt.date() < today or dt.date() > cutoff:
                continue
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%I:%M %p").lstrip("0") if (dt.hour or dt.minute) else ""

            end_time = ""
            de = _epoch_ms_to_local(it.get("endDate"))
            if de and de.date().isoformat() == date_str and (de.hour or de.minute):
                end_time = de.strftime("%I:%M %p").lstrip("0")

            full = it.get("fullUrl") or ""
            url_str = (f"{self.store_root.rstrip('/')}{full}"
                       if full.startswith("/") else (full or self.url))

            desc = _strip_html(it.get("excerpt") or it.get("body") or "")
            if len(desc) > 400:
                desc = desc[:397] + "..."

            image = it.get("assetUrl") or ""

            key = f"{title.lower()}|{date_str}"
            if key in seen:
                continue
            seen.add(key)

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                end_time=end_time,
                location=self.name,
                area=self.area,
                description=desc,
                category=self.default_category,
                tags=list(self.default_tags),
                url=url_str,
                image=image,
            ))

        print(f"  [{self.name}] {len(events)} event(s) from "
              f"{len(upcoming)} upcoming record(s)")
        return events

    def parse(self, soup) -> list[dict]:
        return []


class GoldenEraScraper(SquarespaceEventsScraper):
    """Golden Era Cocktail Bar & Lounge — historic Nevada City saloon
    on Broad Street; live music several nights a week."""
    name             = "Golden Era Lounge"
    url              = "https://www.goldeneralounge.com/events"
    store_root       = "https://www.goldeneralounge.com"
    events_path      = "/events"
    area             = "Nevada City"
    default_category = "Music event"
    default_tags     = ["Music"]

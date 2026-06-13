"""
Trumba community-calendar scraper (base class)
==============================================
Trumba is a hosted calendar product. Several Nevada County community
calendars run on it, each identified by a `webName`, and Trumba publishes
a machine-readable JSON feed for every public calendar at a predictable
URL:

    https://www.trumba.com/calendars/<webName>.json

The public web page embeds the calendar with a spud:

    $Trumba.addSpud({ webName: "<webName>", ... })

so to add a new Trumba calendar you only need its webName (view-source on
the calendar page and grep for `webName`).

Known Nevada County Trumba calendars:
    nevada-county-arts-council   NCAC arts & culture calendar
    nevada-city-chamber          Nevada City Chamber community calendar

These calendars are CONSOLIDATORS — they aggregate events from many
organizers and overlap each other heavily (≈half their events are shared)
and overlap our direct scrapers. They therefore run late in ALL_SCRAPERS,
and merge() dedupes by (title, date, area) across sources so the direct
copy wins. Each Trumba event's permaLinkUrl points back at its own
calendar, so different calendars give the same event different URLs — which
is exactly why URL dedup isn't enough and the title+date+area pass exists.

This base class holds all the parsing; concrete calendars are a few lines
of config (see NCACCalendarScraper, NevadaCityChamberScraper).
"""
from __future__ import annotations
import html
from datetime import datetime, timedelta, date

import requests
from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS

_MAX_FUTURE_DAYS = 480     # ≈16 months — pagination horizon
_MAX_PAGES       = 12      # safety cap on pagination loop

# Western Nevada County only (drop Truckee / Palisades Tahoe / etc.)
_KEEP_CITIES = {
    "nevada city", "grass valley", "north san juan",
    "penn valley", "rough and ready", "rough & ready",
    "cedar ridge", "washington", "graniteville",
    "alta sierra", "lake of the pines", "smartsville",
}

# Map Trumba "Type of event" values onto our internal categories
_TRUMBA_CATEGORY_MAP = {
    "art & gallery":       "Art event",
    "visual arts":         "Art event",
    "music":               "Music event",
    "music / concert":     "Music event",
    "theatre":             "Theatre",
    "theater":             "Theatre",
    "dance":               "Dance",
    "film":                "Film",
    "literary arts":       "Literary",
    "outdoors / recreation": "Outdoor",
    "children / family":   "Family",
    "workshop":            "Workshop",
    "conference / lecture / workshop": "Workshop",
    "beer / wine / food":  "Food event",
    "history / heritage":  "Heritage",
    "fundraiser":          "Fundraiser",
    "health / wellbeing":  "Wellness",
    "community":           "Community",
}


def _strip_html(s: str) -> str:
    """Trumba returns HTML in description/location fields. Flatten it."""
    if not s:
        return ""
    text = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    return html.unescape(text)


def _pick_category(type_value: str) -> str:
    v = (type_value or "").lower()
    for key, cat in _TRUMBA_CATEGORY_MAP.items():
        if key in v:
            return cat
    return "Art event"


def _pick_area(city_value: str) -> str:
    c = (city_value or "").strip().lower()
    if "nevada city" in c:    return "Nevada City"
    if "grass valley" in c:   return "Grass Valley"
    if "north san juan" in c: return "North San Juan"
    if "penn valley" in c:    return "Penn Valley"
    if "rough" in c:          return "Rough & Ready"
    return "Nevada County"


class TrumbaCalendarScraper(EventScraper):
    """Base for any Trumba-backed community calendar. Subclasses set
    `name`, `url`, and `web_name`; everything else is inherited."""

    # ── Subclass contract ─────────────────────────────────────────────────────
    web_name: str = ""          # Trumba calendar webName (required)
    default_category = "Art event"
    keep_cities = _KEEP_CITIES  # override per calendar if needed

    skip_rss       = True   # we hit Trumba JSON directly
    skip_selenium  = True   # never need a browser

    @property
    def feed_url(self) -> str:
        return f"https://www.trumba.com/calendars/{self.web_name}.json"

    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        if not self.web_name:
            print(f"  [{self.name}] no web_name configured — skipping")
            return []
        print(f"  [{self.name}] -> {self.feed_url}  (Trumba JSON feed, paginated)")

        # ── Paginated fetch: Trumba returns ~200 events/call; page forward by
        # setting startdate to the day after the latest event seen.
        raw: dict = {}
        cursor = date.today()
        horizon = date.today() + timedelta(days=_MAX_FUTURE_DAYS)
        for page in range(_MAX_PAGES):
            qs = cursor.strftime("%Y%m%d")
            try:
                resp = requests.get(f"{self.feed_url}?startdate={qs}",
                                    headers=_REQUESTS_HEADERS, timeout=20)
                resp.raise_for_status()
                batch = resp.json()
            except Exception as e:
                print(f"  [{self.name}] page {page+1} fetch failed: {e}")
                break
            if not batch:
                break
            new_count = 0
            latest_seen = cursor
            for ev in batch:
                eid = ev.get("eventID")
                if eid and eid not in raw:
                    raw[eid] = ev
                    new_count += 1
                start_str = (ev.get("startDateTime") or "")[:10]
                if start_str:
                    try:
                        d = datetime.strptime(start_str, "%Y-%m-%d").date()
                        if d > latest_seen:
                            latest_seen = d
                    except Exception:
                        pass
            print(f"  [{self.name}] page {page+1}: {len(batch)} returned, "
                  f"{new_count} new, cursor -> {latest_seen}")
            if new_count == 0 or latest_seen <= cursor or latest_seen >= horizon:
                break
            cursor = latest_seen + timedelta(days=1)

        data = list(raw.values())
        if not data:
            return []

        if discover:
            import os, json
            from .base import SNAPSHOT_DIR
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            fname = self.web_name + ".json"
            with open(os.path.join(SNAPSHOT_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  [{self.name}] Snapshot saved -> snapshots/{fname}")

        events = []
        cutoff = datetime.now() + timedelta(days=_MAX_FUTURE_DAYS)
        today  = datetime.now().date()
        seen   = set()

        for ev in data:
            title = html.unescape((ev.get("title") or "").strip())
            if not title:
                continue

            cf = {}
            for f in ev.get("customFields", []) or []:
                lbl = (f.get("label") or "").strip().lower()
                val = _strip_html(f.get("value") or "")
                if lbl and val:
                    cf[lbl] = val

            # Geographic filter (western Nevada County only)
            city_raw = cf.get("city/area") or cf.get("city / area") or cf.get("city") or ""
            city_lc  = city_raw.lower()
            if city_lc and not any(ok in city_lc for ok in self.keep_cities):
                continue
            # No city set → allow through (calendar's own events often have none)

            # Date / time
            start = ev.get("startDateTime") or ""
            date_str, time_str = "", ""
            if start:
                try:
                    dt = datetime.strptime(start[:19], "%Y-%m-%dT%H:%M:%S")
                    if dt.date() < today:
                        continue
                    if dt > cutoff:
                        continue
                    date_str = dt.strftime("%Y-%m-%d")
                    if not ev.get("allDay") and (dt.hour or dt.minute):
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    continue

            end_time = ""
            end_raw = ev.get("endDateTime") or ""
            if end_raw and time_str:
                try:
                    dt_e = datetime.strptime(end_raw[:19], "%Y-%m-%dT%H:%M:%S")
                    if dt_e.date().isoformat() == date_str:
                        end_time = dt_e.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass

            desc = (cf.get("event description")
                    or cf.get("event details")
                    or _strip_html(ev.get("description") or ""))
            if desc and len(desc) > 400:
                desc = desc[:397] + "..."

            venue    = cf.get("venue") or cf.get("event location") or ""
            location = venue or _strip_html(ev.get("location") or "")
            location = html.unescape(location)
            if location and len(location) > 120:
                location = location.split(",")[0][:120]

            category = _pick_category(cf.get("type of event") or cf.get("type") or "")
            area     = _pick_area(city_raw)

            image = ""
            img_obj = ev.get("eventImage") or ev.get("detailImage") or {}
            if isinstance(img_obj, dict):
                image = img_obj.get("url", "") or ""

            url_str = ev.get("permaLinkUrl") or self.url

            key = f"{title.lower()}|{date_str}"
            if key in seen:
                continue
            seen.add(key)

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                end_time=end_time,
                location=location,
                description=desc,
                area=area,
                category=category,
                url=url_str,
                image=image,
            ))

        print(f"  [{self.name}] {len(events)} event(s) from Trumba feed")
        return events

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        return []   # never called — scrape() is overridden

"""
Nevada County Arts Council — Arts & Culture Calendar
URL (public page): https://www.nevadacountyarts.org/calendar/

NCAC describes their calendar as "the most comprehensive, accurate, and
up-to-date calendar of arts & culture events in Nevada County" — they
sync with community calendars (gonevadacounty.com, chambers).

DATA SOURCE
===========
The public page embeds a Trumba calendar widget (a SaaS calendar product).
The page's HTML contains:
    $Trumba.addSpud({ webName: "nevada-county-arts-council", ... })

Trumba publishes machine-readable feeds for every public calendar at
predictable URLs. We hit the JSON feed directly — bypassing the embed:

    https://www.trumba.com/calendars/nevada-county-arts-council.json

PAGINATION
==========
Each call returns at most ~200 events from `startdate` forward. We page
forward by setting startdate to the day after the latest event in the
previous batch, until either an empty response or we exceed 16 months
ahead. Empirically this yields ~600+ events spanning 16 months.

Each event contains rich structured data: title, startDateTime/endDateTime,
description, location, eventImage, customFields (Type of event, City/Area,
Price, Age range, Venue), permaLinkUrl, etc.

We filter to western Nevada County (Nevada City, Grass Valley, North San
Juan, Penn Valley, Rough & Ready, Cedar Ridge); Truckee/Tahoe events are
dropped because they are far outside our target area.
"""

from __future__ import annotations
import re, html, requests
from datetime import datetime, timedelta, date

from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS

_FEED_URL = "https://www.trumba.com/calendars/nevada-county-arts-council.json"
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
    """Map a Trumba 'Type of event' value to our category vocabulary."""
    v = (type_value or "").lower()
    for key, cat in _TRUMBA_CATEGORY_MAP.items():
        if key in v:
            return cat
    return "Art event"


def _pick_area(city_value: str) -> str:
    """Normalize Trumba City/Area values to our area labels."""
    c = (city_value or "").strip().lower()
    if "nevada city" in c:    return "Nevada City"
    if "grass valley" in c:   return "Grass Valley"
    if "north san juan" in c: return "North San Juan"
    if "penn valley" in c:    return "Penn Valley"
    if "rough" in c:          return "Rough & Ready"
    return "Nevada County"


class NCACCalendarScraper(EventScraper):
    name           = "NCAC Calendar"
    url            = "https://www.nevadacountyarts.org/calendar/"
    skip_rss       = True   # we hit Trumba JSON directly in scrape()
    skip_selenium  = True   # never need a browser

    # ── Override scrape() entirely — we don't need HTML parsing ──────────────
    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        print(f"  [{self.name}] -> {_FEED_URL}  (Trumba JSON feed, paginated)")

        # ── Paginated fetch ─────────────────────────────────────────────────
        # Trumba returns up to ~200 events per call. We page forward by
        # setting startdate to the day after the latest event seen, until
        # either we get an empty page or we exceed _MAX_FUTURE_DAYS.
        raw = {}
        cursor = date.today()
        horizon = date.today() + timedelta(days=_MAX_FUTURE_DAYS)
        for page in range(_MAX_PAGES):
            qs = cursor.strftime("%Y%m%d")
            try:
                resp = requests.get(
                    f"{_FEED_URL}?startdate={qs}",
                    headers=_REQUESTS_HEADERS, timeout=20,
                )
                resp.raise_for_status()
                batch = resp.json()
            except Exception as e:
                print(f"  [{self.name}] Page {page+1} fetch failed: {e}")
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
            path = os.path.join(SNAPSHOT_DIR, "ncac_calendar.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  [{self.name}] Snapshot saved -> snapshots/ncac_calendar.json")

        events = []
        cutoff = datetime.now() + timedelta(days=_MAX_FUTURE_DAYS)
        today  = datetime.now().date()
        seen   = set()

        for ev in data:
            # Trumba returns HTML-encoded entities in titles (&#8220; &amp; etc.) —
            # unescape so users see proper quotes/dashes/ampersands.
            title = html.unescape((ev.get("title") or "").strip())
            if not title:
                continue

            # ── Custom fields ────────────────────────────────────────────────
            cf = {}
            for f in ev.get("customFields", []) or []:
                lbl = (f.get("label") or "").strip().lower()
                val = _strip_html(f.get("value") or "")
                if lbl and val:
                    cf[lbl] = val

            # ── Geographic filter (western Nevada County only) ──────────────
            city_raw = cf.get("city/area") or cf.get("city / area") or cf.get("city") or ""
            city_lc  = city_raw.lower()
            if city_lc and not any(ok in city_lc for ok in _KEEP_CITIES):
                # Outside our area (Truckee, Tahoe, etc.) — drop
                continue
            # If no city set, allow it through (NCAC's own events have none)

            # ── Date / time ──────────────────────────────────────────────────
            start = ev.get("startDateTime") or ""
            date_str, time_str = "", ""
            if start:
                try:
                    dt = datetime.strptime(start[:19], "%Y-%m-%dT%H:%M:%S")
                    if dt.date() < today:
                        continue   # past event
                    if dt > cutoff:
                        continue   # too far in future
                    date_str = dt.strftime("%Y-%m-%d")
                    if not ev.get("allDay") and (dt.hour or dt.minute):
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    continue

            # ── End time ─────────────────────────────────────────────────────
            end_time = ""
            end_raw = ev.get("endDateTime") or ""
            if end_raw and time_str:
                try:
                    dt_e = datetime.strptime(end_raw[:19], "%Y-%m-%dT%H:%M:%S")
                    # Only show end-time when same day (otherwise it's a date range)
                    if dt_e.date().isoformat() == date_str:
                        end_time = dt_e.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass

            # ── Description ─────────────────────────────────────────────────
            desc = (cf.get("event description")
                    or cf.get("event details")
                    or _strip_html(ev.get("description") or ""))
            if desc and len(desc) > 400:
                desc = desc[:397] + "..."

            # ── Location ────────────────────────────────────────────────────
            venue    = cf.get("venue") or cf.get("event location") or ""
            location = venue or _strip_html(ev.get("location") or "")
            location = html.unescape(location)
            if location and len(location) > 120:
                # When raw HTML address is too long, keep just the first line
                location = location.split(",")[0][:120]

            # ── Category / Area ─────────────────────────────────────────────
            category = _pick_category(cf.get("type of event") or cf.get("type") or "")
            area     = _pick_area(city_raw)

            # ── Image ───────────────────────────────────────────────────────
            image = ""
            img_obj = ev.get("eventImage") or ev.get("detailImage") or {}
            if isinstance(img_obj, dict):
                image = img_obj.get("url", "") or ""

            # ── URL: prefer NCAC permalink so user lands back on the calendar
            url_str = ev.get("permaLinkUrl") or self.url

            # ── Dedup on title+date ─────────────────────────────────────────
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

    # parse() never called (we override scrape) but keep stub for safety
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        return []

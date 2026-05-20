"""
Nevada County Fairgrounds -- Event Scraper
===========================================
nevadacountyfair.com runs on Saffire (a SaaS used by US fairgrounds and
event venues). The site exposes a public JSONP web service that returns
the featured-events list -- the same Strawberry / Father's Day Bluegrass
/ Nevada County Fair / Draft Horse Classic / Country Christmas Faire
records the homepage shows:

    https://www.nevadacountyfair.com/services/eventsservice.asmx/GetEventsJsonP

Response shape (wrapped in saffireEvents([...]);):
    {
      "Name": "Draft Horse Classic & Harvest Fair",
      "Date": "Sept 17 - Sept 20, 2026",
      "URL":  "" | "https://...",
      "ImageURL": "https://cdn.saffire.com/..." | "",
      "Description": "" | "...",
      "LongDescription": null | "...",
      "Purchaseable": false
    }

Date strings are free-text English ranges. Observed formats:
    "Sept 05, 2026"                  -- single day
    "Sept 17 - Sept 20, 2026"        -- range, abbreviated month
    "Aug 12 - Aug 16, 2026"          -- range, same month
    "May 21 - May 24, 2026"          -- range
    "Dec 30, 2025 - Jan 2, 2026"     -- (defensive) cross-year range

The scraper emits one event per record, anchored on the start date; the
human-readable range becomes the description so multi-day fairs read
naturally in the UI.
"""
from __future__ import annotations
import json, os, re, requests
from datetime import date, timedelta

from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS, SNAPSHOT_DIR


_API = "https://www.nevadacountyfair.com/services/eventsservice.asmx/GetEventsJsonP"
_FALLBACK_URL = "https://www.nevadacountyfair.com/events/"
_LOCATION   = "Nevada County Fairgrounds"
_AREA       = "Grass Valley"
_MAX_FUTURE_DAYS = 480

# Saffire wraps the JSON array in a JSONP callback: saffireEvents([...]);
_JSONP_RE = re.compile(r"^[^(]*\((.*)\)\s*;?\s*$", re.S)

# Range separator may be hyphen or en-dash
_RANGE_SPLIT_RE = re.compile(r"\s*[–—-]\s*")

# Trailing 4-digit year (always present in observed Saffire dates)
_YEAR_TAIL_RE = re.compile(r"(\d{4})\s*$")


def _parse_date_range(raw: str) -> tuple[str, str]:
    """
    Parse Saffire's free-text date strings into (start_iso, end_iso).
    Single-day events return the same date in both slots.
    Returns ("", "") if the string can't be parsed.
    """
    if not raw:
        return "", ""
    s = raw.strip()
    m_year = _YEAR_TAIL_RE.search(s)
    if not m_year:
        return "", ""
    year = int(m_year.group(1))
    body = s[: m_year.start()].rstrip().rstrip(",").strip()

    parts = _RANGE_SPLIT_RE.split(body, maxsplit=1)

    if len(parts) == 1:
        try:
            d = dateparser.parse(f"{body} {year}").date()
            iso = d.isoformat()
            return iso, iso
        except Exception:
            return "", ""

    left  = parts[0].strip().rstrip(",")
    right = parts[1].strip().rstrip(",")

    try:
        start = dateparser.parse(f"{left} {year}").date()
    except Exception:
        return "", ""

    try:
        end = dateparser.parse(f"{right} {year}").date()
    except Exception:
        end = start

    # Cross-year range: "Dec 30, 2025 - Jan 2, 2026" parses both into 2026
    # by default; if end < start, the start was actually the previous year.
    if end < start:
        try:
            start = dateparser.parse(f"{left} {year - 1}").date()
        except Exception:
            pass

    return start.isoformat(), end.isoformat()


class FairgroundsScraper(EventScraper):
    """Nevada County Fairgrounds via Saffire eventsservice.asmx JSONP."""

    name          = "Nevada County Fairgrounds"
    url           = "https://www.nevadacountyfair.com/events/"
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        print(f"  [{self.name}] -> {_API}  (Saffire JSONP)")
        try:
            resp = requests.get(_API, headers=_REQUESTS_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [{self.name}] HTTP error: {e}")
            return []

        body = resp.text.strip()
        m = _JSONP_RE.match(body)
        payload = m.group(1) if m else body
        try:
            raw = json.loads(payload)
        except Exception as e:
            print(f"  [{self.name}] JSON parse error: {e}")
            return []

        if discover:
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            fn = "nevada_county_fairgrounds_events.json"
            with open(os.path.join(SNAPSHOT_DIR, fn), "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
            print(f"  [{self.name}] Snapshot saved -> snapshots/{fn}")

        today  = date.today()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)

        events = []
        for ev in raw:
            title = (ev.get("Name") or "").strip()
            if not title:
                continue

            raw_date = (ev.get("Date") or "").strip()
            start_iso, end_iso = _parse_date_range(raw_date)
            if not start_iso:
                continue

            try:
                start_dt = date.fromisoformat(start_iso)
                end_dt   = date.fromisoformat(end_iso)
            except ValueError:
                continue

            if end_dt < today or start_dt > cutoff:
                continue

            # Description: human-readable range + LongDescription if any
            pieces = []
            if start_iso != end_iso:
                pieces.append(raw_date)
            long_desc = (ev.get("LongDescription") or ev.get("Description") or "").strip()
            if long_desc:
                pieces.append(long_desc)
            description = " - ".join(pieces)

            url   = (ev.get("URL") or "").strip() or _FALLBACK_URL
            image = (ev.get("ImageURL") or "").strip()

            events.append(self.make_event(
                title=title,
                date=start_iso,
                location=_LOCATION,
                area=_AREA,
                description=description,
                category="Festival",
                url=url,
                image=image,
            ))

        print(f"  [{self.name}] {len(events)} event(s) from {len(raw)} record(s)")
        return events

    def parse(self, soup) -> list[dict]:
        return []

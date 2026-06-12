"""
Bear Yuba Land Trust (BYLT) -- Events Scraper
==============================================
bylt.org runs WordPress with the Event Organiser plugin, which exposes
a clean public iCal feed:

    https://www.bylt.org/?feed=eo-events

Each VEVENT carries SUMMARY, DTSTART/DTEND, DESCRIPTION, a per-event
URL (the /events/event/<slug>/ detail page), and usually an ATTACH
image. No LOCATION property — BYLT events happen on trails all over
western Nevada County, so location stays generic and the admin / AI
pass refines it.

Why not parse_ical()
--------------------
The base parse_ical() drops any event whose DTSTART is in the past —
but BYLT runs month-long programs (trail art installations, hike
challenges) that START before today and END weeks later. Those are
exactly the events a visitor can still join, so this scraper parses
VEVENTs itself: an ongoing event is kept and anchored to its END date
(stable dedup key, survives the nightly prune until it actually ends),
with the full run window stated in the description.
"""
from __future__ import annotations
import re
from datetime import datetime

import requests
from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS


_ORG     = "Bear Yuba Land Trust"
_LANDING = "https://www.bylt.org/events/"
_ICS_URL = "https://www.bylt.org/?feed=eo-events"

# Title keywords → (category, tags). First hit wins; default is Outdoors —
# BYLT programming is hikes, trail days, and nature events at heart.
_CATEGORY_RULES = [
    (re.compile(r"\bart\b|installation|gallery",            re.I), ("Art",         ["Art", "Outdoors"])),
    (re.compile(r"theatrical|theatre|theater|performance",  re.I), ("Performance", ["Performance", "Outdoors"])),
    (re.compile(r"party|celebration|festival",              re.I), ("Festival",    ["Festival", "Community"])),
    (re.compile(r"hike|walk|trail|trek|stroll",             re.I), ("Outdoors",    ["Outdoors", "Hiking"])),
]


def _unescape_ics(text: str) -> str:
    r"""iCal escapes: \, \; \n literals → real characters."""
    return (text.replace("\\n", " ").replace("\\,", ",")
                .replace("\\;", ";").replace("\\\\", "\\")).strip()


def _parse_dt(raw: str):
    """'20260601T070000' (after the colon) → datetime, or None."""
    if not raw:
        return None
    try:
        return dateparser.parse(raw.replace("T", " ").rstrip("Z"))
    except Exception:
        return None


class BYLTScraper(EventScraper):
    """Bear Yuba Land Trust — Event Organiser iCal feed."""

    name          = "Bear Yuba Land Trust"
    url           = _LANDING
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver, discover: bool = False) -> list[dict]:
        print(f"  [{self.name}] -> {_ICS_URL}  (Event Organiser iCal)")
        try:
            resp = requests.get(_ICS_URL, headers=_REQUESTS_HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  [{self.name}] HTTP {resp.status_code} — no events")
                return []
        except Exception as e:
            print(f"  [{self.name}] ICS fetch error: {e}")
            return []

        # Unfold continuation lines once, then walk VEVENT blocks.
        unfolded = re.sub(r"\r?\n[ \t]", "", resp.text)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        events = []
        for block in re.split(r"BEGIN:VEVENT", unfolded)[1:]:
            block = block.split("END:VEVENT")[0]

            def field(prop):
                m = re.search(rf"^{prop}[;:][^\r\n]*", block, re.M)
                return m.group(0).split(":", 1)[1].strip() if m else ""

            title = _unescape_ics(field("SUMMARY"))
            if not title:
                continue

            start = _parse_dt(field("DTSTART"))
            end   = _parse_dt(field("DTEND"))
            if start is None:
                continue
            start = start.replace(tzinfo=None)
            end   = end.replace(tzinfo=None) if end else start

            window = ""
            if end < today:
                continue                       # fully over
            elif start < today:
                # Ongoing multi-day program (installation, hike challenge).
                # Anchor to the END date: the key stays stable across scrapes
                # and the nightly prune keeps it until the window closes.
                date_str, time_str = end.strftime("%Y-%m-%d"), ""
                window = (f"On now through {end.strftime('%B %d').replace(' 0', ' ')}. ")
            else:
                date_str = start.strftime("%Y-%m-%d")
                time_str = start.strftime("%I:%M %p").lstrip("0")
                if time_str in ("12:00 AM",):   # all-day marker, not a real time
                    time_str = ""

            category, tags = "Outdoors", ["Outdoors", "Nature"]
            for rx, (cat, tg) in _CATEGORY_RULES:
                if rx.search(title):
                    category, tags = cat, tg
                    break

            desc = _unescape_ics(field("DESCRIPTION"))
            attach = field("ATTACH")            # usually the event image URL
            image = attach if attach.startswith("http") else ""

            events.append(self.make_event(
                title       = title,
                date        = date_str,
                time        = time_str,
                location    = _ORG,
                description = (window + (desc or f"{_ORG} event. {title}."))[:400],
                url         = field("URL") or _LANDING,
                category    = category,
                tags        = tags,
                image       = image,
            ))

        print(f"  [{self.name}] {len(events)} event(s) kept")
        return events

    def parse(self, soup):
        """Unused — scrape() pulls the iCal feed directly."""
        return []

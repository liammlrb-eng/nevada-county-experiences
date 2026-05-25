"""
Gold Vibe Hard Kombucha (Taproom) -- Calendar Scraper
======================================================
goldvibe.com/pages/food-1 embeds a public Google Calendar via
iframe. The same calendar exposes a free public ICS feed:

    https://calendar.google.com/calendar/ical/<calendar-id>/public/basic.ics

The calendar carries ~800 historical entries — mostly food trucks
(Vegan Circus, ZALT BBQ, Fire Goddess Pizza, Cousins Maine Lobster,
etc.) — interspersed with the music + entertainment events we want
(Argentine Tango nights, line dancing, open jam, karaoke).

Filter strategy
---------------
Because the calendar mixes food vendors and music acts in one
stream, we use an inclusion-only filter: keep events whose title
matches a music / dance / community-event keyword. Everything
else is treated as a food-truck rotation and skipped — those
don't belong in the public events grid.
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta

import requests

from .base import EventScraper, _REQUESTS_HEADERS


_VENUE   = "Gold Vibe Hard Kombucha"
_ADDRESS = "12615 Charles Dr, Grass Valley, CA"
_LANDING = "https://www.goldvibe.com/pages/food-1"
_CAL_ID  = "c_f4c16d66db5d8547d035349e757833001c1a94884fed2173559a8a0cd16d8945@group.calendar.google.com"
_ICS_URL = f"https://calendar.google.com/calendar/ical/{_CAL_ID}/public/basic.ics"

# Title keywords that mark an event as music / dance / community
# programming (vs. a food-truck rotation). Case-insensitive
# word-boundary match; one hit qualifies the entry.
_MUSIC_KEYWORDS = re.compile(
    r"\b(?:music|live|jam|mic|band|concert|dj|karaoke|"
    r"dance|dancing|tango|salsa|swing|bluegrass|"
    r"jazz|blues|folk|rock|country|acoustic|"
    r"songwriter|songwriters|"
    r"trivia|bingo|comedy|drag|movie|film|"
    r"festival|fest|"
    r"open\s+mic|open\s+jam|"
    r"line\s+dance|line\s+dancing)\b",
    re.I,
)


class GoldVibeScraper(EventScraper):
    """Gold Vibe Hard Kombucha — public Google Calendar ICS."""

    name          = "Gold Vibe Kombucha"
    url           = _LANDING
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver, discover: bool = False) -> list[dict]:
        """Pull the ICS feed directly; bypass the iframe-fronted landing page."""
        print(f"  [{self.name}] -> {_ICS_URL}  (Google Calendar ICS)")
        try:
            resp = requests.get(_ICS_URL, headers=_REQUESTS_HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  [{self.name}] HTTP {resp.status_code} — no events")
                return []
        except Exception as e:
            print(f"  [{self.name}] ICS fetch error: {e}")
            return []

        events = self.parse_ical(resp.text)

        # Augment + filter:
        #  1) keep only music / community programming (skip food trucks)
        #  2) drop past-dated entries (parse_ical does today onwards already)
        #  3) inject venue + image fallback
        kept = []
        today = datetime.now().date()
        future_cap = today + timedelta(days=365)
        for ev in events:
            title = ev.get("title", "")
            if not _MUSIC_KEYWORDS.search(title):
                continue

            d = ev.get("date", "")
            try:
                d_obj = datetime.strptime(d, "%Y-%m-%d").date()
                if d_obj > future_cap:
                    continue
            except Exception:
                pass

            ev["location"]    = _VENUE + " · " + _ADDRESS
            ev["area"]        = "Grass Valley"
            ev["category"]    = "Music"
            ev["source"]      = self.name
            ev["source_url"]  = _LANDING
            ev["url"]         = ev.get("url") or _LANDING
            # parse_ical's bare description is often empty for Google Calendar
            # entries — prefix the venue so the auto_tagger reliably tags Music.
            base_desc = ev.get("description") or ""
            ev["description"] = f"Live at {_VENUE}. {base_desc}".strip()[:400]

            kept.append(ev)

        print(f"  [{self.name}] {len(kept)} kept (of {len(events)} from ICS)")
        return kept

    def parse(self, soup):
        """Unused — scrape() pulls ICS directly."""
        return []

"""
Wild Eye Pub -- Live Music Calendar Scraper
=============================================
wildeyepub.com is a Wix site. The pub's ticketed concerts are
published on /tickets-1 (the /events page is empty — the venue
funnels ticket sales through the tickets-1 page instead).

Like Nevada City Winery's site, the page embeds a Wix Events
hydration payload:

    "events":[{ ... }, { ... }, ...]

Unlike NC Winery, Wild Eye's events use the structured datetime
fields — `scheduling.config.startDate` is a real ISO timestamp
with timezone info. That makes parsing simpler: no TBD-message
regex needed.

Schema notes (per /tickets-1, May 2026):
    title             -> "Silas Lowe on tour"
    slug              -> "silas-lowe-on-tour"
    description       -> full plain-text description
    scheduling.config.startDate     -> "2026-06-06T01:30:00.000Z"  (UTC)
    scheduling.config.endDate       -> "2026-06-06T03:30:00.000Z"
    scheduling.config.timeZoneId    -> "America/Los_Angeles"
    scheduling.startDateFormatted   -> "June 5, 2026"      (already localised)
    scheduling.startTimeFormatted   -> "6:30 PM"
    location.address                -> street address
    mainImage.url                   -> hero image
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper


_VENUE   = "Wild Eye Pub"
_ADDRESS = "535 Mill St, Grass Valley, CA 95945"
_SOURCE  = "https://www.wildeyepub.com/tickets-1"
_BASE    = "https://www.wildeyepub.com"


def _extract_events_json(html: str) -> list[dict]:
    """Bracket-balanced grab of the `"events":[ ... ]` array from page HTML."""
    idx = html.find('"events":[')
    if idx < 0:
        return []
    start = idx + len('"events":')
    depth = 0
    end = None
    for i in range(start, min(start + 2_000_000, len(html))):
        c = html[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return []
    try:
        return json.loads(html[start:end])
    except Exception:
        return []


class WildEyePubScraper(EventScraper):
    """Wild Eye Pub — Wix Events on the /tickets-1 page (structured dates)."""

    name          = "Wild Eye Pub"
    url           = _SOURCE
    wait_css      = "body"
    skip_rss      = True
    skip_selenium = True

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        html = str(soup)
        records = _extract_events_json(html)
        if not records:
            return []

        events = []
        today      = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        future_cap = today + timedelta(days=365)

        for rec in records:
            title = (rec.get("title") or "").strip()
            if not title:
                continue

            sched = (rec.get("scheduling") or {})
            cfg = sched.get("config") or {}
            start_iso = cfg.get("startDate") or ""

            # If structured startDate is missing, fall back to the formatted
            # strings — but for Wild Eye in practice startDate is always set.
            date_str, time_str = "", ""
            if start_iso:
                try:
                    dt_utc = dateparser.parse(start_iso)
                    if dt_utc:
                        # Convert to Pacific for display. Wix stores UTC in
                        # startDate and the human-meant local time is the
                        # value the venue typed; converting UTC→America/LA
                        # gives us back the local hour.
                        from datetime import timezone as _tz, timedelta as _td
                        pac = _tz(_td(hours=-7))   # PDT; fine for this scope
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=_tz.utc)
                        dt_local = dt_utc.astimezone(pac)
                        date_str = dt_local.strftime("%Y-%m-%d")
                        time_str = dt_local.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass
            if not date_str:
                # Wix-provided pre-formatted strings as a last resort.
                d_fmt = sched.get("startDateFormatted") or ""
                t_fmt = sched.get("startTimeFormatted") or ""
                try:
                    dt = dateparser.parse(f"{d_fmt} {t_fmt}")
                    if dt:
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass
            if not date_str:
                continue

            try:
                event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if event_dt < today or event_dt > future_cap:
                    continue
            except Exception:
                continue

            # Image
            image = ""
            main_img = rec.get("mainImage") or {}
            if isinstance(main_img, dict):
                image = main_img.get("url") or ""
                if image and not image.startswith("http"):
                    image = f"https://static.wixstatic.com/media/{image}"

            # Detail page URL
            slug = rec.get("slug") or ""
            event_url = urljoin(f"{_BASE}/event-details/", slug) if slug else _SOURCE

            # Description
            desc = (rec.get("description") or "").strip()
            if not desc:
                desc = (rec.get("about") or "").strip()
            description = f"Live music at {_VENUE}. {desc}".strip()

            events.append(self.make_event(
                title       = f"{title} at {_VENUE}",
                date        = date_str,
                time        = time_str,
                location    = _VENUE + " · " + _ADDRESS,
                description = description[:400],
                url         = event_url,
                category    = "Music",
                tags        = ["Music"],
                image       = image,
                area        = "Grass Valley",
            ))

        return events

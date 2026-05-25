"""
Nevada City Winery -- Events Scraper
=====================================
ncwinery.com/events runs on Wix Events. The events list is server-
rendered into the page HTML as a JSON blob embedded in a `<script>`
tag (the Wix Events widget hydration payload). We don't need to
parse HTML cards — we pull the JSON directly.

Where the JSON lives
--------------------
Inside the page HTML you'll find:
    "events":[{ ... event 1 ... }, { ... event 2 ... }, ...]

Each event is a Wix Events object with a `title`, `slug`,
`mainImage`, `location`, and a `scheduling` block that, on this
particular winery's site, almost always uses the TBD-message
convention to encode the date:

    scheduling.config.scheduleTbdMessage  →  "Sunday, May 24th, 3:00 - 5:00 PM"

Wix stores it as a free-text "to be determined" message rather than
the structured start/end-date fields, so we parse the message with
a regex.

Skipped event types
-------------------
A handful of entries use the message field for things that aren't
calendar-able:
    - "Available by Reservation"        (Tour & Tasting bookings)
    - "First Wednesday of Each Month"   (book club — recurring)
    - "Every Third Tuesday of the Month!" (Spring Street Swing Out)
    - "On Display Through June 29th"    (art exhibit — range)
These are skipped — they belong in EXPERIENCES (recurring) or are
not visit-driving for the public events grid.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper


_VENUE   = "Nevada City Winery"
_ADDRESS = "321 Spring St, Nevada City, CA 95959"
_SOURCE  = "https://www.ncwinery.com/events"

# "Sunday, May 24th, 3:00 - 5:00 PM"  →  groups: weekday, month, day, start_time
_TBD_MSG_RE = re.compile(
    r"""
    (?:Sun|Mon|Tues?|Wed|Thurs?|Fri|Sat)[a-z]*,?\s+
    (?P<month>January|February|March|April|May|June|July|August|September|October|November|December)
    \s+
    (?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+
    (?P<hour>\d{1,2}):(?P<minute>\d{2})
    \s*
    (?P<ampm1>[AP]M)?           # rare; usually omitted on start
    \s*[-–]\s*
    (?P<endhour>\d{1,2}):(?P<endminute>\d{2})\s*
    (?P<ampm2>[AP]M)            # always present on end
    """,
    re.I | re.X,
)

# These TBD-message strings are explicitly non-calendar (recurring rules,
# "by reservation", or display ranges). Skip outright.
_SKIP_PATTERNS = re.compile(
    r"by reservation|first \w+ of each month|every \w+ \w+ of the month|"
    r"on display through|tba|tbd",
    re.I,
)


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


def _parse_tbd_date(message: str, today: datetime) -> tuple[str, str]:
    """
    Parse a Wix TBD-message date string like 'Sunday, May 24th, 3:00 - 5:00 PM'
    into (YYYY-MM-DD, '3:00 PM'). The start time often omits its AM/PM —
    we inherit it from the end time when missing (winery shows are
    matinee-leaning so the same period almost always applies).
    """
    m = _TBD_MSG_RE.search(message or "")
    if not m:
        return "", ""

    month  = m.group("month")
    day    = int(m.group("day"))
    hour   = int(m.group("hour"))
    minute = int(m.group("minute"))
    end_ampm   = m.group("ampm2").upper()
    start_ampm = (m.group("ampm1") or end_ampm).upper()

    # 12-hour → 24-hour
    h24 = hour
    if start_ampm == "PM" and hour != 12:
        h24 += 12
    elif start_ampm == "AM" and hour == 12:
        h24 = 0

    # Year inference: try current year, roll forward if past.
    year = today.year
    try:
        dt = dateparser.parse(f"{month} {day} {year} {h24:02d}:{minute:02d}")
        if dt and dt.date() < today.date():
            year += 1
            dt = dateparser.parse(f"{month} {day} {year} {h24:02d}:{minute:02d}")
    except Exception:
        return "", ""
    if not dt:
        return "", ""

    return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip("0")


class NevadaCityWineryScraper(EventScraper):
    """Nevada City Winery — Wix Events JSON embedded in /events page."""

    name          = "Nevada City Winery"
    url           = _SOURCE
    wait_css      = "body"
    skip_rss      = True
    skip_selenium = True       # JSON sits inline in the static HTML

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        # soup is a BeautifulSoup view; the JSON lives in the raw HTML text.
        # Pull it back out via the soup's own decoded string.
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

            sched = (rec.get("scheduling") or {}).get("config") or {}
            msg = (sched.get("scheduleTbdMessage") or "").strip()

            if _SKIP_PATTERNS.search(msg) or not msg:
                continue

            date_str, time_str = _parse_tbd_date(msg, today)
            if not date_str:
                continue

            try:
                event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if event_dt < today or event_dt > future_cap:
                    continue
            except Exception:
                continue

            # Image: Wix mainImage has a `url` field; sometimes `id` for CDN lookup
            image = ""
            main_img = rec.get("mainImage") or {}
            if isinstance(main_img, dict):
                image = main_img.get("url") or ""
                # Wix sometimes stores just the relative ID — prepend the CDN root.
                if image and not image.startswith("http"):
                    image = f"https://static.wixstatic.com/media/{image}"

            # Detail page slug → canonical URL
            slug = rec.get("slug") or ""
            event_url = urljoin("https://www.ncwinery.com/event-details/", slug) if slug else _SOURCE

            # Wix `about` field carries plain-text description; fallback to msg
            about = (rec.get("about") or "").strip() or msg
            description = f"Live music at {_VENUE}. {about}".strip()

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
                area        = "Nevada City",
            ))

        return events

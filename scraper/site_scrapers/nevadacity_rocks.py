"""
NevadaCity.Rocks -- Live Music Event Scraper
=============================================
nevadacity.rocks is a community-maintained live-music calendar for
Nevada City + Grass Valley. The site is an ASP.NET property with
clean, server-rendered HTML — a static `requests` fetch returns
the entire upcoming-events list in one shot. Typically 400+ events
covering the next ~6 months.

Source URL:
    https://nevadacity.rocks/live-music-in-nevada-city-grass-valley

Event card markup (one per <div class="GreyPanel">):
    <div class="GreyPanel">
      <div class="EventListImageBox">
        <img src="/UpldUsr/ProfileEvent/...jpg">
      </div>
      <div class="EventListDataBox">
        <div class="EventListBoxNameVenueArtist">
          <div class="EventListBoxName">
            <a href="/event/koa-and-dasty-island-at-friar-tucks-5/24/2026-5-30-pm">
              Koa and Dasty Island at Friar Tucks
            </a>
          </div>
          <div class="EventListBoxVenue">
            <a href="/venue/Friar-Tucks-...">Friar Tucks</a>
          </div>
          <div class="EventListBoxArtist">
            <a href="/performer/Koa-Musician-Profile">Koa</a>
          </div>
        </div>
        <div class="EventListDate">
          <span>Sun 24 May - 5.30p</span>
        </div>
        <div class="EventListDesc">Koa and Dasty Island at Friar Tucks</div>
      </div>
    </div>

Year inference
--------------
The event-link slug embeds the year via the path-with-slashes pattern
`.../M/D/YYYY-H-MM-am|pm` — we pull the year from there. This is more
robust than guessing from "Sun 24 May" alone, especially across the
December → January boundary. If no slug-year is found we fall back to:
  - the current year if the parsed date is still in the future, or
  - the next year if it's already past

Local filter
------------
Almost every venue on nevadacity.rocks is in Nevada County. We still
run the title+venue+location through the shared `_DISTANT_PLACES`
exclude list (used by the KVMR scraper) to defend against any rare
out-of-county listing.

Local-music tagging
-------------------
The auto-tagger's Music ruleset already covers most of these (band /
trio / artist@venue patterns). We additionally seed category="Music"
so the Music pill / vibe always matches even if the title is a bare
performer name.
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper


_BASE   = "https://nevadacity.rocks"
_SOURCE = "https://nevadacity.rocks/live-music-in-nevada-city-grass-valley"

# Out-of-county venues to skip. Keep aligned with KVMR's distant list —
# nevadacity.rocks does occasionally list a Tahoe / Reno / Sacramento
# venue when a local artist tours out. Title + venue are scanned.
_DISTANT_PLACES = {
    "sacramento", "reno", "tahoe city", "south lake tahoe", "incline village",
    "kings beach", "crystal bay", "chico", "oroville", "paradise",
    "downieville", "marysville", "yuba city", "placerville",
    "san francisco", "oakland", "berkeley", "napa", "sonoma",
}
_DISTANT_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _DISTANT_PLACES) + r")\b",
    re.I,
)

# Year inside a slug like ".../5/24/2026-5-30-pm" — look for /YYYY-
_YEAR_FROM_SLUG_RE  = re.compile(r"/(20\d{2})[-/]")
# Fallback: a bare 4-digit year tucked into the slug ("...-2026-at-...")
_YEAR_BARE_RE       = re.compile(r"\b(20\d{2})\b")

# Time formats observed: "5.30p", "11.00a", "5p", "8.00P"
# Day-Month formats observed: "Sun 24 May", "Fri 13 Nov"
_DATE_TEXT_RE = re.compile(
    r"""^\s*
        (?:[A-Za-z]{3}\s+)?               # optional weekday
        (?P<day>\d{1,2})\s+               # day-of-month
        (?P<month>[A-Za-z]{3,9})          # month name
        \s*-\s*                           # separator
        (?P<hour>\d{1,2})                 # hour
        (?:\.(?P<minute>\d{2}))?          # optional minute (dot-sep)
        \s*(?P<ampm>[ap])                 # a/p
    """,
    re.I | re.X,
)


def _infer_year(slug: str, today: datetime) -> int | None:
    """Pull year from the event-page slug. Returns None if not present."""
    m = _YEAR_FROM_SLUG_RE.search(slug)
    if m:
        return int(m.group(1))
    m = _YEAR_BARE_RE.search(slug)
    if m:
        return int(m.group(1))
    return None


def _parse_date_text(text: str, slug: str, today: datetime) -> tuple[str, str]:
    """
    Parse "Sun 24 May - 5.30p" → ("2026-05-24", "5:30 PM").
    Year comes from the slug when available; otherwise we pick the next
    occurrence (today or future).
    Returns ("", "") if the text doesn't match.
    """
    m = _DATE_TEXT_RE.match(text or "")
    if not m:
        return "", ""

    day      = int(m.group("day"))
    month    = m.group("month")
    hour     = int(m.group("hour"))
    minute   = int(m.group("minute") or 0)
    ampm     = m.group("ampm").lower()

    # 12-hour → 24-hour
    if ampm == "p" and hour != 12:
        hour += 12
    elif ampm == "a" and hour == 12:
        hour = 0

    year = _infer_year(slug, today)
    if year is None:
        # No slug-year → guess current year; if already past, roll forward.
        year = today.year
        try:
            candidate = dateparser.parse(f"{year}-{month}-{day} {hour:02d}:{minute:02d}")
            if candidate and candidate.date() < today.date():
                year += 1
        except Exception:
            pass

    try:
        dt = dateparser.parse(f"{year}-{month}-{day} {hour:02d}:{minute:02d}")
    except Exception:
        return "", ""
    if not dt:
        return "", ""

    return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip("0")


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def _is_local(title: str, venue: str) -> bool:
    """Reject any event whose title or venue names a non-local city."""
    text = (title or "") + " " + (venue or "")
    return not _DISTANT_RE.search(text)


class NevadaCityRocksScraper(EventScraper):
    """nevadacity.rocks live-music calendar — static HTML, ASP.NET."""

    name          = "NevadaCity.Rocks"
    url           = _SOURCE
    wait_css      = ".GreyPanel"
    skip_rss      = True       # no RSS on this site
    skip_selenium = True       # server-rendered; static fetch is fine

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []
        today      = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        future_cap = today + timedelta(days=365)

        # Each event lives inside its own .GreyPanel. There are also non-event
        # .GreyPanel blocks (in-house ads etc.), so we key off the presence of
        # an inner .EventListBoxName anchor.
        for panel in soup.select("div.GreyPanel"):
            name_a = panel.select_one("div.EventListBoxName a")
            if not name_a:
                continue   # ad block, skip

            title = _text(name_a)
            if not title:
                continue

            event_url = name_a.get("href", "")
            if event_url:
                event_url = urljoin(_BASE + "/", event_url)

            venue_a    = panel.select_one("div.EventListBoxVenue a")
            artist_a   = panel.select_one("div.EventListBoxArtist a")
            date_span  = panel.select_one("div.EventListDate span")
            desc_div   = panel.select_one("div.EventListDesc")
            img_tag    = panel.select_one("div.EventListImageBox img")

            venue   = _text(venue_a)
            artist  = _text(artist_a)
            datetxt = _text(date_span)
            desc    = _text(desc_div) or title

            # Local guard
            if not _is_local(title, venue):
                continue

            date_str, time_str = _parse_date_text(datetxt, event_url, today)
            if not date_str:
                continue

            # Window: today through +365 days
            try:
                event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if event_dt < today or event_dt > future_cap:
                    continue
            except Exception:
                continue

            # Image — site serves relative paths from /Img/... or /UpldUsr/...
            image = ""
            if img_tag and img_tag.get("src"):
                image = urljoin(_BASE + "/", img_tag["src"])

            # Build a richer description. nevadacity.rocks is exclusively a
            # live-music calendar, so we prefix "Live music at {venue}" both
            # to communicate the event type to readers and to give the
            # auto_tagger a reliable Music signal regardless of which venue
            # appears (otherwise we'd need per-venue regex patterns).
            description = desc
            if artist and artist.lower() not in description.lower():
                description = f"{description} — featuring {artist}"
            if venue:
                description = f"Live music at {venue}. {description}"
            else:
                description = f"Live music. {description}"

            events.append(self.make_event(
                title       = title,
                date        = date_str,
                time        = time_str,
                location    = venue,
                description = description[:400],
                url         = event_url,
                category    = "Music",
                image       = image,
                area        = "Nevada County",
            ))

        return events

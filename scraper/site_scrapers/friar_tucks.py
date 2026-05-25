"""
Friar Tuck's Restaurant -- Live Music Calendar Scraper
=======================================================
friartucks.com/pages/calendar is a hand-curated calendar page on
Shopify. The HTML is server-rendered; each upcoming date appears
as a `.ft-cal-day-row` block containing 1+ `.ft-cal-show` cards.

Markup pattern (one day):
    <div class="ft-cal-day-row">
      <div>...</div>
        <div>May</div>     ← month name
        <div>19</div>      ← day-of-month
        <div>Tue</div>     ← weekday
      </div>
      <div class="ft-cal-show" data-artist-genre="R&B / Soul">
        <img alt="Aedryan Gantt" src="...">
        <div>Aedryan Gantt</div>
        <div>R&amp;B / Soul</div>
        <div>5:00 PM - 8:00 PM</div>
      </div>
      ... more shows on the same day ...
    </div>

The page typically shows about 2 weeks ahead (~11 day rows, ~15
shows). Less coverage than NevadaCity.Rocks, but this is the
canonical source — direct artist names, genre tags, and OpenTable
reservation links.

Year inference: the markup omits the year. We start with the
current year; if the parsed date is in the past, we roll forward
by one year. (The page is forward-looking by design, so this is
safe outside the very narrow new-year transition.)
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper


_VENUE   = "Friar Tuck's"
_ADDRESS = "111 N Pine St, Nevada City, CA"
_SOURCE  = "https://friartucks.com/pages/calendar"

# Friar Tuck's shows times as "5:00 PM - 8:00 PM" (en-dash sometimes)
_TIME_RANGE_RE = re.compile(
    r"(\d{1,2}:\d{2}\s*[AP]M)\s*[-–]\s*(\d{1,2}:\d{2}\s*[AP]M)",
    re.I,
)


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


_MONTH_RE = re.compile(
    r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*$",
    re.I,
)


def _parse_day_header(row) -> tuple[str, int, str] | None:
    """
    Pull (month_name, day_of_month, weekday) from a day row's three-line
    header block. The header lives inside the row's first child wrapper
    as three sibling divs (month / day / weekday). Earlier broader
    searches accidentally grabbed parent divs whose text concatenated
    all three labels into one string ("May19Tue"), so we restrict to
    *leaf* divs (no nested div) and validate by content.
    """
    leaves = []
    for d in row.find_all("div"):
        if d.find("div"):                # not a leaf
            continue
        txt = d.get_text(strip=True)
        if not txt or "PM" in txt or "AM" in txt:
            continue
        leaves.append(txt)
        if len(leaves) >= 6:
            break

    # We expect month (text), day (digits), weekday (text) in some order
    # near the top. Find first month-like token + the next digit-only token
    # and the weekday after that.
    month = day = weekday = ""
    for i, t in enumerate(leaves):
        if not month and _MONTH_RE.match(t):
            month = t
        elif month and not day and t.isdigit():
            day = t
        elif month and day and not weekday and t.isalpha():
            weekday = t
            break

    if not (month and day):
        return None
    return month, int(day), weekday or ""


class FriarTucksScraper(EventScraper):
    """Friar Tuck's Restaurant — Shopify-hosted live-music calendar."""

    name          = "Friar Tuck's"
    url           = _SOURCE
    wait_css      = ".ft-cal-day-row"
    skip_rss      = True       # Shopify; no RSS for this page
    skip_selenium = True       # server-rendered HTML

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []
        today      = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        future_cap = today + timedelta(days=120)   # page only shows ~2 weeks

        for row in soup.select(".ft-cal-day-row"):
            hdr = _parse_day_header(row)
            if not hdr:
                continue
            month_name, day, _weekday = hdr

            # Each .ft-cal-show inside the row is one performance slot.
            for show in row.select(".ft-cal-show"):
                # The show's display order: img → artist-name → genre badge → time range.
                # `data-artist-genre` carries the genre tag canonically.
                genre = (show.get("data-artist-genre") or "").strip()

                # Walk *leaf* divs so we never concatenate child text. The
                # leaves in document order are: artist name, genre badge,
                # time range. (The image's wrapper div has an <img>, so
                # `find('div')` won't treat it as a leaf — img is not a div.)
                leaves = [d for d in show.find_all("div") if not d.find("div")]
                texts  = [d.get_text(strip=True) for d in leaves if d.get_text(strip=True)]
                if len(texts) < 2:
                    continue

                artist = texts[0]
                time_range = ""
                start_time = ""
                for t in texts:
                    m = _TIME_RANGE_RE.search(t)
                    if m:
                        time_range = t
                        start_time = m.group(1)
                        break

                if not artist or not start_time:
                    continue

                # Build date with year-rollover guard
                try:
                    candidate = dateparser.parse(f"{month_name} {day} {today.year}")
                    if candidate and candidate.date() < today.date():
                        candidate = dateparser.parse(f"{month_name} {day} {today.year + 1}")
                except Exception:
                    continue
                if not candidate:
                    continue
                if candidate > future_cap:
                    continue

                date_str = candidate.strftime("%Y-%m-%d")

                # Time normalisation: dateparser handles "5:00 PM" cleanly.
                try:
                    t_dt = dateparser.parse(start_time)
                    time_str = t_dt.strftime("%I:%M %p").lstrip("0") if t_dt else start_time
                except Exception:
                    time_str = start_time

                # Image
                image = ""
                img = show.find("img")
                if img and img.get("src"):
                    image = img["src"]

                # Description: artist + genre + venue context
                desc_parts = [f"Live music at {_VENUE}"]
                if genre:
                    desc_parts.append(f"({genre})")
                desc_parts.append(f"with {artist}")
                if time_range:
                    desc_parts.append(time_range)
                description = " ".join(desc_parts)

                tags = ["Music"]
                if genre:
                    tags.append(genre)

                events.append(self.make_event(
                    title       = f"{artist} at Friar Tuck's",
                    date        = date_str,
                    time        = time_str,
                    location    = _VENUE + " · " + _ADDRESS,
                    description = description[:400],
                    url         = _SOURCE,
                    category    = "Music",
                    tags        = tags,
                    image       = image,
                    area        = "Nevada City",
                ))

        return events

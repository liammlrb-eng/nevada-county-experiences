"""
Alibi Ale Works (Truckee Public House) -- Event Calendar Scraper
=================================================================
alibialeworks.com/truckee-public-house/ hosts the Truckee taproom's
event calendar built on the WordPress "Events Manager" plugin (em-*
class prefix). The plugin pages results via `?pno=N` and currently
spans ~12 pages with 15 events each — ~180 events covering the next
18 months.

Markup of one event:
    <div class="em-event em-item ...">
      <div class="em-item-image">
        <img src="https://alibialeworks.com/.../show-image-300x300.png">
      </div>
      <div class="em-item-info">
        <h3 class="em-item-title">
          <a href="https://alibialeworks.com/events/...">Music Mondays | Open Mic</a>
        </h3>
        <div class="em-event-meta">
          <div class="em-event-date">Mon., May 25, 2026</div>
          <div class="em-event-time">6:00 pm - 9:00 pm</div>
          <div class="em-event-location">
            <a>Alibi Ale Works - Truckee Public House</a>
          </div>
        </div>
      </div>
    </div>

Filtering
---------
The calendar mixes live music with bar-special "every Wednesday"
specials (Beer & A Burger For Locals, Wine Down Wednesday, Taco
Thursdays). For a music-focused calendar we skip those — they're
not visit-driving events for a Nevada-County tourism site.
"""
from __future__ import annotations
import re
import time as time_mod
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS


_VENUE   = "Alibi Ale Works — Truckee Public House"
_BASE    = "https://alibialeworks.com"
_SOURCE  = "https://alibialeworks.com/truckee-public-house/"

# Cap how many ?pno= pages to walk. 12 + a small overshoot is plenty;
# the plugin returns 0 events past the last real page so we exit early.
_MAX_PAGES = 18
_PAGE_DELAY_SEC = 0.4   # courtesy to the host

# Bar-special titles to skip — these are recurring food/drink promos, not
# music or event-night programming. Pattern is case-insensitive substring.
_SKIP_TITLE_PATTERNS = re.compile(
    r"beer (?:&|and) a burger|wine down|taco thursday|"
    r"happy hour|locals night|brunch buffet",
    re.I,
)


def _parse_date(text: str) -> str:
    """'Mon., May 25, 2026' → '2026-05-25'."""
    try:
        dt = dateparser.parse(text)
        return dt.strftime("%Y-%m-%d") if dt else ""
    except Exception:
        return ""


def _parse_time(text: str) -> str:
    """'6:00 pm - 9:00 pm' → '6:00 PM'."""
    m = re.search(r"(\d{1,2}:\d{2}\s*[ap]m)", text, re.I)
    if not m:
        return ""
    try:
        dt = dateparser.parse(m.group(1))
        return dt.strftime("%I:%M %p").lstrip("0") if dt else ""
    except Exception:
        return ""


class AlibiTruckeeScraper(EventScraper):
    """Alibi Ale Works Truckee — paginated Events Manager calendar."""

    name          = "Alibi Ale Works Truckee"
    url           = _SOURCE
    wait_css      = ".em-event"
    skip_rss      = True
    skip_selenium = True       # we handle paginated requests ourselves

    def scrape(self, driver, discover: bool = False) -> list[dict]:
        """Walk ?pno=1..N until a page returns no events (or cap hits)."""
        all_events: list[dict] = []
        seen_urls: set[str] = set()

        today      = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        future_cap = today + timedelta(days=540)

        for pno in range(1, _MAX_PAGES + 1):
            page_url = f"{_SOURCE}?pno={pno}" if pno > 1 else _SOURCE
            print(f"  [{self.name}] page {pno} → {page_url}")
            try:
                resp = requests.get(page_url, headers=_REQUESTS_HEADERS, timeout=20)
                if resp.status_code != 200:
                    print(f"  [{self.name}] HTTP {resp.status_code} — stopping pagination")
                    break
            except Exception as e:
                print(f"  [{self.name}] page fetch error: {e} — stopping")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            blocks = soup.select(".em-event")
            if not blocks:
                print(f"  [{self.name}] page {pno} empty — done")
                break

            page_events = self._parse_blocks(blocks, today, future_cap, seen_urls)
            all_events.extend(page_events)
            print(f"  [{self.name}] page {pno} → {len(page_events)} kept (total {len(all_events)})")

            time_mod.sleep(_PAGE_DELAY_SEC)

        return all_events

    def _parse_blocks(self, blocks, today, future_cap, seen_urls) -> list[dict]:
        events = []
        for ev in blocks:
            t_el = ev.select_one(".em-item-title a") or ev.select_one(".em-item-title")
            title = t_el.get_text(strip=True) if t_el else ""
            if not title or _SKIP_TITLE_PATTERNS.search(title):
                continue

            # URL — anchor in title preferred, fallback to data-href
            url = ""
            if t_el and t_el.name == "a":
                url = t_el.get("href", "")
            if not url:
                url = ev.get("data-href", "")
            # Dedup across pages: same event URL only once.
            if url and url in seen_urls:
                continue

            date_text = ""
            d_el = ev.select_one(".em-event-date")
            if d_el:
                date_text = d_el.get_text(" ", strip=True)
            date_str = _parse_date(date_text)
            if not date_str:
                continue

            try:
                event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if event_dt < today or event_dt > future_cap:
                    continue
            except Exception:
                continue

            time_str = ""
            tm_el = ev.select_one(".em-event-time")
            if tm_el:
                time_str = _parse_time(tm_el.get_text(" ", strip=True))

            # Image
            image = ""
            img = ev.select_one(".em-item-image img")
            if img:
                # Prefer the medium-sized variant from srcset if present
                src = img.get("src", "")
                if src:
                    image = src

            # Category hint from title
            tags = ["Music"]
            tl = title.lower()
            if "trivia" in tl:
                tags = ["Trivia", "Social"]
            elif "line dance" in tl or "dance" in tl:
                tags = ["Dance", "Music"]
            elif "drag" in tl:
                tags = ["Performance", "Social"]

            if url:
                seen_urls.add(url)

            description = (
                f"Live music at {_VENUE}. {title}."
                if "Music" in tags
                else f"At {_VENUE}. {title}."
            )

            events.append(self.make_event(
                title       = title,
                date        = date_str,
                time        = time_str,
                location    = _VENUE,
                description = description[:400],
                url         = url or _SOURCE,
                category    = tags[0],
                tags        = tags,
                image       = image,
                area        = "Truckee",
            ))

        return events

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """Unused — we drive pagination from scrape() directly."""
        return []

"""
Nevada County Arts Council — Arts & Culture Calendar
URL: https://www.nevadacountyarts.org/calendar/

NCAC describes their calendar as "the most comprehensive, accurate, and
up-to-date calendar of arts & culture events in Nevada County" — they
sync with community calendars (gonevadacounty.com, chambers).

The calendar page is JS-rendered, so Selenium is required. The base.py
EventScraper.scrape() handles this automatically.

Selectors are best-effort — run with `--discover --site "NCAC Calendar"`
to save HTML for refinement.
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper

_MAX_FUTURE_DAYS = 365


class NCACCalendarScraper(EventScraper):
    name      = "NCAC Calendar"
    url       = "https://www.nevadacountyarts.org/calendar/"
    wait_css  = "body"
    extra_wait = 4.0   # Calendar may load events lazily

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []
        seen_urls = set()
        cutoff = datetime.now() + timedelta(days=_MAX_FUTURE_DAYS)

        # Try multiple selector strategies
        candidates = []
        for selector in [
            "article.event",
            ".event-card",
            ".event-listing",
            ".tribe-events-calendar-list__event",
            "article[class*='event']",
            ".calendar-event",
        ]:
            found = soup.select(selector)
            if found:
                candidates = found
                break

        # Fallback: any /event/ link gets walked up
        if not candidates:
            seen_link = set()
            for link in soup.select("a[href*='/event']"):
                href = link.get("href", "")
                if not href or href in seen_link:
                    continue
                seen_link.add(href)
                container = link
                for _ in range(4):
                    if container.parent: container = container.parent
                candidates.append(container)

        for card in candidates:
            link_el = (card.select_one("a[href*='/event']")
                       or card.find("a", href=True))
            if not link_el:
                continue
            url = link_el.get("href", "").split("?")[0]
            if not url.startswith("http"):
                url = "https://www.nevadacountyarts.org" + (url if url.startswith("/") else "/" + url)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title_el = card.select_one("h1, h2, h3, h4")
            title = (title_el.get_text(strip=True) if title_el
                     else link_el.get_text(strip=True))
            if not title or len(title) < 3:
                continue

            date_str, time_str = "", ""
            time_el = card.select_one("time[datetime]")
            if time_el:
                try:
                    dt = dateparser.parse(time_el.get("datetime", ""))
                    if dt:
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass
            if not date_str:
                txt = card.get_text(" ", strip=True)
                m = re.search(
                    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})',
                    txt, re.I,
                )
                if m:
                    try:
                        year = datetime.now().year
                        dt = dateparser.parse(f"{m.group(1)} {m.group(2)} {year}", fuzzy=True)
                        if dt and dt < datetime.now() - timedelta(days=30):
                            dt = dateparser.parse(f"{m.group(1)} {m.group(2)} {year + 1}", fuzzy=True)
                        if dt:
                            date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                t = re.search(r'(\d{1,2}:\d{2}\s*[ap]m)', txt, re.I)
                if t: time_str = t.group(1).upper()

            if date_str:
                try:
                    if datetime.strptime(date_str, "%Y-%m-%d") > cutoff:
                        continue
                except Exception:
                    pass

            img_el = card.find("img")
            image = ""
            if img_el:
                image = (img_el.get("src", "") or img_el.get("data-src", ""))

            desc = ""
            desc_el = card.select_one(".description, p")
            if desc_el:
                desc = desc_el.get_text(" ", strip=True)[:400]

            # NCAC mentions venue / location in many event cards
            location = ""
            loc_el = card.select_one(".location, .venue, [class*='location']")
            if loc_el:
                location = loc_el.get_text(strip=True)

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location=location or "Nevada County",
                description=desc,
                area="Nevada County",
                category="Art event",
                url=url,
                image=image,
            ))

        return events

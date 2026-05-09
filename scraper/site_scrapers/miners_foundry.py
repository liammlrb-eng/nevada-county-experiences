"""
Miners Foundry Cultural Center (Nevada City) — events scraper.
URL: https://minersfoundry.org/events/

Miners Foundry blocks raw HTTP requests with a 403, so we MUST use Selenium.
The base.py EventScraper.scrape() method handles this automatically.

Selectors (best-effort — refine after first --discover run):
  - Try common event card selectors
  - Fall back to /event/ URL pattern detection

Run:
  python scraper/event_scraper.py --discover --site "Miners Foundry"
to inspect HTML and refine selectors.
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper

_MAX_FUTURE_DAYS = 365


class MinersFoundryScraper(EventScraper):
    name      = "Miners Foundry"
    url       = "https://minersfoundry.org/events/"
    wait_css  = "body"     # Will refine after first run
    extra_wait = 3.0       # Give JS plenty of time to populate

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []
        seen_urls = set()
        cutoff = datetime.now() + timedelta(days=_MAX_FUTURE_DAYS)

        # Try multiple card selector strategies
        candidates = []
        for selector in [
            "article.event",
            ".event-listing",
            ".event-card",
            ".tribe-events-list-event",
            "article[class*='event']",
        ]:
            found = soup.select(selector)
            if found:
                candidates = found
                break

        # Fallback: any /event/ link gets walked up to a container
        if not candidates:
            seen_link = set()
            for link in soup.select("a[href*='/event/'], a[href*='/events/']"):
                href = link.get("href", "")
                if not href or href in seen_link:
                    continue
                seen_link.add(href)
                container = link
                for _ in range(4):
                    if container.parent: container = container.parent
                candidates.append(container)

        for card in candidates:
            link_el = (card.select_one("a[href*='/event/']")
                       or card.select_one("a[href*='/events/']")
                       or card.find("a", href=True))
            if not link_el:
                continue
            url = link_el.get("href", "").split("?")[0]
            if not url.startswith("http"):
                url = "https://minersfoundry.org" + (url if url.startswith("/") else "/" + url)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title_el = card.select_one("h1, h2, h3, h4")
            title = (title_el.get_text(strip=True) if title_el
                     else link_el.get_text(strip=True))
            if not title or len(title) < 3:
                continue

            # Date/time
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
                # Search text for month names + day numbers
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
                # Time
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
                image = (img_el.get("src", "") or img_el.get("data-src", "")
                         or img_el.get("data-lazy-src", ""))

            desc = ""
            desc_el = card.select_one(".event-description, .description, p")
            if desc_el:
                desc = desc_el.get_text(" ", strip=True)[:400]

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location="Miners Foundry",
                description=desc,
                area="Nevada City",
                category="Music venue",
                url=url,
                image=image,
            ))

        return events

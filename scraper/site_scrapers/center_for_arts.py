"""
The Center for the Arts (Grass Valley) — concert calendar scraper.
URL: https://thecenterforthearts.org/events/

The Center is a major Western Nevada County music venue. Their events are
a custom HTML layout (NOT Tribe Events — their RSS feed is news-only).
Events appear to be rendered server-side, so requests works without Selenium.

Each event listing has the pattern:
    "May 12, Tue 7:00pm — Eric Johnson- Texaphonic Tour 2026  ($54-64)"

We try multiple selector fallbacks because the page structure can change.
Run with `--discover --site "Center for the Arts"` to save HTML snapshot.
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS

# Cap to events within the next 12 months (some sites list multi-year)
_MAX_FUTURE_DAYS = 365


class CenterForTheArtsScraper(EventScraper):
    name      = "Center for the Arts"
    url       = "https://thecenterforthearts.org/events/"
    wait_css  = "body"
    skip_rss  = True   # Their tribe_events RSS is news-only — skip autodiscovery

    # ── Override scrape() to prefer requests; fall back to Selenium if needed ──
    def scrape(self, driver, discover=False):
        print(f"  [{self.name}] → {self.url}")
        # 1. Try requests first (fast)
        try:
            resp = requests.get(self.url, headers=_REQUESTS_HEADERS, timeout=20)
            if resp.status_code == 200 and len(resp.text) > 5000:
                if discover:
                    self._save_snapshot(resp.text)
                soup = BeautifulSoup(resp.text, "html.parser")
                events = self.parse(soup)
                if events:
                    print(f"  [{self.name}] {len(events)} event(s) via requests")
                    return events
        except Exception as e:
            print(f"  [{self.name}] requests failed: {e}")

        # 2. Fall back to Selenium
        print(f"  [{self.name}] falling back to Selenium...")
        return super().scrape(driver, discover=discover)

    # ── Parse rendered HTML ───────────────────────────────────────────────────
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []
        seen_urls = set()
        cutoff = datetime.now() + timedelta(days=_MAX_FUTURE_DAYS)

        # The Center for the Arts uses Elementor — event cards are wrapped
        # in elementor sections, with the title in <h2.elementor-heading-title>
        # and a /ticket/ link in a nearby button.
        title_headings = soup.select("h2.elementor-heading-title")
        candidates = []
        seen_titles = set()

        # Skip-list of non-event headings on the page
        skip_titles = {
            'low ticket alert', 'sold out', 'eventsat the center',
            'events at the center', 'become a member',
        }

        # Pattern that proves a container is a real event row (has a date)
        date_in_text = re.compile(
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}',
            re.I,
        )

        for h in title_headings:
            title = h.get_text(strip=True)
            if not title or len(title) < 3 or len(title) > 110:
                continue
            if title.lower() in skip_titles:
                continue
            if 'sold out' in title.lower() and len(title) < 30:
                continue
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())

            # Walk up until we find a container that holds BOTH the title
            # AND a date pattern (the event-row level)
            container = h
            for _ in range(10):
                if container.parent:
                    container = container.parent
                if date_in_text.search(container.get_text(' ', strip=True)):
                    break
            candidates.append((title, container))

        for title, card in candidates:
            link_el = card.select_one("a[href*='/ticket/']")
            if not link_el:
                continue
            url = link_el.get("href", "").split("?")[0]
            if not url.startswith("http"):
                url = "https://thecenterforthearts.org" + url
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Date/time: look for time tag, datetime attribute, or text matching
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

            # Fallback: parse date and time SEPARATELY from card text.
            # Doing both in one regex caused day "12" to split into day=1, hour=2.
            if not date_str:
                card_text = card.get_text(" ", strip=True)
                # Date: month name + day number (word-bounded so "12" stays whole)
                date_m = re.search(
                    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})\b',
                    card_text, re.I,
                )
                if date_m:
                    try:
                        year_to_use = datetime.now().year
                        candidate = dateparser.parse(
                            f"{date_m.group(1)} {date_m.group(2)} {year_to_use}", fuzzy=True
                        )
                        if candidate and candidate < datetime.now() - timedelta(days=30):
                            candidate = dateparser.parse(
                                f"{date_m.group(1)} {date_m.group(2)} {year_to_use + 1}", fuzzy=True
                            )
                        if candidate:
                            date_str = candidate.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                # Time: H:MM AM/PM
                time_m = re.search(r'(\d{1,2}):(\d{2})\s*([ap]m)', card_text, re.I)
                if time_m:
                    time_str = f"{int(time_m.group(1))}:{time_m.group(2)} {time_m.group(3).upper()}"

            # Skip events outside our window
            if date_str:
                try:
                    if datetime.strptime(date_str, "%Y-%m-%d") > cutoff:
                        continue
                except Exception:
                    pass

            # Image
            img_el = card.find("img")
            image = ""
            if img_el:
                image = (img_el.get("src", "") or img_el.get("data-src", "")
                         or img_el.get("data-lazy-src", ""))

            # Description: text content beyond title
            desc = ""
            desc_el = card.select_one(".event-description, .description, p")
            if desc_el:
                desc = desc_el.get_text(" ", strip=True)[:400]

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location="Center for the Arts",
                description=desc,
                area="Grass Valley",
                category="Music venue",
                url=url,
                image=image,
            ))

        return events

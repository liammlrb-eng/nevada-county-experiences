"""
GoNevadaCounty — Festivals & Special Events page
URL: https://gonevadacounty.com/festivals-special-events/

This is a manually-curated static page listing the major annual / recurring
festivals in Western Nevada County: Cornish Christmas, Wild & Scenic, Mardi Gras,
Bluegrass Festival, etc. Most are already in our hardcoded EVENTS array, but
scraping ensures we pick up new additions and any date changes the chamber
publishes.

The page is static HTML — requests works, no Selenium needed.
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS

_MAX_FUTURE_DAYS = 365


class GoNevadaFestivalsScraper(EventScraper):
    name      = "Go Nevada County Festivals"
    url       = "https://gonevadacounty.com/festivals-special-events/"
    wait_css  = "body"
    skip_rss  = True   # Static HTML, no RSS

    def scrape(self, driver, discover=False):
        print(f"  [{self.name}] → {self.url}")
        try:
            resp = requests.get(self.url, headers=_REQUESTS_HEADERS, timeout=20)
            if resp.status_code == 200:
                if discover:
                    self._save_snapshot(resp.text)
                soup = BeautifulSoup(resp.text, "html.parser")
                events = self.parse(soup)
                print(f"  [{self.name}] {len(events)} event(s) found")
                return events
        except Exception as e:
            print(f"  [{self.name}] ERROR: {e}")
        return []

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []
        seen_titles = set()
        cutoff = datetime.now() + timedelta(days=_MAX_FUTURE_DAYS + 30)

        # The page is structured as featured-post-style cards.
        # Each "festival" gets a heading + description block.
        # Look for h2/h3/h4 headings that likely name a festival.
        headings = soup.select("h2, h3, h4")
        for h in headings:
            title = h.get_text(strip=True)
            # Filter to festival-like names (avoid menu / footer headings)
            if not title or len(title) < 5 or len(title) > 80:
                continue
            # Skip generic page navigation / cta headings
            if re.search(r'^(home|menu|search|filter|sign up|subscribe|newsletter|footer)\b',
                         title, re.I):
                continue
            if title.lower() in seen_titles:
                continue

            # Find a link near the heading
            link_el = h.find("a", href=True) or h.find_next("a", href=True)
            url = link_el.get("href", "") if link_el else self.url
            if url and not url.startswith("http"):
                url = "https://gonevadacounty.com" + (url if url.startswith("/") else "/" + url)

            # Find description from the next sibling paragraph
            desc = ""
            next_p = h.find_next("p")
            if next_p:
                desc = next_p.get_text(" ", strip=True)[:400]

            # Only keep entries that look like real festivals — must have date
            # context in the description (month name or year)
            if not re.search(
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b'
                r'|\bspring\b|\bsummer\b|\bautumn\b|\bfall\b|\bwinter\b|\bannual\b'
                r'|\bevery (week|day|month|year)\b'
                r'|\b\d{4}\b',
                title + ' ' + desc, re.I,
            ):
                continue

            seen_titles.add(title.lower())

            # Try to extract a specific date from description
            date_str = ""
            m = re.search(
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:[-–]\s*\d{1,2})?(?:,?\s*(\d{4}))?',
                desc, re.I,
            )
            if m:
                try:
                    year = m.group(3) or datetime.now().year
                    dt = dateparser.parse(f"{m.group(1)} {m.group(2)} {year}", fuzzy=True)
                    if dt:
                        # If past, assume next year
                        if dt < datetime.now() - timedelta(days=30):
                            dt = dateparser.parse(
                                f"{m.group(1)} {m.group(2)} {datetime.now().year + 1}",
                                fuzzy=True,
                            )
                        if dt and dt < cutoff:
                            date_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            # Image — find first img near the heading or in its parent
            image = ""
            container = h.parent
            if container:
                img_el = container.find("img")
                if img_el:
                    image = (img_el.get("src", "") or img_el.get("data-src", ""))

            # Infer area from title/desc
            area = "Nevada County"
            content = (title + ' ' + desc).lower()
            if "grass valley" in content:    area = "Grass Valley"
            elif "nevada city" in content:   area = "Nevada City"
            elif "penn valley" in content:   area = "Penn Valley"
            elif "north san juan" in content: area = "North San Juan"

            events.append(self.make_event(
                title=title,
                date=date_str,
                time="",
                location="",
                description=desc,
                area=area,
                category="Festival",
                url=url,
                image=image,
            ))

        return events

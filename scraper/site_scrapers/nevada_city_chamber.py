"""
Nevada City Chamber of Commerce — Events
URL: https://www.nevadacitychamber.com/nevada-city-events/

Simple WordPress site with Essential Grid plugin. Server-rendered; no
headless browser needed. Events sit inside `li.eg-events-wrapper` items.

Confirmed selectors (from HTML snapshot 2026-05-06):
  Card     : li.eg-events-wrapper
  Title    : .esg-entry-content .esg-content:first-child  (short non-date text)
  Date     : .esg-content div containing date-like text
  Desc     : .esg-content div with longest text
  URL      : a[class*="eg-events-element"] href (the READ MORE anchor)
  Image    : .esg-media-poster background-image OR img src
"""

from .base import EventScraper
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import requests
import re

_BASE_URL = "https://www.nevadacitychamber.com"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_DATE_RE = re.compile(
    r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|'
    r'monday|tuesday|wednesday|thursday|friday|saturday|sunday|'
    r'\d{1,2}/\d{1,2}|\d{4})',
    re.I
)


class NevadaCityChamberScraper(EventScraper):
    name      = "Nevada City Chamber"
    url       = _BASE_URL + "/nevada-city-events/"
    wait_css  = "body"
    extra_wait = 0

    # ── Override: use requests instead of Selenium ───────────────────────────
    def scrape(self, driver, discover=False):
        print(f"  [{self.name}] → {self.url}  (static fetch)")
        try:
            resp = requests.get(self.url, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"  [{self.name}] HTTP ERROR: {e}")
            return []

        if discover:
            self._save_snapshot(html)
            fname = self.name.lower().replace(" ", "_") + ".html"
            print(f"  [{self.name}] Snapshot saved → snapshots/{fname}")

        soup = BeautifulSoup(html, "html.parser")
        try:
            events = self.parse(soup)
        except Exception as e:
            print(f"  [{self.name}] ERROR in parse(): {e}")
            events = []

        print(f"  [{self.name}] {len(events)} event(s) found")
        return events

    # ── Parse Essential Grid event items ─────────────────────────────────────
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []

        # Essential Grid plugin: each event is a <li class="eg-events-wrapper ...">
        cards = soup.select("li.eg-events-wrapper")

        # Fallback to simpler selectors
        if not cards:
            cards = soup.select("[class*='eg-events-wrapper']")
        if not cards:
            # Try basic structure: entry-content > article > li
            cards = soup.select(".entry-content article li, .entry-content ul li")

        seen_urls = set()
        for card in cards:
            # ── URL ──────────────────────────────────────────────────────────
            # READ MORE anchor has class like "eg-events-element-2"
            link_el = (
                card.select_one("a[class*='eg-events-element']")
                or card.select_one("a[href]")
            )
            if not link_el:
                continue
            url = link_el.get("href", "")
            if not url:
                continue
            if not url.startswith("http"):
                url = _BASE_URL + url
            # Deduplicate — page sometimes lists calendar hub link before events
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # ── Content divs (title, date, description) ───────────────────
            content_divs = card.select(".esg-content")

            title = ""
            date_str = ""
            time_str = ""
            description = ""

            if content_divs:
                # First div = title (shortest non-date text usually)
                title = content_divs[0].get_text(strip=True)

                # Remaining divs: look for date and description
                for div in content_divs[1:]:
                    text = div.get_text(strip=True)
                    if not text:
                        continue
                    if _DATE_RE.search(text) and not date_str and len(text) < 80:
                        # Looks like a date
                        date_str, time_str = self._parse_date(text)
                        if not date_str:
                            date_str = text[:50]
                    elif len(text) > 20 and not description:
                        description = text[:300]
            else:
                # Fallback: grab text from esg-entry-content
                entry = card.select_one(".esg-entry-content")
                if entry:
                    lines = [t for t in entry.get_text(separator="\n", strip=True).split("\n") if t]
                    if lines:
                        title = lines[0]
                    for line in lines[1:]:
                        if _DATE_RE.search(line) and not date_str and len(line) < 80:
                            date_str, time_str = self._parse_date(line)
                            if not date_str:
                                date_str = line[:50]
                        elif len(line) > 20 and not description:
                            description = line[:300]

            if not title or title.upper() == "READ MORE":
                continue

            # Skip the "Local Calendar of Events" hub link
            if "calendar of events" in title.lower():
                continue

            # ── Image ─────────────────────────────────────────────────────
            image = ""
            poster = card.select_one(".esg-media-poster")
            if poster:
                style = poster.get("style", "")
                m = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
                if m:
                    image = m.group(1)
            if not image:
                img_el = card.select_one("img")
                if img_el:
                    image = img_el.get("src", img_el.get("data-src", ""))

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                description=description,
                url=url,
                image=image,
                area="Nevada City",
                category="Community Event",
            ))

        return events

    # ── Date helper ───────────────────────────────────────────────────────────
    def _parse_date(self, text: str):
        """
        Return (date_str, time_str) from a raw date string, or (raw_text, '').

        Handles date ranges like "August 6-10, 2025"  → takes the first date.
        Handles "& N" extra days like "Sep 20 & 21, 2025" → strips the second.
        Keeps raw text for non-parseable strings ("October – November", etc.).
        """
        # 1. Strip "N-M" or "N–M" ranges, keep first date:  "6-10" → "6"
        #    Negative lookahead prevents touching 4-digit years.
        clean = re.sub(r'(?<!\d)(\d{1,2})\s*[-–]\s*\d{1,2}(?!\d)', r'\1', text)

        # 2. Strip "& N" extra day numbers like "20 & 21" → "20"
        #    Only when followed by comma, end-of-string, or year.
        clean = re.sub(r'\s*&\s*(\d{1,2})(?=\s*(?:,|\Z|\s+\d{4}))', '', clean)

        # 3. Strip stray commas at the end
        clean = clean.strip().rstrip(',').strip()

        # 4a. Day-of-week only (e.g. "Every Saturday") — try fuzzy to get next occurrence
        if re.search(r'\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|'
                     r'thursday|friday|saturday|sunday)\b', clean, re.I) \
                and not re.search(r'\b\d{1,2}\b', re.sub(r'\d{4}', '', clean)):
            try:
                dt = dateparser.parse(clean, fuzzy=True)
                if dt and 2020 <= dt.year <= 2035:
                    return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip("0")
            except Exception:
                pass
            return text.strip()[:50], ""

        # 4b. If no specific day number in the cleaned string, keep raw text.
        #    e.g. "April 2026", "2025 Concert Dates" → not parseable to a day.
        if not re.search(r'\b\d{1,2}\b', re.sub(r'\d{4}', '', clean)):
            return text.strip()[:50], ""

        # 4c. Multiple comma-separated day numbers (e.g. "July 15, 22 & 29, 2026")
        #    → return raw text since we can't pick one date reliably.
        if re.search(r'\b\d{1,2}\s*,\s*\d{1,2}\b', re.sub(r'\d{4}', '', clean)):
            return text.strip()[:50], ""

        # 5. Try parsing — exact first, then fuzzy
        for attempt in [clean, text]:
            for fuzzy in [False, True]:
                try:
                    dt = dateparser.parse(attempt, fuzzy=fuzzy, dayfirst=False)
                    if dt and 2020 <= dt.year <= 2035:
                        return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass

        # 6. Return raw text so the date is at least human-readable in the UI
        return text.strip()[:50], ""

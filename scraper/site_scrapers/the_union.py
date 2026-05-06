"""
The Union (theunion.com) — Nevada County's newspaper
Events page: https://www.theunion.com/local-events/

The Union uses TownNews/BLOX CMS. The events calendar page requires a
subscriber login. However, TownNews sites often expose public RSS endpoints
for their article feeds which include local events.

We attempt the following in order:
  1. RSS feed at /local-events/?format=rss  (standard BLOX CMS endpoint)
  2. RSS feed at /search/?category=events&format=rss
  3. Selenium scrape of the public-facing events page (extracts whatever
     is accessible without login)

If all attempts yield 0 events the scraper returns an empty list rather
than erroring, so it doesn't block the rest of the pipeline.
"""

from .base import EventScraper
from bs4 import BeautifulSoup
import requests
import re
from dateutil import parser as dateparser
from datetime import datetime, timedelta
import time

# Only keep articles published in the last 90 days (RSS returns old articles)
_MAX_AGE_DAYS = 90

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

_RSS_CANDIDATES = [
    "https://www.theunion.com/local-events/?format=rss",
    "https://www.theunion.com/search/?q=events&format=rss",
    "https://www.theunion.com/entertainment/?format=rss",
    "https://www.theunion.com/news/local/?format=rss",
]


class TheUnionScraper(EventScraper):
    name      = "The Union"
    url       = "https://www.theunion.com/local-events/"
    wait_css  = ".tnt-asset-list, .event-list, article, .asset"
    extra_wait = 3.0

    # ── Override: try RSS before falling back to Selenium ────────────────────
    def scrape(self, driver, discover=False):
        # 1. Try RSS feeds (no Selenium needed, much faster)
        for rss_url in _RSS_CANDIDATES:
            events = self._try_rss(rss_url)
            if events:
                print(f"  [{self.name}] {len(events)} event(s) via RSS ({rss_url})")
                return events

        # 2. Fall back to Selenium scrape of the public page
        print(f"  [{self.name}] RSS unavailable — falling back to Selenium scrape")
        return super().scrape(driver, discover=discover)

    def _try_rss(self, rss_url: str) -> list[dict]:
        """Attempt to fetch and parse an RSS/Atom feed. Returns [] on any failure."""
        try:
            resp = requests.get(rss_url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                return []
            content_type = resp.headers.get("Content-Type", "")
            # Must look like XML/RSS — reject HTML login pages
            if "html" in content_type and "xml" not in content_type:
                return []
            text = resp.text
            if "<rss" not in text and "<feed" not in text and "<channel" not in text:
                return []
        except Exception:
            return []

        soup = BeautifulSoup(text, "xml")
        items = soup.select("item") or soup.select("entry")
        events = []
        for item in items:
            title = (item.find("title") or item.find("name"))
            if not title:
                continue
            title = title.get_text(strip=True)
            # Skip overly generic titles that are article headlines, not events
            if not title or len(title) < 8:
                continue
            if re.match(r'^(events?|upcoming events?|area events?|schedule of events?|'
                        r'successful events?|volunteer events?|music\s*&\s*events?)$',
                        title, re.I):
                continue

            link_el = item.find("link")
            url = ""
            if link_el:
                url = link_el.get_text(strip=True) or link_el.get("href", "")

            # Date — skip articles older than _MAX_AGE_DAYS
            date_str, time_str = "", ""
            pub = item.find("pubDate") or item.find("published") or item.find("updated")
            if pub:
                try:
                    dt = dateparser.parse(pub.get_text(strip=True))
                    if dt:
                        # Strip timezone for comparison
                        dt_naive = dt.replace(tzinfo=None)
                        cutoff = datetime.now() - timedelta(days=_MAX_AGE_DAYS)
                        if dt_naive < cutoff:
                            continue   # Too old — skip
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass

            # Description / summary
            desc_el = item.find("description") or item.find("summary") or item.find("content")
            description = ""
            if desc_el:
                raw = desc_el.get_text(strip=True)
                # Strip embedded HTML tags if any
                description = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:300]

            # Category
            cat_el = item.find("category")
            category = cat_el.get_text(strip=True) if cat_el else "Event"

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                description=description,
                url=url,
                category=category,
                area="Nevada County",
            ))

        return events

    # ── Selenium parse (fallback) ─────────────────────────────────────────────
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []

        cards = (
            soup.select(".tnt-asset-list .tnt-asset")
            or soup.select("article.tnt-asset")
            or soup.select(".asset-list .asset")
            or soup.select(".event-item")
            or soup.select("article")
        )

        for card in cards:
            title_el = (
                card.select_one(".tnt-headline a")
                or card.select_one("h2 a, h3 a, h4 a")
                or card.select_one(".headline a")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url   = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = "https://www.theunion.com" + url

            # Skip login/signup links
            if "/users/login" in url or "/users/signup" in url:
                continue

            time_el = card.select_one("time[datetime]")
            date_str, time_str = "", ""
            if time_el:
                dt_raw = time_el.get("datetime", "")
                try:
                    dt = dateparser.parse(dt_raw)
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    date_str = time_el.get_text(strip=True)

            loc_el = card.select_one(".tnt-location, .location, .venue, .address")
            location = loc_el.get_text(strip=True) if loc_el else ""

            desc_el = card.select_one(".tnt-summary, .summary, .description, p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            cat_el = card.select_one(".tnt-section-nav, .section, .category, .tag")
            category = cat_el.get_text(strip=True) if cat_el else "Event"

            events.append(self.make_event(
                title=title, date=date_str, time=time_str,
                location=location, description=description,
                category=category, url=url,
            ))

        return events

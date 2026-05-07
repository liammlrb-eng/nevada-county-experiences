"""
Base scraper — headless Chrome via Selenium + webdriver-manager.
All site-specific scrapers inherit from EventScraper.

RSS-FIRST DESIGN
================
Before any Selenium scraping, EventScraper.scrape() calls
try_rss_discovery() which:
  1. Fetches the page HTML with requests (fast, no browser)
  2. Looks for <link rel="alternate" type="application/rss+xml"> in HEAD
  3. Tries Tribe Events hidden feed:  /?post_type=tribe_events&feed=rss2
  4. Tries common WordPress/CMS feed URLs: /feed/, /rss.xml
  5. Tries iCal: /?post_type=tribe_events&ical=1

If a feed is found, parse_rss() is called instead of launching Chrome.
Subclasses can override parse_rss() to customise RSS field extraction,
or override scrape() entirely for full control.

ADDING A NEW SCRAPER
====================
1. Create site_scrapers/mysite.py
2. class MySiteScraper(EventScraper):
       name     = "My Site"
       url      = "https://mysite.com/events/"
       wait_css = ".event-card"          # CSS to wait for if JS renders
3. Override parse(soup) to extract events from BeautifulSoup HTML
   — or —
   Override parse_rss(feed_text) to extract events from RSS XML
4. Register in event_scraper.py: ALL_SCRAPERS.append(MySiteScraper())
5. Add entry to scraper/sources.json
"""

import os, time, re
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

SNAPSHOT_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'scraper_output', 'snapshots'
)

_REQUESTS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Pacific timezone offset (handles both PST and PDT crudely)
# For a production server, install pytz and use America/Los_Angeles
_PACIFIC = timezone(timedelta(hours=-7))   # PDT (summer); switch to -8 for PST


def make_driver() -> webdriver.Chrome:
    """Create a headless Chrome driver (auto-downloads matching ChromeDriver)."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# ── RSS autodiscovery ─────────────────────────────────────────────────────────

_RSS_PROBE_PATTERNS = [
    # Tribe Events Calendar hidden feed (most WP event sites)
    "?post_type=tribe_events&feed=rss2",
    # Standard WordPress feed
    "feed/",
    "rss.xml",
    "rss/",
    # BLOX/TownNews CMS
    "?format=rss",
]

_ICAL_PROBE_PATTERNS = [
    "?post_type=tribe_events&ical=1",
    "events.ics",
    "calendar.ics",
]


def discover_feed(page_url: str) -> tuple[str, str] | None:
    """
    Attempt to discover an RSS or iCal feed for a given page URL.
    Returns (feed_url, feed_type) where feed_type is 'rss' or 'ical',
    or None if nothing is found.

    Strategy:
    1. Fetch the page HTML (lightweight requests call)
    2. Look for <link rel="alternate" type="application/rss+xml"> in HEAD
    3. Probe common Tribe Events / CMS feed URL patterns
    """
    base = page_url.rstrip("/") + "/"
    # strip path to site root for probing
    from urllib.parse import urlparse
    parsed = urlparse(page_url)
    site_root = f"{parsed.scheme}://{parsed.netloc}/"

    # Step 1: fetch page, look for declared feed link
    try:
        resp = requests.get(page_url, headers=_REQUESTS_HEADERS, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            # BeautifulSoup fast parse just for <link> tags
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("link", rel="alternate"):
                lt = link.get("type", "")
                href = link.get("href", "")
                if "rss" in lt or "atom" in lt:
                    return href, "rss"
                if "ical" in lt or "calendar" in lt:
                    return href, "ical"
    except Exception:
        pass

    # Step 2: probe Tribe Events and common CMS feed patterns
    for pattern in _RSS_PROBE_PATTERNS:
        # Try both from page_url base and from site root
        for base_url in [base, site_root]:
            probe_url = base_url + pattern if not pattern.startswith("?") else base_url.rstrip("/") + pattern
            try:
                r = requests.head(probe_url, headers=_REQUESTS_HEADERS, timeout=8, allow_redirects=True)
                ct = r.headers.get("Content-Type", "")
                if r.status_code == 200 and ("xml" in ct or "rss" in ct or "atom" in ct):
                    return probe_url, "rss"
                # Some servers return text/html even for RSS; do a quick GET check
                if r.status_code == 200:
                    r2 = requests.get(probe_url, headers=_REQUESTS_HEADERS, timeout=8)
                    if r2.status_code == 200 and ("<rss" in r2.text[:500] or "<feed" in r2.text[:500]):
                        return probe_url, "rss"
            except Exception:
                continue

    # Step 3: probe iCal
    for pattern in _ICAL_PROBE_PATTERNS:
        for base_url in [base, site_root]:
            probe_url = base_url + pattern if not pattern.startswith("?") else base_url.rstrip("/") + pattern
            try:
                r = requests.get(probe_url, headers=_REQUESTS_HEADERS, timeout=8)
                if r.status_code == 200 and "BEGIN:VCALENDAR" in r.text[:200]:
                    return probe_url, "ical"
            except Exception:
                continue

    return None


# ── Base event scraper ────────────────────────────────────────────────────────

class EventScraper:
    """
    Base class for site-specific event scrapers.

    Subclasses must define:
        name       : str  — human-readable label (e.g. "The Union")
        url        : str  — events page URL
        wait_css   : str  — CSS selector to wait for before parsing
        parse(soup): list[dict]  — extract events from rendered HTML

    Optional overrides:
        parse_rss(text)  — extract events from RSS XML string
        extra_wait       — extra seconds after wait_css found (for lazy loaders)
        skip_rss         — set True to always use HTML scraping
        skip_selenium    — set True to always use requests (no browser)
    """

    name       = "Base"
    url        = ""
    wait_css   = "body"
    extra_wait = 2.0
    skip_rss   = False       # force HTML scraping even if feed found
    skip_selenium = False    # use requests instead of Selenium

    # ── Main entry point ──────────────────────────────────────────────────────
    def scrape(self, driver: webdriver.Chrome, discover: bool = False) -> list[dict]:

        # 1. Try RSS/iCal autodiscovery first (unless disabled)
        if not self.skip_rss:
            result = discover_feed(self.url)
            if result:
                feed_url, feed_type = result
                print(f"  [{self.name}] Feed found: {feed_type.upper()} → {feed_url}")
                try:
                    resp = requests.get(feed_url, headers=_REQUESTS_HEADERS, timeout=20)
                    if resp.status_code == 200:
                        if feed_type == "rss":
                            events = self.parse_rss(resp.text)
                        else:
                            events = self.parse_ical(resp.text)
                        if events:
                            print(f"  [{self.name}] {len(events)} event(s) from {feed_type.upper()}")
                            return events
                        print(f"  [{self.name}] Feed returned 0 events — falling back to HTML scrape")
                except Exception as e:
                    print(f"  [{self.name}] Feed fetch error: {e} — falling back to HTML scrape")

        # 2. HTML scrape (requests if skip_selenium, else Selenium)
        if self.skip_selenium:
            return self._scrape_static(discover)
        return self._scrape_selenium(driver, discover)

    # ── Selenium HTML scrape ──────────────────────────────────────────────────
    def _scrape_selenium(self, driver, discover):
        print(f"  [{self.name}] → {self.url}  (Selenium)")
        driver.get(self.url)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.wait_css))
            )
        except Exception:
            print(f"  [{self.name}] WARNING: wait_css '{self.wait_css}' not found — proceeding anyway")

        if self.extra_wait > 0:
            time.sleep(self.extra_wait)

        html = driver.page_source
        if discover:
            self._save_snapshot(html)
            print(f"  [{self.name}] Snapshot saved → snapshots/{self.name.lower().replace(' ','_')}.html")

        soup = BeautifulSoup(html, "html.parser")
        try:
            events = self.parse(soup)
        except Exception as e:
            print(f"  [{self.name}] ERROR in parse(): {e}")
            events = []

        print(f"  [{self.name}] {len(events)} event(s) found")
        return events

    # ── Static requests HTML scrape ───────────────────────────────────────────
    def _scrape_static(self, discover):
        print(f"  [{self.name}] → {self.url}  (static fetch)")
        try:
            resp = requests.get(self.url, headers=_REQUESTS_HEADERS, timeout=20)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"  [{self.name}] HTTP ERROR: {e}")
            return []

        if discover:
            self._save_snapshot(html)
            print(f"  [{self.name}] Snapshot saved → snapshots/{self.name.lower().replace(' ','_')}.html")

        soup = BeautifulSoup(html, "html.parser")
        try:
            events = self.parse(soup)
        except Exception as e:
            print(f"  [{self.name}] ERROR in parse(): {e}")
            events = []

        print(f"  [{self.name}] {len(events)} event(s) found")
        return events

    # ── Override these in subclasses ──────────────────────────────────────────
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        raise NotImplementedError(f"{self.name}.parse() not implemented")

    def parse_rss(self, feed_text: str) -> list[dict]:
        """
        Default RSS parser. Subclasses can override for site-specific fields.
        Extracts: title, link, pubDate, description, category.
        pubDate is treated as event start datetime (UTC → Pacific).
        """
        from datetime import datetime, timezone, timedelta
        soup = BeautifulSoup(feed_text, "xml")
        items = soup.select("item") or soup.select("entry")
        events = []
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # today onwards only

        for item in items:
            title_el = item.find("title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            link_el = item.find("link")
            url = ""
            if link_el:
                url = link_el.get_text(strip=True) or link_el.get("href", "")

            # Date from pubDate (UTC) → Pacific
            date_str, time_str = "", ""
            pub = item.find("pubDate") or item.find("published") or item.find("updated")
            if pub:
                try:
                    dt_utc = dateparser.parse(pub.get_text(strip=True))
                    if dt_utc:
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc
                        dt_pac = dt_utc.astimezone(_PACIFIC)
                        # Skip if before today
                        if dt_pac.replace(tzinfo=None) < cutoff:
                            continue
                        date_str = dt_pac.strftime("%Y-%m-%d")
                        time_str = dt_pac.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass

            # Description
            desc_el = item.find("description") or item.find("summary")
            description = ""
            if desc_el:
                raw = desc_el.get_text(strip=True)
                description = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:300]

            # Category
            cat_el = item.find("category")
            category = cat_el.get_text(strip=True) if cat_el else "Event"

            events.append(self.make_event(
                title=title, date=date_str, time=time_str,
                description=description, url=url, category=category,
            ))

        return events

    def parse_ical(self, ical_text: str) -> list[dict]:
        """
        Basic iCal (VCALENDAR/VEVENT) parser.
        Extracts SUMMARY, DTSTART, DTEND, LOCATION, DESCRIPTION, URL.
        """
        events = []
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # today onwards only

        # Split into VEVENT blocks
        blocks = re.split(r'BEGIN:VEVENT', ical_text)[1:]
        for block in blocks:
            end = block.find("END:VEVENT")
            if end >= 0:
                block = block[:end]

            def field(name):
                m = re.search(rf'^{name}[;:][^\r\n]*', block, re.M)
                if not m:
                    return ""
                val = m.group(0).split(":", 1)[1].strip()
                # Handle multi-line folded values
                return re.sub(r'\r?\n[ \t]', '', val)

            title = field("SUMMARY")
            if not title:
                continue

            dtstart = field("DTSTART")
            date_str, time_str = "", ""
            try:
                dt = dateparser.parse(dtstart.replace("T", " ").rstrip("Z"))
                if dt:
                    if dt.replace(tzinfo=None) < cutoff:
                        continue
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%I:%M %p").lstrip("0") if "T" in dtstart else ""
            except Exception:
                pass

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location=field("LOCATION"),
                description=field("DESCRIPTION")[:300],
                url=field("URL"),
            ))

        return events

    # ── Event factory ─────────────────────────────────────────────────────────
    def make_event(self, **kw) -> dict:
        return {
            "source":      self.name,
            "source_url":  self.url,
            "title":       kw.get("title", "").strip(),
            "date":        kw.get("date", ""),
            "time":        kw.get("time", ""),
            "end_time":    kw.get("end_time", ""),
            "location":    kw.get("location", "").strip(),
            "area":        kw.get("area", "Nevada County"),
            "description": kw.get("description", "").strip(),
            "category":    kw.get("category", "Event"),
            "tags":        kw.get("tags", []),
            "url":         kw.get("url", "").strip(),
            "image":       kw.get("image", ""),
            "scraped_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status":      "pending",
        }

    def _save_snapshot(self, html: str):
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        fname = self.name.lower().replace(" ", "_") + ".html"
        with open(os.path.join(SNAPSHOT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(html)

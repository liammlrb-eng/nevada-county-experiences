"""
Base scraper — headless Chrome via Selenium + webdriver-manager.
All site-specific scrapers inherit from EventScraper.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os, time
from datetime import datetime

SNAPSHOT_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'scraper_output', 'snapshots'
)


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


class EventScraper:
    """
    Base class for site-specific event scrapers.

    Subclasses must define:
        name       : str — human-readable label (e.g. "The Union")
        url        : str — events page URL
        wait_css   : str — CSS selector to wait for before parsing
        parse(soup): list[dict] — extract events from rendered HTML

    Optional:
        extra_wait : float — extra seconds after selector found (for lazy loaders)
    """

    name      = "Base"
    url       = ""
    wait_css  = "body"
    extra_wait = 2.0    # seconds — let JS finish rendering

    def scrape(self, driver: webdriver.Chrome, discover: bool = False) -> list[dict]:
        print(f"  [{self.name}] → {self.url}")
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

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        raise NotImplementedError(f"{self.name}.parse() not implemented")

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

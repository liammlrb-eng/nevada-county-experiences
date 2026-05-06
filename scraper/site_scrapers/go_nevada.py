"""
Go Nevada County (gonevadacounty.com) — Official tourism site
Community Calendar: https://gonevadacounty.com/community-calendar/

Uses WordPress + Smart Post Show plugin (shortcode [smart_post_show id="1204"]).
Content is JS-rendered via AJAX — requires:
  1. A long extra_wait (12 s) for the plugin to fetch + render posts
  2. A JavaScript scroll to trigger any intersection-observer lazy loaders
  3. JS poll that waits until .sps-post elements actually appear in the DOM

Re-run with --discover to refresh HTML snapshots for selector inspection.
"""

from .base import EventScraper
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from dateutil import parser as dateparser
import time
import re


class GoNevadaScraper(EventScraper):
    name      = "Go Nevada County"
    url       = "https://gonevadacounty.com/community-calendar/"
    wait_css  = "body"      # base class waits for this; we do our own extended wait below
    extra_wait = 0           # we handle all waiting ourselves in scrape()

    # ── Override scrape() for smarter JS wait ────────────────────────────────
    def scrape(self, driver, discover=False):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        print(f"  [{self.name}] → {self.url}")
        driver.get(self.url)

        # 1. Wait for the basic page body
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
        except Exception:
            pass

        # 2. Scroll down to trigger intersection-observer lazy loaders
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")

        # 3. Poll for Smart Post Show posts (up to 20 s)
        deadline = time.time() + 20
        while time.time() < deadline:
            count = driver.execute_script(
                "return document.querySelectorAll('.sps-post, .sps-item, .post-item').length"
            )
            if count > 0:
                print(f"  [{self.name}] Smart Post Show rendered {count} items after "
                      f"{20 - (deadline - time.time()):.0f} s")
                time.sleep(1)   # let images / extra data settle
                break
            time.sleep(1)
        else:
            print(f"  [{self.name}] WARNING: Smart Post Show items not found after 20 s — "
                  "proceeding with whatever rendered")

        html = driver.page_source

        # Detect Cloudflare / nginx 403 block — saves us wasted parse time
        if "403 Forbidden" in html or len(html) < 5000:
            print(f"  [{self.name}] BLOCKED (403 or empty response) — skipping")
            if discover:
                self._save_snapshot(html)
            return []

        if discover:
            self._save_snapshot(html)
            fname = self.name.lower().replace(" ", "_") + ".html"
            print(f"  [{self.name}] Snapshot saved → snapshots/{fname}")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        try:
            events = self.parse(soup)
        except Exception as e:
            print(f"  [{self.name}] ERROR in parse(): {e}")
            events = []

        print(f"  [{self.name}] {len(events)} event(s) found")
        return events

    # ── Parse rendered HTML ───────────────────────────────────────────────────
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events = []

        # Smart Post Show cards
        cards = (
            soup.select(".sps-post")
            or soup.select(".sps-item")
            or soup.select(".post-item")
            # Tribe Events Calendar fallback
            or soup.select(".type-tribe_events")
            or soup.select("article.tribe_events_cat")
            or soup.select(".tribe-event-url")
        )

        if not cards:
            # Last resort — generic articles with date metadata
            cards = [
                a for a in soup.select("article")
                if a.select_one("time[datetime], .tribe-events-schedule, .event-date, abbr[title]")
            ]

        for card in cards:
            title_el = (
                card.select_one(".sps-title a, .sps-post-title a")
                or card.select_one(".tribe-event-url")
                or card.select_one("h2 a, h3 a, h4 a")
                or card.select_one(".entry-title a")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title:
                continue

            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = "https://gonevadacounty.com" + url

            # ── Date / time ──────────────────────────────────────────────────
            date_str, time_str = "", ""

            abbr_el = card.select_one("abbr[title]")
            if abbr_el:
                try:
                    dt = dateparser.parse(abbr_el.get("title", ""))
                    date_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            time_el = card.select_one(
                ".tribe-events-schedule, .tribe-event-date-start, "
                ".sps-date, .event-date, time[datetime]"
            )
            if time_el:
                raw = time_el.get("datetime") or time_el.get_text(strip=True)
                try:
                    dt = dateparser.parse(raw)
                    if not date_str:
                        date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    if not date_str:
                        date_str = raw

            # ── Location ─────────────────────────────────────────────────────
            loc_el = card.select_one(
                ".tribe-venue, .tribe-address, .sps-meta-location, "
                ".location, .venue, address"
            )
            location = loc_el.get_text(strip=True) if loc_el else ""

            # ── Description ──────────────────────────────────────────────────
            desc_el = card.select_one(
                ".sps-excerpt, .tribe-events-schedule ~ p, "
                ".entry-summary, .excerpt, p"
            )
            description = desc_el.get_text(strip=True) if desc_el else ""

            # ── Category ─────────────────────────────────────────────────────
            cat_el = card.select_one(".tribe-events-cat, .sps-category, .category")
            category = cat_el.get_text(strip=True) if cat_el else "Event"

            # ── Image ────────────────────────────────────────────────────────
            img_el = card.select_one("img")
            image = img_el.get("src", "") if img_el else ""

            events.append(self.make_event(
                title=title, date=date_str, time=time_str,
                location=location, description=description,
                category=category, url=url, image=image,
                area="Nevada County",
            ))

        return events

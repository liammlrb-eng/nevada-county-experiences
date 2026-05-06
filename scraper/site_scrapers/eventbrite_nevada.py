"""
Eventbrite — Nevada County / Nevada City events
URL: https://www.eventbrite.com/d/ca--nevada-city/events/

Confirmed selectors (from HTML snapshot 2026-05-06):
  Card     : section.event-card-details
  URL      : a.event-card-link[href]  (strip query params after ?)
  Location : a.event-card-link[data-event-location]  (e.g. "Nevada City, CA")
  Title    : a.event-card-link h3  (or h2)
  Date/time: first <p> not inside an <aside>
  Venue    : second <p> not inside an <aside>

Location filter: only keep events in Nevada County-area cities.
Online events are kept but marked with location="Online".
Events are deduplicated by URL (Eventbrite repeats cards in sections).

Pagination: click "See more events" button up to MAX_PAGES times.
"""

from .base import EventScraper
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from datetime import datetime, timedelta
import time
import re

MAX_PAGES = 2   # extra "load more" clicks

# Cities considered part of Nevada County or immediate vicinity
# NOTE: "online" is intentionally excluded — Eventbrite's Nevada City online
# events are typically Bay Area startup/business events, not local.
_NEVADA_COUNTY_PLACES = {
    "nevada city",
    "grass valley",
    "nevada county",
    "truckee",
    "penn valley",
    "north san juan",
    "rough and ready",
    "chicago park",
    "cedar ridge",
    "washington",
    "auburn",       # Placer County but adjacent
    "colfax",       # Placer County but adjacent
}

# Day-of-week to next occurrence date helper
_DOW = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


def _next_weekday(dow_name: str) -> datetime:
    """Return the next occurrence of a day name (including today if it matches)."""
    target = _DOW.get(dow_name.lower())
    if target is None:
        return datetime.now()
    today = datetime.now()
    diff = (target - today.weekday()) % 7
    return today + timedelta(days=diff)


def _parse_eb_date(text: str) -> tuple:
    """
    Parse Eventbrite date strings like:
      "Sat, May 30 •  9:00 PM"   → ("2026-05-30", "9:00 PM")
      "Saturday •  6:30 PM"      → (next Saturday date, "6:30 PM")
      "Sat, May 16 •  10:00 AM  + 8 more"  → ("2026-05-16", "10:00 AM")
    Returns ("", "") if parsing fails.
    """
    # Remove urgency signals and extra content
    text = re.sub(r'\+\s*\d+\s*more.*$', '', text, flags=re.I).strip()
    text = text.replace("•", ",").replace("  ", " ").strip()

    # Try full parse first
    try:
        dt = dateparser.parse(text, fuzzy=True,
                              dayfirst=False, yearfirst=False)
        if dt:
            return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        pass

    # Extract time portion "H:MM AM/PM"
    time_m = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text, re.I)
    time_str = time_m.group(1).strip() if time_m else ""

    # Check if text has a month name
    if re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', text, re.I):
        try:
            # Add current year if missing
            if not re.search(r'\b20\d{2}\b', text):
                text_with_year = text + f" {datetime.now().year}"
            else:
                text_with_year = text
            dt = dateparser.parse(text_with_year, fuzzy=True)
            if dt:
                return dt.strftime("%Y-%m-%d"), time_str or dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            pass

    # Day of week only — compute next occurrence
    dow_m = re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|'
                      r'mon|tue|wed|thu|fri|sat|sun)\b', text, re.I)
    if dow_m:
        dt = _next_weekday(dow_m.group(1))
        return dt.strftime("%Y-%m-%d"), time_str

    return "", time_str


class EventbriteNevadaScraper(EventScraper):
    name      = "Eventbrite Nevada"
    url       = "https://www.eventbrite.com/d/ca--nevada-city/events/"
    wait_css  = "body"
    extra_wait = 0   # handled in scrape()

    # ── Override scrape() ────────────────────────────────────────────────────
    def scrape(self, driver, discover=False):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        print(f"  [{self.name}] → {self.url}")
        driver.get(self.url)

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
        except Exception:
            pass

        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 600);")
        time.sleep(2)

        # Poll until .event-card-details appear (up to 15 s)
        deadline = time.time() + 15
        while time.time() < deadline:
            count = driver.execute_script(
                "return document.querySelectorAll('.event-card-details').length"
            )
            if count > 0:
                break
            time.sleep(1)

        # Load more pages
        for _ in range(MAX_PAGES):
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                more_btn = driver.find_elements(
                    By.XPATH,
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    " 'abcdefghijklmnopqrstuvwxyz'), 'see more')]"
                    " | //a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    " 'abcdefghijklmnopqrstuvwxyz'), 'see more')]"
                )
                if more_btn:
                    driver.execute_script("arguments[0].scrollIntoView();", more_btn[0])
                    time.sleep(0.5)
                    more_btn[0].click()
                    time.sleep(3)
                else:
                    break
            except Exception:
                break

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

    # ── Parse rendered HTML ───────────────────────────────────────────────────
    def parse(self, soup: BeautifulSoup) -> list[dict]:
        events  = []
        seen_urls = set()

        cards = soup.select("section.event-card-details")

        for card in cards:
            # ── Link / URL ────────────────────────────────────────────────
            link_el = card.select_one("a.event-card-link")
            if not link_el:
                continue
            url = link_el.get("href", "").split("?")[0]
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            # ── Location filter ───────────────────────────────────────────
            raw_loc = link_el.get("data-event-location", "").strip()
            loc_lower = raw_loc.lower()
            if not any(place in loc_lower for place in _NEVADA_COUNTY_PLACES):
                continue   # outside Nevada County area

            # Normalize location display
            if loc_lower == "online":
                location = "Online"
            else:
                location = raw_loc

            # ── Title ─────────────────────────────────────────────────────
            title_el = link_el.select_one("h3, h2")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 3:
                continue

            # ── Date/time & venue — collect <p> NOT inside <aside> ────────
            aside = card.select_one("aside")
            aside_texts = set()
            if aside:
                aside_texts = {p.get_text(strip=True) for p in aside.select("p")}

            non_aside_ps = [
                p.get_text(strip=True)
                for p in card.select("p")
                if p.get_text(strip=True) not in aside_texts
                and p.get_text(strip=True)
            ]

            date_str, time_str = "", ""
            venue = location  # fallback

            if len(non_aside_ps) >= 1:
                date_str, time_str = _parse_eb_date(non_aside_ps[0])
            if len(non_aside_ps) >= 2:
                v = non_aside_ps[1]
                # Skip price lines "From $..." or organizer lines
                if not v.startswith("From ") and not v.startswith("Check "):
                    venue = v

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location=venue,
                url=url,
                area="Nevada County",
            ))

        return events

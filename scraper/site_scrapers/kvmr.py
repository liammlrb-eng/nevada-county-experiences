"""
KVMR Community Radio — Event Scraper
=====================================
KVMR (kvmr.org) uses The Events Calendar (Tribe Events) WordPress plugin.
Its RSS feed is reliably available at:
    https://www.kvmr.org/?post_type=tribe_events&feed=rss2

The base class discover_feed() will find this automatically, but we
override parse_rss() to extract the real event date from the item URL
or GUID rather than relying on pubDate (which is the *publication* date,
not the event date).

Event date extraction order:
    1. URL path:  /2026-05-06/event-title/
    2. GUID attr: ?eventDate=2026-05-06
    3. Tribe <startDate> or <pubDate> as fallback

Time:  extracted from <pubDate> UTC → Pacific (Tribe Events stores the
       event start time in the UTC pubDate when it knows it).

Location filter: KVMR broadcasts regionally and sometimes lists events
       in Sacramento, Reno, or Bay Area.  We keep only events whose
       location / description mentions Nevada County cities (or has no
       location at all — presumed local KVMR-hosted events).
"""

import re
from datetime import datetime, timezone, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper

# Events at these venues/cities pass through (case-insensitive substring match)
# NOTE: do NOT include "kvmr" here — every item description ends with
# "appeared first on KVMR Community Radio", which would make all events pass.
_LOCAL_PLACES = {
    "nevada city", "grass valley", "nevada county", "truckee",
    "penn valley", "north san juan", "rough and ready", "chicago park",
    "cedar ridge", "washington", "auburn", "colfax", "nevada county",
    "miners foundry", "center for the arts", "nevada theatre",
    "briarpatch", "broad street", "downtown nevada", "downtown grass",
}

# If these appear in location, title, or description and nothing local matches, skip
_DISTANT_PLACES = {
    "sacramento", "san francisco", "oakland", "berkeley", "san jose",
    "reno", "tahoe city", "south lake tahoe", "los angeles", "portland",
    "seattle", "phoenix", "stockton", "modesto", "fresno", "davis",
    # Sacramento venues that show up in KVMR calendar
    "capital stage", "r street", "harris center", "crocker art",
    "music circus", "sacramento state", "sac state",
    "folsom", "elk grove", "roseville", "rocklin", "lincoln",
}

_DATE_FROM_URL_RE = re.compile(r'/(\d{4})-(\d{2})-(\d{2})/')
_DATE_FROM_GUID_RE = re.compile(r'eventDate=(\d{4}-\d{2}-\d{2})')

_PACIFIC = timezone(timedelta(hours=-7))   # PDT; switch to -8 for PST


def _extract_event_date(item) -> str:
    """Pull event date (YYYY-MM-DD) from item URL path or GUID."""
    link = ""
    link_el = item.find("link")
    if link_el:
        link = link_el.get_text(strip=True) or link_el.get("href", "")

    m = _DATE_FROM_URL_RE.search(link)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    guid_el = item.find("guid")
    if guid_el:
        guid = guid_el.get_text(strip=True)
        m = _DATE_FROM_GUID_RE.search(guid)
        if m:
            return m.group(1)

    return ""


def _is_local(title: str, location: str, description: str) -> bool:
    """
    Return True if the event appears to be in Nevada County.

    Strategy:
    - The KVMR RSS description footer always contains "KVMR Community Radio" so
      we cannot use "kvmr" as a local-place signal — it's on every item.
    - We check title first (most reliable), then the first 300 chars of description
      (the actual event text, before the "appeared first on..." footer).
    - Any explicit distant venue/city in those texts → reject.
    - Any explicit local place → accept.
    - No geographic signal → assume local (most KVMR events are Nevada County).
    """
    # Use title + location + only the first 300 chars of description
    # (avoids matching the "appeared first on KVMR" footer)
    desc_head = description[:300] if description else ""
    combined = " ".join([title, location, desc_head]).lower()

    # Explicit distant match (checked first on combined text) → reject
    for place in _DISTANT_PLACES:
        if place in combined:
            return False

    # Explicit local match → accept
    for place in _LOCAL_PLACES:
        if place in combined:
            return True

    return True   # no geographic signal → assume local KVMR event


_KVMR_FEED = "https://www.kvmr.org/?post_type=tribe_events&feed=rss2"


class KVMRScraper(EventScraper):
    """KVMR Community Radio events via Tribe Events RSS feed."""

    name     = "KVMR"
    url      = "https://www.kvmr.org/events/"
    wait_css = "body"          # Selenium fallback (rarely used)
    skip_rss = True            # bypass generic autodiscovery — we target the
                               # Tribe Events feed directly in scrape()

    def scrape(self, driver, discover: bool = False) -> list[dict]:
        """Directly fetch the known Tribe Events RSS feed."""
        import requests
        from .base import _REQUESTS_HEADERS
        print(f"  [{self.name}] → {_KVMR_FEED}  (Tribe Events RSS)")
        try:
            resp = requests.get(_KVMR_FEED, headers=_REQUESTS_HEADERS, timeout=20)
            if resp.status_code == 200:
                events = self.parse_rss(resp.text)
                print(f"  [{self.name}] {len(events)} event(s) from RSS")
                return events
            print(f"  [{self.name}] HTTP {resp.status_code} — no events")
        except Exception as e:
            print(f"  [{self.name}] Feed error: {e}")
        return []

    def parse_rss(self, feed_text: str) -> list[dict]:
        soup = BeautifulSoup(feed_text, "xml")
        items = soup.select("item") or soup.select("entry")
        events = []
        cutoff     = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # today only and future
        future_cap = datetime.now() + timedelta(days=180)   # max 6 months ahead

        for item in items:
            title_el = item.find("title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # URL
            link_el = item.find("link")
            url = ""
            if link_el:
                url = link_el.get_text(strip=True) or link_el.get("href", "")

            # Event date from URL / GUID
            date_str = _extract_event_date(item)

            # Event time from pubDate UTC → Pacific
            time_str = ""
            pub = item.find("pubDate") or item.find("published")
            if pub:
                try:
                    dt_utc = dateparser.parse(pub.get_text(strip=True))
                    if dt_utc:
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc
                        dt_pac = dt_utc.astimezone(_PACIFIC)
                        # If we didn't get date from URL, fall back to pubDate date
                        if not date_str:
                            date_str = dt_pac.strftime("%Y-%m-%d")
                        time_str = dt_pac.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    pass

            # Skip stale or too-far-future events
            if date_str:
                try:
                    event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                    if event_dt < cutoff or event_dt > future_cap:
                        continue
                except Exception:
                    pass

            # Description
            desc_el = item.find("description") or item.find("summary") or item.find("content")
            description = ""
            if desc_el:
                raw = desc_el.get_text(strip=True)
                description = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:400]

            # Location (Tribe Events uses <tribe:venue> or plain text in desc)
            location = ""
            venue_el = item.find("tribe:venue") or item.find("venue")
            if venue_el:
                location = venue_el.get_text(strip=True)

            # Category
            cat_el = item.find("category")
            category = cat_el.get_text(strip=True) if cat_el else "Event"

            # Image — Tribe Events puts <enclosure> or <media:thumbnail>
            image = ""
            enc = item.find("enclosure")
            if enc and enc.get("url", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                image = enc.get("url", "")
            media = item.find("media:thumbnail") or item.find("media:content")
            if not image and media:
                image = media.get("url", "")

            # Local filter
            if not _is_local(title, location, description):
                continue

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location=location,
                description=description,
                url=url,
                category=category,
                image=image,
                area="Nevada County",
            ))

        return events

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """HTML fallback — not normally reached because RSS is available."""
        return []

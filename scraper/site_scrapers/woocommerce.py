"""
WooCommerce Store API scraper.

Many maker / class venues run WordPress + WooCommerce and sell each
class as a *product*. WooCommerce ships a public, read-only Store API
at /wp-json/wc/store/v1/products that returns the full catalog as JSON
— no auth, no HTML scraping, no site changes required.

WHY THIS BEATS RSS / HTML
=========================
The Store API product object includes the `variations` array INLINE,
and each variation carries its session date as an attribute, e.g.:

    "variations": [
      { "id": 72867,
        "attributes": [{ "name": "Date/Time",
                         "value": "Sun 5/17 from 2:00 PM to 6:00 PM" }] } ]

So one paginated request (per_page=100) yields every class WITH every
session date. A WooCommerce product RSS feed, by contrast, gives only
title + link + blurb — no price, no date, no instructor.

ONE CLASS SESSION = ONE EVENT
=============================
A class with three scheduled dates becomes three events in the queue,
each pointing at the same class permalink. The admin approves/dismisses
per session, exactly like any other event.

ADDING ANOTHER WOOCOMMERCE VENUE
================================
Subclass WooCommerceScraper, set name / url / store_root / area.
That's the whole job — the Store API shape is identical everywhere.
"""
from __future__ import annotations
import re, html, requests
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS

_PER_PAGE  = 100
_MAX_PAGES = 10            # safety cap — 1,000 products is far beyond any venue
_MAX_FUTURE_DAYS = 480     # ignore sessions more than ~16 months out


def _strip_html(s: str) -> str:
    if not s:
        return ""
    return html.unescape(BeautifulSoup(s, "html.parser").get_text(" ", strip=True))


def _parse_session_datetime(value: str) -> tuple:
    """Parse a WooCommerce variation 'Date/Time' attribute string.

    Handles e.g. 'Sun 5/17 from 2:00 PM to 6:00 PM' and
    'Sat 6/14 at 10:00 AM'. Returns (date 'YYYY-MM-DD', start_time,
    end_time) — date is None when no M/D could be found.

    Year is inferred: a bare M/D more than 30 days in the past is
    assumed to mean next year (classes are always scheduled forward)."""
    if not value:
        return (None, "", "")
    m = re.search(r"(\d{1,2})/(\d{1,2})", value)
    if not m:
        return (None, "", "")
    month, day = int(m.group(1)), int(m.group(2))
    today = date.today()
    try:
        d = date(today.year, month, day)
    except ValueError:
        return (None, "", "")
    if d < today - timedelta(days=30):
        try:
            d = date(today.year + 1, month, day)
        except ValueError:
            pass

    start_t, end_t = "", ""
    rng = re.search(r"from\s+(.+?)\s+to\s+(.+?)\s*$", value, re.I)
    if rng:
        start_t, end_t = rng.group(1).strip(), rng.group(2).strip()
    else:
        single = re.search(r"\bat\s+(.+?)\s*$", value, re.I)
        if single:
            start_t = single.group(1).strip()
    return (d.strftime("%Y-%m-%d"), start_t, end_t)


class WooCommerceScraper(EventScraper):
    """Generic WooCommerce Store API scraper. Subclass and set the
    four class attributes below."""
    name          = "WooCommerce"
    url           = ""             # human-facing classes page (for source_url)
    store_root    = ""             # site root, e.g. "https://thecuriousforge.org"
    area          = "Nevada County"
    skip_rss      = True           # we hit the Store API directly
    skip_selenium = True           # never need a browser

    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        api = f"{self.store_root.rstrip('/')}/wp-json/wc/store/v1/products"
        print(f"  [{self.name}] -> {api}  (WooCommerce Store API)")

        products = []
        for page in range(1, _MAX_PAGES + 1):
            try:
                resp = requests.get(
                    api, headers=_REQUESTS_HEADERS, timeout=25,
                    params={"per_page": _PER_PAGE, "page": page},
                )
                resp.raise_for_status()
                batch = resp.json()
            except Exception as e:
                print(f"  [{self.name}] page {page} fetch failed: {e}")
                break
            if not isinstance(batch, list) or not batch:
                break
            products.extend(batch)
            print(f"  [{self.name}] page {page}: {len(batch)} product(s)")
            if len(batch) < _PER_PAGE:
                break

        if not products:
            print(f"  [{self.name}] 0 products returned")
            return []

        if discover:
            import os, json
            from .base import SNAPSHOT_DIR
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            fn = self.name.lower().replace(" ", "_") + "_products.json"
            with open(os.path.join(SNAPSHOT_DIR, fn), "w", encoding="utf-8") as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            print(f"  [{self.name}] Snapshot saved -> snapshots/{fn}")

        events = []
        seen = set()
        today  = date.today()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)

        for p in products:
            title = html.unescape((p.get("name") or "").strip())
            if not title:
                continue
            permalink = p.get("permalink") or self.url
            desc = _strip_html(p.get("short_description") or p.get("description") or "")
            if len(desc) > 400:
                desc = desc[:397] + "..."

            # Price — Store API gives minor units (cents) as a string
            price_note = ""
            pr = p.get("prices") or {}
            try:
                minor = int(pr.get("price") or 0)
                unit  = int(pr.get("currency_minor_unit") or 2)
                if minor > 0:
                    price_note = f"${minor / (10 ** unit):.0f}"
            except Exception:
                pass

            # Categories -> tags (the WooCommerce studio/discipline list)
            cats = [html.unescape((c.get("name") or "").strip())
                    for c in (p.get("categories") or []) if c.get("name")]
            tags = ["Hands-on", "Workshop"] + [c for c in cats if c.lower() not in
                    ("uncategorized", "gift certificate", "members only")]

            image = ""
            imgs = p.get("images") or []
            if imgs and isinstance(imgs[0], dict):
                image = imgs[0].get("src", "") or ""

            # Each variation = one class session
            variations = p.get("variations") or []
            for var in variations:
                dt_value = ""
                for attr in (var.get("attributes") or []):
                    if (attr.get("name") or "").strip().lower() in (
                            "date/time", "date / time", "date", "session"):
                        dt_value = attr.get("value") or ""
                        break
                if not dt_value:
                    continue
                date_str, start_t, end_t = _parse_session_datetime(dt_value)
                if not date_str:
                    continue
                try:
                    d = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if d < today or d > cutoff:
                    continue

                key = f"{title.lower()}|{date_str}|{start_t}"
                if key in seen:
                    continue
                seen.add(key)

                note = desc
                if price_note:
                    note = f"{price_note} · {note}" if note else price_note

                events.append(self.make_event(
                    title=title,
                    date=date_str,
                    time=start_t,
                    end_time=end_t,
                    location=self.name,
                    area=self.area,
                    description=note,
                    category="Workshop",
                    tags=tags,
                    url=permalink,
                    image=image,
                ))

        print(f"  [{self.name}] {len(events)} class session(s) from "
              f"{len(products)} product(s)")
        return events

    # parse() is never called (scrape is overridden) — stub for the ABC
    def parse(self, soup) -> list[dict]:
        return []


class CuriousForgeScraper(WooCommerceScraper):
    """The Curious Forge — 20,000 sq ft makerspace in Nevada City.
    Classes are WooCommerce products; each variation is a session date."""
    name       = "The Curious Forge"
    url        = "https://thecuriousforge.org/classes-events/classes/"
    store_root = "https://thecuriousforge.org"
    area       = "Nevada City"

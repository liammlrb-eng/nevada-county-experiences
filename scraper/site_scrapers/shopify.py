"""
Shopify scraper via the public /products.json endpoint.

Shopify stores expose their entire product catalog as JSON at
/products.json — public, no auth, paginated (?limit=250&page=N). For
venues that sell classes/workshops as Shopify products this is the
clean equivalent of the WooCommerce Store API.

PER-VENUE DATE HANDLING
=======================
Unlike WooCommerce (where one product carries dated variations),
Shopify class venues vary in how they encode the session date:
  - in the product title          ("Copper Spoons | Wed, May 20, 5-8pm")
  - in the body_html as labels    ("Date: ...  Time: ...  Cost: ...")
  - in variant option values
  - in a third-party booking app

So ShopifyScraper handles the generic mechanics (fetch, paginate,
filter, build events) and delegates date extraction to
extract_datetime(), which subclasses override for their venue.

Wolf Craft Collective makes ONE product per class date — each class
is a single dated product, so one product = one event.

ADDING ANOTHER SHOPIFY VENUE
============================
Subclass ShopifyScraper, set name / url / store_root / area, set
product_types if the store mixes classes with merch, and override
extract_datetime() if the venue encodes dates differently.
"""
from __future__ import annotations
import re, html, requests
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS

_PER_PAGE  = 250           # Shopify's max page size
_MAX_PAGES = 8
_MAX_FUTURE_DAYS = 480


def _strip_html(s: str) -> str:
    if not s:
        return ""
    return html.unescape(BeautifulSoup(s, "html.parser").get_text(" ", strip=True))


def _clean_time(s: str) -> str:
    """Reduce a messy time fragment to just the 'H:MM am/pm' token —
    drops trailing parentheticals like '(with a break for lunch ~1pm)'."""
    if not s:
        return ""
    m = re.match(r"\s*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", s, re.I)
    return m.group(1).strip() if m else s.strip()


class ShopifyScraper(EventScraper):
    """Generic Shopify /products.json scraper. Subclass and configure."""
    name          = "Shopify"
    url           = ""              # human-facing classes page
    store_root    = ""              # site root, e.g. "https://wolfcraftcollective.com"
    area          = "Nevada County"
    product_types = None            # None = all; else a set, e.g. {"Class"}
    skip_rss      = True
    skip_selenium = True

    # ── Date extraction — override per venue ────────────────────────────────
    def extract_datetime(self, product: dict) -> tuple:
        """Return (date 'YYYY-MM-DD' | None, start_time, end_time).

        Default strategy: parse a labeled block out of body_html —
            Date: <human date>   Time: <start> - <end>
        Works for class-selling Shopify stores that format descriptions
        this way (Wolf Craft does). Subclasses override for other shapes."""
        body = _strip_html(product.get("body_html") or "")
        date_str, start_t, end_t = None, "", ""

        m = re.search(r"Date:\s*(.+?)(?=\s+(?:Time|Cost|Location|Workshop|Instructor)\s*:|$)",
                      body, re.I)
        if m:
            raw = m.group(1).strip()
            # Multi-day ("... and Sunday, ...") — take the first date
            raw = re.split(r"\s+and\s+", raw, maxsplit=1)[0].strip()
            try:
                d = dateparser.parse(raw, fuzzy=True).date()
                date_str = d.strftime("%Y-%m-%d")
            except Exception:
                date_str = None

        tm = re.search(r"Time:\s*(.+?)(?=\s+(?:Cost|Location|Workshop|Instructor|Date)\s*:|$)",
                       body, re.I)
        if tm:
            tval = tm.group(1).strip()
            parts = re.split(r"\s*[-–—]\s*", tval, maxsplit=1)
            start_t = _clean_time(parts[0])
            if len(parts) > 1:
                end_t = _clean_time(parts[1])

        # Fallback: pull a date out of the product title if body had none
        if not date_str:
            title = product.get("title") or ""
            if "|" in title:
                tail = title.split("|", 1)[1]
                try:
                    d = dateparser.parse(tail, fuzzy=True).date()
                    date_str = d.strftime("%Y-%m-%d")
                except Exception:
                    pass

        return (date_str, start_t, end_t)

    def product_filter(self, product: dict) -> bool:
        if self.product_types is None:
            return True
        return product.get("product_type") in self.product_types

    # ── Main ────────────────────────────────────────────────────────────────
    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        api = f"{self.store_root.rstrip('/')}/products.json"
        print(f"  [{self.name}] -> {api}  (Shopify products.json)")

        products = []
        for page in range(1, _MAX_PAGES + 1):
            try:
                resp = requests.get(api, headers=_REQUESTS_HEADERS, timeout=25,
                                    params={"limit": _PER_PAGE, "page": page})
                resp.raise_for_status()
                batch = (resp.json() or {}).get("products", [])
            except Exception as e:
                print(f"  [{self.name}] page {page} fetch failed: {e}")
                break
            if not batch:
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
        seen   = set()
        today  = date.today()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)

        for p in products:
            if not self.product_filter(p):
                continue
            # Cleaned title — strip a "| date" suffix venues append
            title = html.unescape((p.get("title") or "").split("|", 1)[0].strip())
            if not title:
                continue

            date_str, start_t, end_t = self.extract_datetime(p)
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

            handle = p.get("handle") or ""
            permalink = (f"{self.store_root.rstrip('/')}/products/{handle}"
                         if handle else self.url)

            desc = _strip_html(p.get("body_html") or "")
            # Trim the leading "Date:/Time:/Cost:/Location:" labels off the
            # description — they're already captured as structured fields.
            desc = re.sub(r"^.*?Workshop [Dd]escription:\s*", "", desc)
            if len(desc) > 400:
                desc = desc[:397] + "..."

            image = ""
            imgs = p.get("images") or []
            if imgs and isinstance(imgs[0], dict):
                image = imgs[0].get("src", "") or ""

            ptype = p.get("product_type") or ""
            tags  = ["Hands-on", "Workshop"]
            if ptype and ptype.lower() not in ("class", "workshop"):
                tags.append(ptype)

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=start_t,
                end_time=end_t,
                location=self.name,
                area=self.area,
                description=desc,
                category="Workshop",
                tags=tags,
                url=permalink,
                image=image,
            ))

        print(f"  [{self.name}] {len(events)} class session(s) from "
              f"{len(products)} product(s)")
        return events

    def parse(self, soup) -> list[dict]:
        return []


class WolfCraftScraper(ShopifyScraper):
    """Wolf Craft School & Collective — hands-on craft workshops
    (metalwork, stained glass, shoemaking, fiber arts) in Nevada City.
    Each class is one dated Shopify product of product_type 'Class'."""
    name          = "Wolf Craft Collective"
    url           = "https://wolfcraftcollective.com/collections/classes"
    store_root    = "https://wolfcraftcollective.com"
    area          = "Nevada City"
    product_types = {"Class"}

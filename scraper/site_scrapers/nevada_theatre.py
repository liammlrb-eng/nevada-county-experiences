"""
Nevada Theatre — historic 1865 theatre, 401 Broad St, Nevada City.

The site runs WordPress with the MEC (Modern Events Calendar) plugin.
MEC registers its events as the 'mec-events' post type, which IS
exposed on the generic WP REST API:

    /wp-json/wp/v2/mec-events

BUT the REST response carries only standard post fields (title,
content, link) — MEC keeps the actual event date/time in post meta
that isn't show_in_rest. So this scraper does list-then-fetch:

  1. List events from /wp-json/wp/v2/mec-events  (one call)
  2. Fetch each event's page and parse the displayed date + time

~a dozen events, so ~a dozen page fetches per run — acceptable for a
nightly scrape. The date parse is regex on MEC's rendered markup, so
it is the brittle kind: if MEC changes its date layout the regex
needs updating. Nevada Theatre is a marquee venue, so the resilience
(not depending solely on KVMR) is worth the maintenance.
"""
from __future__ import annotations
import re, html, requests
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup

from .base import EventScraper, _REQUESTS_HEADERS

_API = "https://nevadatheatre.com/wp-json/wp/v2/mec-events"
_MAX_FUTURE_DAYS = 480

_MONTHS = ("January|February|March|April|May|June|July|August|"
           "September|October|November|December")
_DATE_RE = re.compile(rf"({_MONTHS})\s+(\d{{1,2}}),?\s+(20\d\d)", re.I)
_TIME_RE = re.compile(r"(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", re.I)


def _strip_html(s: str) -> str:
    if not s:
        return ""
    return html.unescape(BeautifulSoup(s, "html.parser").get_text(" ", strip=True))


class NevadaTheatreScraper(EventScraper):
    name          = "Nevada Theatre"
    url           = "https://nevadatheatre.com/events/"
    area          = "Nevada City"
    skip_rss      = True
    skip_selenium = True

    def scrape(self, driver=None, discover: bool = False) -> list[dict]:
        print(f"  [{self.name}] -> {_API}  (MEC events via WP REST)")
        try:
            resp = requests.get(_API, headers=_REQUESTS_HEADERS, timeout=25,
                                params={"per_page": 50})
            resp.raise_for_status()
            records = resp.json()
        except Exception as e:
            print(f"  [{self.name}] event-list fetch failed: {e}")
            return []
        if not isinstance(records, list) or not records:
            print(f"  [{self.name}] 0 events in REST list")
            return []
        print(f"  [{self.name}] {len(records)} event(s) listed — fetching dates")

        events = []
        seen   = set()
        today  = date.today()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)

        for rec in records:
            title = html.unescape((rec.get("title") or {}).get("rendered", "").strip())
            link  = rec.get("link") or self.url
            if not title:
                continue

            # Fetch the event page and parse the displayed date/time
            try:
                page = requests.get(link, headers=_REQUESTS_HEADERS, timeout=20).text
            except Exception:
                continue
            text = BeautifulSoup(page, "html.parser").get_text(" ", strip=True)

            dm = _DATE_RE.search(text)
            if not dm:
                continue
            try:
                d = datetime.strptime(f"{dm.group(1)} {dm.group(2)} {dm.group(3)}",
                                      "%B %d %Y").date()
            except ValueError:
                continue
            if d < today or d > cutoff:
                continue
            date_str = d.strftime("%Y-%m-%d")

            # Time — first time token after the date in the page text
            time_str = ""
            tail = text[dm.end():dm.end() + 120]
            tm = _TIME_RE.search(tail)
            if tm:
                t = tm.group(1).upper().replace(".", "").replace(" ", "")
                time_str = re.sub(r"(\d)(AM|PM)", r"\1 \2", t)

            desc = _strip_html((rec.get("excerpt") or {}).get("rendered", "")
                               or (rec.get("content") or {}).get("rendered", ""))
            if len(desc) > 400:
                desc = desc[:397] + "..."

            key = f"{title.lower()}|{date_str}"
            if key in seen:
                continue
            seen.add(key)

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location="Nevada Theatre",
                area=self.area,
                description=desc,
                category="Theatre",
                tags=["Theater", "Film", "Music"],
                url=link,
            ))

        print(f"  [{self.name}] {len(events)} event(s) with parseable dates")
        return events

    def parse(self, soup) -> list[dict]:
        return []

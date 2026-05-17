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
_API_PER_PAGE    = 50    # nevadatheatre.com 500s on per_page=100
_MAX_API_PAGES   = 12    # paginate the full mec-events post list

_MONTHS = ("January|February|March|April|May|June|July|August|"
           "September|October|November|December")
# MEC's .mec-start-date-label renders e.g. "May 13 2026"
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

        # ── List ALL mec-events posts (the REST list is post-date ordered,
        #    not event-date ordered, so upcoming events are scattered
        #    through the full set — paginate everything). ──────────────────
        records = []
        for page in range(1, _MAX_API_PAGES + 1):
            try:
                resp = requests.get(_API, headers=_REQUESTS_HEADERS, timeout=25,
                                    params={"per_page": _API_PER_PAGE, "page": page})
                if resp.status_code == 400:
                    break          # past the last page
                resp.raise_for_status()
                batch = resp.json()
            except Exception as e:
                print(f"  [{self.name}] list page {page} failed: {e}")
                break
            if not isinstance(batch, list) or not batch:
                break
            records.extend(batch)
            if len(batch) < _API_PER_PAGE:
                break
        if not records:
            print(f"  [{self.name}] 0 events in REST list")
            return []
        print(f"  [{self.name}] {len(records)} event post(s) listed — "
              f"fetching dates")

        events = []
        seen   = set()
        today  = date.today()
        cutoff = today + timedelta(days=_MAX_FUTURE_DAYS)
        fetched = 0

        for rec in records:
            title = html.unescape((rec.get("title") or {}).get("rendered", "").strip())
            link  = rec.get("link") or self.url
            if not title:
                continue

            # Fetch the event page; read MEC's clean date/time elements
            try:
                page = requests.get(link, headers=_REQUESTS_HEADERS, timeout=20).text
                fetched += 1
            except Exception:
                continue
            soup = BeautifulSoup(page, "html.parser")

            # MEC renders the start date in .mec-start-date-label ("May 13 2026")
            dlabel = soup.select_one(".mec-start-date-label, .mec-events-abbr")
            dtext  = dlabel.get_text(" ", strip=True) if dlabel else ""
            dm = _DATE_RE.search(dtext) or _DATE_RE.search(
                 soup.get_text(" ", strip=True))
            if not dm:
                continue
            try:
                d = datetime.strptime(f"{dm.group(1)} {dm.group(2)} {dm.group(3)}",
                                      "%B %d %Y").date()
            except ValueError:
                continue
            if d < today or d > cutoff:
                continue          # past or too-far event — skip
            date_str = d.strftime("%Y-%m-%d")

            # Time — MEC's .mec-single-event-time ("Time 7:00 pm")
            time_str = ""
            tlabel = soup.select_one(".mec-single-event-time")
            tm = _TIME_RE.search(tlabel.get_text(" ", strip=True) if tlabel else "")
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

        print(f"  [{self.name}] {len(events)} upcoming event(s) "
              f"({fetched} pages fetched)")
        return events

    def parse(self, soup) -> list[dict]:
        return []

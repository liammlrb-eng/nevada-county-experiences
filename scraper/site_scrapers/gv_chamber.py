"""
Greater Grass Valley Chamber of Commerce — Event Scraper
=========================================================
URL: https://www.grassvalleychamber.com/about/chamber-events/

The GV Chamber publishes their events calendar as a manually-coded
Elementor WordPress page (NOT a structured events plugin like Tribe Events).

Page structure pattern:
  <h3>Event Title</h3>          ← event name (h3 or h4)
  <h5>Day, Month NNth, YYYY, at H:MMPM</h5>  ← event date/time
  <a href="…detail-page…">…</a>  ← event detail link (optional)

Events are grouped in Elementor widget containers. We parse by walking
all heading elements in DOM order and pairing each h5 date line with the
nearest preceding h3/h4 title.

NOTE: Because this is a hand-authored page, the structure may shift when
the Chamber team edits it.  If the scraper returns 0 events, run with
--discover to save a snapshot and re-inspect the selectors.
"""

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import EventScraper, _REQUESTS_HEADERS

# Patterns that identify section-header h3s rather than event titles
_SECTION_HEADERS = re.compile(
    r'^(January|February|March|April|May|June|July|August|September|October|November|December'
    r'|Spring|Summer|Fall|Winter|Upcoming|Calendar|Events?|Meetings?|Networking|Monthly|Quarterly)',
    re.I,
)

# Pattern to detect a date in an h5 (day-of-week or month name)
_DATE_IN_H5 = re.compile(
    r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday'
    r'|January|February|March|April|May|June|July|August|September|October|November|December)',
    re.I,
)

# Pattern to clean "Monday, May 18th, 2026, at 3:30PM" → parseable
_DATE_CLEAN = re.compile(r'\b(\d+)(st|nd|rd|th)\b', re.I)


def _parse_event_date(text: str) -> tuple[str, str]:
    """
    Parse "Monday, May 18th, 2026, at 3:30PM" into (YYYY-MM-DD, H:MM AM/PM).
    Returns ('', '') on failure.
    """
    clean = _DATE_CLEAN.sub(r'\1', text)       # strip ordinal suffixes
    clean = re.sub(r'\bat\b', '', clean, flags=re.I).strip()
    try:
        dt = dateparser.parse(clean, dayfirst=False)
        if dt:
            return dt.strftime('%Y-%m-%d'), dt.strftime('%I:%M %p').lstrip('0')
    except Exception:
        pass
    return '', ''


class GVChamberScraper(EventScraper):
    """Greater Grass Valley Chamber of Commerce events (static Elementor page)."""

    name        = "GV Chamber"
    url         = "https://www.grassvalleychamber.com/about/chamber-events/"
    wait_css    = "body"
    skip_rss    = True        # no usable events RSS feed
    skip_selenium = True      # static HTML — requests is fine

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """
        Each event lives inside an Elementor top-level section (6 levels above h5).
        Section layout:
          <section class="elementor-top-section …">
            …
            <h5>Day, Month Nth, YYYY, at H:MMAM/PM</h5>   ← date/time
            <h3> or <h4>Event Title</h3>                   ← title (if present)
            <p><strong>Event Title</strong> location…</p>  ← title in <strong> if no h3/h4
            <a href="…detail…">…</a>                       ← detail link (optional)
        """
        events = []
        cutoff = datetime.now() - timedelta(days=7)

        for h5 in soup.find_all('h5'):
            date_text = h5.get_text(strip=True)
            if not _DATE_IN_H5.search(date_text):
                continue

            date_str, time_str = _parse_event_date(date_text)

            # Skip stale events
            if date_str:
                try:
                    if datetime.strptime(date_str, '%Y-%m-%d') < cutoff:
                        continue
                except Exception:
                    pass

            # Walk UP exactly 6 levels to reach elementor-top-section
            section = h5
            for _ in range(6):
                if section.parent:
                    section = section.parent

            # 1. Try h3 / h4 in the section
            title = ''
            link_url = ''
            for tag in ('h3', 'h4'):
                for hx in section.find_all(tag):
                    txt = hx.get_text(strip=True)
                    if txt and not _SECTION_HEADERS.match(txt):
                        title = txt
                        a = hx.find('a', href=True)
                        if a and a['href'].startswith('http'):
                            link_url = a['href']
                        break
                if title:
                    break

            # 2. Fall back: first <strong> in first <p> in the section
            if not title:
                for p in section.find_all('p'):
                    strong = p.find('strong')
                    if strong:
                        txt = strong.get_text(strip=True)
                        if txt and not _DATE_IN_H5.search(txt):
                            title = txt
                            break

            if not title:
                continue

            # Extract location: look for street address in paragraph text
            location = 'Grass Valley, CA'
            addr_re = re.compile(r'\d+\s+\w+\s+(Street|St|Ave|Road|Rd|Way|Dr|Blvd)', re.I)
            for p in section.find_all('p'):
                for span in p.find_all(['span', 'strong', 'em']) + [p]:
                    txt = span.get_text(strip=True)
                    if addr_re.search(txt) and len(txt) < 120:
                        location = txt.split('|')[0].strip()
                        break
                if location != 'Grass Valley, CA':
                    break

            # Detail page link
            if not link_url:
                for a in section.find_all('a', href=True):
                    href = a['href']
                    if (href.startswith('https://www.grassvalleychamber.com/')
                            and '/about/' not in href
                            and '/category/' not in href):
                        link_url = href
                        break

            # Description: full section text minus the date line
            description = section.get_text(separator=' ', strip=True)
            description = re.sub(re.escape(date_text), '', description).strip()[:300]

            # Image — first <img> in the section, or background-image in a style attr
            image = ''
            img_el = section.find('img')
            if img_el:
                image = img_el.get('src') or img_el.get('data-src') or img_el.get('data-lazy-src', '')
                if image and image.startswith('/'):
                    image = 'https://www.grassvalleychamber.com' + image
            if not image:
                for tag in section.find_all(style=True):
                    m = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', tag.get('style', ''))
                    if m and any(m.group(1).lower().endswith(ext) for ext in ('.jpg','.jpeg','.png','.webp')):
                        image = m.group(1)
                        break

            events.append(self.make_event(
                title=title,
                date=date_str,
                time=time_str,
                location=location,
                area='Grass Valley',
                description=description,
                url=link_url or self.url,
                category='Chamber Event',
                image=image,
            ))

        # Deduplicate by title+date+time (workshops at multiple times kept separate)
        seen: set[str] = set()
        unique = []
        for ev in events:
            key = f"{ev['title'].lower()}|{ev['date']}|{ev['time']}"
            if key not in seen:
                seen.add(key)
                unique.append(ev)

        return unique

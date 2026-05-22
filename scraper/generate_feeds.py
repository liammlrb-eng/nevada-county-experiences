#!/usr/bin/env python3
"""
Nevada County Experience -- Outbound Feed Generator
====================================================
Reads scraper_output/events.json + the EXPERIENCES list in index.html and
writes four static feed files into ./feeds/ that any partner can
subscribe to:

    feeds/events.ics    -- iCal feed (Google Cal / Apple Cal / Outlook)
    feeds/events.rss    -- RSS 2.0 (KVMR newsletter, partner sites)
    feeds/events.json   -- Clean public JSON (developer use)
    feeds/venues.json   -- The 164 curated experiences (stable list)

These are committed to the repo so GitHub Pages serves them at:
    https://liammlrb-eng.github.io/nevada-county-experiences/feeds/<file>

Run:
    python scraper/generate_feeds.py
Hooked into event_scraper.py so feeds refresh automatically after each scrape.

Filtering rules match what the public site shows:
  - Only events with status == "approved"
  - Only events whose end date (or start date if no end) is today or later

Design notes:
  - No external feed libraries -- straight-line text generation keeps the
    file dependency-free and the output diff-friendly under version control.
  - AI-enriched fields (ai_area, ai_venue, ai_summary, ai_tags) supersede
    raw scraper fields when present.
"""
from __future__ import annotations
import os, re, sys, json
from datetime import datetime, date, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
ROOT_DIR    = SCRIPT_DIR.parent
EVENTS_FILE = ROOT_DIR / "scraper_output" / "events.json"
INDEX_HTML  = ROOT_DIR / "index.html"
FEEDS_DIR   = ROOT_DIR / "feeds"

# Public URLs -- partners' subscribe target.
SITE_URL = "https://liammlrb-eng.github.io/nevada-county-experiences/"
FEED_BASE = SITE_URL + "feeds/"

# ── UTF-8 stdout for Windows console -─────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


# ── Event loading + normalisation ─────────────────────────────────────────────

def _today() -> date:
    return date.today()


def _public_event(ev: dict) -> dict | None:
    """Project a raw scraper event into the public feed schema.
    Returns None if the event should not be published (wrong status, past, no date)."""
    if ev.get("status") != "approved":
        return None
    d = ev.get("date") or ""
    if len(d) < 10:
        return None
    try:
        start = date.fromisoformat(d[:10])
    except ValueError:
        return None
    end_raw = ev.get("end_date") or d
    try:
        end = date.fromisoformat(end_raw[:10])
    except ValueError:
        end = start
    if end < _today():
        return None

    # AI fields override scraper fields when available.
    area     = (ev.get("ai_area") or ev.get("area") or "").strip()
    venue    = (ev.get("ai_venue") or ev.get("location") or "").strip()
    summary  = (ev.get("ai_summary") or ev.get("description") or "").strip()
    tags_raw = ev.get("ai_tags") or ev.get("tags") or []
    tags     = [t for t in (tags_raw if isinstance(tags_raw, list) else []) if t]

    return {
        "id":          ev.get("scraper_id") or "",
        "title":       (ev.get("title") or "").strip(),
        "date":        start.isoformat(),
        "end_date":    end.isoformat(),
        "time":        (ev.get("time") or "").strip(),
        "end_time":    (ev.get("end_time") or "").strip(),
        "venue":       venue,
        "area":        area,
        "category":    (ev.get("ai_event_type") or ev.get("category") or "Event").strip(),
        "tags":        tags,
        "description": summary[:600],
        "url":         (ev.get("url") or "").strip(),
        "image":       (ev.get("image") or "").strip(),
        "source":      (ev.get("source") or "").strip(),
    }


def load_public_events() -> list[dict]:
    with open(EVENTS_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    for ev in raw:
        p = _public_event(ev)
        if p and p["title"]:
            out.append(p)
    out.sort(key=lambda e: (e["date"], e["title"]))
    return out


# ── EXPERIENCES extraction from index.html ────────────────────────────────────
# Each entry is a single line of the form:
#     { id: 70, name: 'The Onyx Theatre', sub: '...', tags: ['Film', ...], ... }
# Mixed single/double quotes in values. We do a state-tracked JS-to-JSON
# rewrite then json.loads. The format is admin-controlled (saveAll writes
# one entry per line) so parsing is stable.

_EXP_BLOCK_RE = re.compile(
    r"^const\s+EXPERIENCES\s*=\s*\[\s*$(.*?)^\];",
    re.M | re.S,
)

def _js_object_to_json(s: str) -> str:
    """Convert a JavaScript object literal to a JSON string.
    Handles: single-quoted strings, unquoted keys, trailing commas.
    Does NOT handle: template literals, comments, computed keys (none used)."""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "'":
            j = i + 1
            buf = []
            while j < n and s[j] != "'":
                if s[j] == "\\" and j + 1 < n:
                    buf.append(s[j])
                    buf.append(s[j + 1])
                    j += 2
                    continue
                buf.append(s[j])
                j += 1
            inner = "".join(buf).replace('"', '\\"')
            out.append('"' + inner + '"')
            i = j + 1
        elif c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                if s[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                j += 1
            out.append(s[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    js = "".join(out)
    # Quote unquoted keys (after { or , whitespace).
    js = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', js)
    # Drop trailing commas inside objects/arrays.
    js = re.sub(r',(\s*[}\]])', r'\1', js)
    return js


def load_public_venues() -> list[dict]:
    """Extract the EXPERIENCES array from index.html as a list of dicts.
    Filters to public fields; drops the `photo` URL fingerprint and other
    non-essential layout fields."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    m = _EXP_BLOCK_RE.search(html)
    if not m:
        print("  [feeds] WARNING: could not locate EXPERIENCES array in index.html")
        return []
    body = m.group(1)

    venues = []
    skipped = 0
    for raw_line in body.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line.startswith("{") or not line.endswith("}"):
            continue
        try:
            obj = json.loads(_js_object_to_json(line))
        except Exception as e:
            skipped += 1
            continue
        venues.append({
            "id":          obj.get("id"),
            "name":        obj.get("name", ""),
            "blurb":       obj.get("sub", ""),
            "area":        obj.get("area", ""),
            "type":        obj.get("type", ""),
            "tags":        obj.get("tags", []) or [],
            "hours":       obj.get("hours", ""),
            "notes":       obj.get("notes", ""),
            "url":         obj.get("url", ""),
            "directions":  obj.get("directions", ""),
            "lat":         obj.get("lat"),
            "lng":         obj.get("lng"),
            "season":      obj.get("season", "Year-Round"),
            "icon":        obj.get("icon", ""),
            "photo":       obj.get("photo", ""),
        })
    if skipped:
        print(f"  [feeds] skipped {skipped} unparseable EXPERIENCES line(s)")
    return venues


# ── iCal generation ───────────────────────────────────────────────────────────
# RFC 5545 with the bits that calendar apps actually want.
#   - VEVENT per event
#   - DTSTART;VALUE=DATE for all-day, DTSTART:YYYYMMDDTHHMMSS for timed
#   - DTSTAMP / UID required
#   - Folding at 75 octets (we keep it simple and let SUMMARY/DESCRIPTION fit
#     in one line; long descriptions wrapped naively).

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*([apAP])[\.\s]?[mM]?\.?")

def _parse_time(s: str) -> tuple[int, int] | None:
    """Parse '7:30 PM' / '7 PM' / '7:30pm' into (24h hour, minute) or None."""
    m = _TIME_RE.match(s or "")
    if not m:
        return None
    h = int(m.group(1)) % 12
    mi = int(m.group(2) or 0)
    if m.group(3).lower() == "p":
        h += 12
    return h, mi


def _ical_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _ical_fold(line: str) -> str:
    """RFC 5545 line folding at 75 octets."""
    if len(line.encode("utf-8")) <= 75:
        return line
    parts, cur = [], []
    size = 0
    for ch in line:
        b = ch.encode("utf-8")
        if size + len(b) > 75:
            parts.append("".join(cur))
            cur = [" ", ch]
            size = 1 + len(b)
        else:
            cur.append(ch)
            size += len(b)
    parts.append("".join(cur))
    return "\r\n".join(parts)


def generate_ics(events: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nevada County Experience//Events Feed//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Nevada County Experience",
        "X-WR-CALDESC:Aggregated events across Western Nevada County, CA.",
        "X-WR-TIMEZONE:America/Los_Angeles",
    ]
    for ev in events:
        uid = (ev["id"] or ev["title"]) + "@nevadacountyexperience"
        ds  = ev["date"].replace("-", "")
        de  = ev["end_date"].replace("-", "")

        tstart = _parse_time(ev["time"])
        tend   = _parse_time(ev["end_time"])
        if tstart:
            sh, sm = tstart
            eh, em = tend if tend else (sh + 1, sm)   # default 1-hour duration
            if eh >= 24: eh, em = 23, 59
            dtstart = f"DTSTART;TZID=America/Los_Angeles:{ds}T{sh:02d}{sm:02d}00"
            dtend   = f"DTEND;TZID=America/Los_Angeles:{ds}T{eh:02d}{em:02d}00"
        else:
            # All-day; DTEND is exclusive so add 1 day to inclusive end.
            try:
                end_dt = (date.fromisoformat(ev["end_date"]))
                from datetime import timedelta
                dtend_d = (end_dt + timedelta(days=1)).strftime("%Y%m%d")
            except Exception:
                dtend_d = de
            dtstart = f"DTSTART;VALUE=DATE:{ds}"
            dtend   = f"DTEND;VALUE=DATE:{dtend_d}"

        loc_parts = [ev["venue"], ev["area"]]
        location = ", ".join([p for p in loc_parts if p])

        cats = ev["tags"] or [ev["category"]]
        cats_str = ",".join(_ical_escape(t) for t in cats if t)

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now}")
        lines.append(dtstart)
        lines.append(dtend)
        lines.append(_ical_fold(f"SUMMARY:{_ical_escape(ev['title'])}"))
        if location:
            lines.append(_ical_fold(f"LOCATION:{_ical_escape(location)}"))
        if ev["description"]:
            lines.append(_ical_fold(f"DESCRIPTION:{_ical_escape(ev['description'])}"))
        if ev["url"]:
            lines.append(f"URL:{ev['url']}")
        if cats_str:
            lines.append(_ical_fold(f"CATEGORIES:{cats_str}"))
        if ev["source"]:
            lines.append(_ical_fold(f"X-SOURCE:{_ical_escape(ev['source'])}"))
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ── RSS 2.0 generation ────────────────────────────────────────────────────────

def _rfc822(dt_iso: str) -> str:
    """YYYY-MM-DD -> RFC 822 datetime string in PT noon (so it always lands on
    the correct local day regardless of reader timezone)."""
    try:
        d = date.fromisoformat(dt_iso)
        # Noon Pacific ≈ 19:00 UTC (within DST drift); good enough for sort/pub.
        return d.strftime("%a, %d %b %Y 19:00:00 GMT")
    except Exception:
        return ""


def generate_rss(events: list[dict]) -> str:
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items = []
    for ev in events:
        loc = ", ".join([p for p in [ev["venue"], ev["area"]] if p])
        date_label = ev["date"] if ev["date"] == ev["end_date"] else f"{ev['date']} – {ev['end_date']}"
        body = []
        body.append(f"<p><strong>{xml_escape(date_label)}</strong>")
        if ev["time"]:
            body.append(f" · {xml_escape(ev['time'])}")
        body.append("</p>")
        if loc:
            body.append(f"<p>📍 {xml_escape(loc)}</p>")
        if ev["description"]:
            body.append(f"<p>{xml_escape(ev['description'])}</p>")
        if ev["source"]:
            body.append(f"<p><em>Source: {xml_escape(ev['source'])}</em></p>")
        desc_html = "".join(body)

        cat_xml = "".join(
            f"    <category>{xml_escape(t)}</category>\n" for t in (ev["tags"] or []) if t
        )
        link = ev["url"] or SITE_URL
        guid = ev["id"] or ev["title"]
        items.append(
            f"""  <item>
    <title>{xml_escape(ev['title'])}</title>
    <link>{xml_escape(link)}</link>
    <guid isPermaLink="false">{xml_escape(str(guid))}</guid>
    <pubDate>{_rfc822(ev['date'])}</pubDate>
{cat_xml}    <description>{xml_escape(desc_html)}</description>
  </item>"""
        )
    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Nevada County Experience — Events</title>
  <link>{SITE_URL}</link>
  <description>Aggregated upcoming events across Western Nevada County, California. Updated nightly.</description>
  <language>en-us</language>
  <lastBuildDate>{now_rfc}</lastBuildDate>
  <atom:link href="{FEED_BASE}events.rss" rel="self" type="application/rss+xml" />
{items_xml}
</channel>
</rss>
"""


# ── Public JSON ───────────────────────────────────────────────────────────────

def generate_events_json(events: list[dict]) -> str:
    payload = {
        "feed":         "Nevada County Experience — Events",
        "homepage":     SITE_URL,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count":        len(events),
        "license":      "CC BY 4.0 — attribution required",
        "attribution":  "Nevada County Experience — https://liammlrb-eng.github.io/nevada-county-experiences/",
        "events":       events,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def generate_venues_json(venues: list[dict]) -> str:
    payload = {
        "feed":         "Nevada County Experience — Curated Venues & Experiences",
        "homepage":     SITE_URL,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count":        len(venues),
        "license":      "CC BY 4.0 — attribution required",
        "attribution":  "Nevada County Experience — https://liammlrb-eng.github.io/nevada-county-experiences/",
        "venues":       venues,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ── Driver ────────────────────────────────────────────────────────────────────

def build():
    FEEDS_DIR.mkdir(exist_ok=True)
    events = load_public_events()
    venues = load_public_venues()

    files = {
        "events.ics":  generate_ics(events),
        "events.rss":  generate_rss(events),
        "events.json": generate_events_json(events),
        "venues.json": generate_venues_json(venues),
    }
    for fname, body in files.items():
        path = FEEDS_DIR / fname
        path.write_text(body, encoding="utf-8", newline="")
        print(f"  [feeds] wrote {path.relative_to(ROOT_DIR)}  ({len(body):,} bytes)")
    print(f"  [feeds] {len(events)} events, {len(venues)} venues published")
    return events, venues


if __name__ == "__main__":
    build()

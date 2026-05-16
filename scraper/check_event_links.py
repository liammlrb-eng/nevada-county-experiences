"""
check_event_links.py — verify the URL on every event in the queue.

Runs as the final step of the nightly scrape (event_scraper.py calls
check_all() at the end) and can also be run standalone:

    python check_event_links.py            # check every event
    python check_event_links.py --new-only # only events never checked before

For each event with a `url`, performs a HEAD request (falling back to GET
when HEAD is refused). The result is written back onto the event:

    url_ok       bool   — True if the URL returned a success status
    url_status   str    — "200", "404", "timeout", "error: <msg>", ...
    url_checked  str    — "YYYY-MM-DD HH:MM" of the last check

Events that fail (url_ok == False) are FLAGGED — the admin Events Queue
shows a warning marker so a human can fix or dismiss them. A broken link
does not hide the event from the public site; the event still happened,
the "More Info" link just needs attention.

Concurrency: a thread pool keeps a full ~1,000-event sweep to a few
minutes. Politeness: one request per URL, 12-second timeout, realistic
User-Agent.
"""
import os, sys, json, argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(SCRIPT_DIR)
EVENTS_FILE = os.path.join(ROOT_DIR, "scraper_output", "events.json")

# Force UTF-8 console output (Windows defaults to cp1252 — see event_scraper.py)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
}
_TIMEOUT = 12
_MAX_WORKERS = 10


def check_url(url: str) -> tuple:
    """Return (ok: bool, status: str). A URL is OK when it returns a
    2xx or 3xx status. 4xx/5xx, timeouts, and connection errors fail."""
    if not url or not url.strip():
        return (False, "no url")
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return (False, "bad scheme")
    try:
        # HEAD first — cheap, no body download
        r = requests.head(url, headers=_HEADERS, timeout=_TIMEOUT,
                           allow_redirects=True)
        # Some servers refuse HEAD (405) or mishandle it — retry with GET
        if r.status_code in (403, 405, 501) or r.status_code >= 500:
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT,
                             allow_redirects=True, stream=True)
            r.close()
        ok = 200 <= r.status_code < 400
        return (ok, str(r.status_code))
    except requests.exceptions.Timeout:
        return (False, "timeout")
    except requests.exceptions.ConnectionError:
        return (False, "connection error")
    except requests.exceptions.RequestException as e:
        return (False, f"error: {type(e).__name__}")


def check_all(new_only: bool = False) -> dict:
    """Check every event's URL, write results back to events.json.
    Returns a summary dict. Safe to call from event_scraper.py."""
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)
    except Exception as e:
        print(f"  Link check: could not read events.json ({e})")
        return {"checked": 0, "flagged": 0}

    # Which events to check
    todo = []
    for ev in events:
        if not ev.get("url"):
            continue
        if new_only and ev.get("url_checked"):
            continue
        todo.append(ev)

    if not todo:
        print("  Link check: nothing to check")
        return {"checked": 0, "flagged": 0}

    print(f"  Link check: verifying {len(todo)} event URL(s)...")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    flagged = 0

    # Distinct URLs only — many events share a venue/source URL
    url_cache = {}
    distinct = list({ev["url"].strip() for ev in todo if ev.get("url")})

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(check_url, u): u for u in distinct}
        for fut in as_completed(futures):
            u = futures[fut]
            try:
                url_cache[u] = fut.result()
            except Exception as e:
                url_cache[u] = (False, f"error: {type(e).__name__}")

    for ev in todo:
        ok, status = url_cache.get(ev["url"].strip(), (False, "error"))
        ev["url_ok"]      = ok
        ev["url_status"]  = status
        ev["url_checked"] = stamp
        if not ok:
            flagged += 1

    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print(f"  Link check: {len(todo)} checked, {flagged} flagged "
          f"(broken / unreachable URL)")
    # List the flagged ones so the nightly log shows them
    if flagged:
        print("  Flagged for admin follow-up:")
        for ev in todo:
            if not ev.get("url_ok"):
                title = (ev.get("title") or "")[:55]
                print(f"    [{ev.get('url_status','?'):>16}]  {title}  "
                      f"({ev.get('source','?')})")
    return {"checked": len(todo), "flagged": flagged}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-only", action="store_true",
                    help="only check events with no previous url_checked stamp")
    args = ap.parse_args()
    print("=" * 56)
    print("  Event link checker")
    print("=" * 56)
    result = check_all(new_only=args.new_only)
    print("=" * 56)

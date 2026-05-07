#!/usr/bin/env python3
"""
Nevada County Experience — Local Development & Demo Server
===========================================================
Runs on http://localhost:5000

Serves the static site + a small JSON API that powers the admin
"Events Queue" panel.  On a traditional production server (Apache/Nginx)
this script runs as a systemd service alongside the web server.

Usage:
  python server.py              # starts on port 5000
  python server.py --port 8080  # custom port

API endpoints:
  GET  /                         → index.html (static site)
  GET  /api/events               → scraper_output/events.json
  GET  /api/sources              → scraper/sources.json
  POST /api/events/<id>/approve  → mark event approved (adds to DB)
  POST /api/events/<id>/dismiss  → mark event dismissed
  POST /api/scrape               → run scraper in background
  GET  /api/scrape/status        → current scrape status
"""

import os, sys, json, threading, subprocess, argparse
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, abort, Response

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.join(BASE_DIR, "scraper")
OUT_DIR     = os.path.join(BASE_DIR, "scraper_output")
EVENTS_FILE = os.path.join(OUT_DIR, "events.json")
SOURCES_FILE= os.path.join(SCRAPER_DIR, "sources.json")
SCRAPER_PY  = os.path.join(SCRAPER_DIR, "event_scraper.py")
AI_PY       = os.path.join(SCRAPER_DIR, "ai_categorize.py")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")

# ── Scrape job state ─────────────────────────────────────────────────────────
_scrape_status = {
    "running":    False,
    "last_run":   None,
    "last_added": 0,
    "last_total": 0,
    "last_error": None,
}
_scrape_lock = threading.Lock()

# ── AI categorization job state ──────────────────────────────────────────────
_ai_status = {
    "running":     False,
    "last_run":    None,
    "last_processed": 0,
    "last_failed": 0,
    "last_error":  None,
}
_ai_lock = threading.Lock()


# ── Static site ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    """Serve any other static file (CSS, images, etc.)."""
    return send_from_directory(BASE_DIR, filename)


# ── Events API ────────────────────────────────────────────────────────────────
def _load_events():
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def _save_events(events):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


@app.route("/api/events")
def get_events():
    """Return all events (or filter by ?status=pending|approved|dismissed)."""
    events = _load_events()
    status_filter = request.args.get("status")
    if status_filter:
        events = [e for e in events if e.get("status") == status_filter]
    return jsonify(events)


@app.route("/api/events/<event_id>/approve", methods=["POST"])
def approve_event(event_id):
    """Mark an event as approved so it appears in the public events feed."""
    events = _load_events()
    for ev in events:
        if str(ev.get("id", "")) == event_id or ev.get("scraper_id") == event_id:
            ev["status"] = "approved"
            ev["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break
    else:
        return jsonify({"error": "event not found"}), 404
    _save_events(events)
    return jsonify({"ok": True})


@app.route("/api/events/approve-all", methods=["POST"])
def approve_all_events():
    """
    Approve all pending events that are today or in the future.
    Pending events whose date has already passed are auto-dismissed instead.
    """
    events = _load_events()
    today  = datetime.now().strftime("%Y-%m-%d")
    now    = datetime.now().strftime("%Y-%m-%d %H:%M")
    approved_count  = 0
    dismissed_count = 0
    for ev in events:
        if ev.get("status") != "pending":
            continue
        date = ev.get("date", "")
        if date and len(date) >= 10 and date < today:
            # Past event — auto-dismiss so it doesn't come back on next scrape
            ev["status"]       = "dismissed"
            ev["dismissed_at"] = now
            dismissed_count   += 1
        else:
            ev["status"]      = "approved"
            ev["approved_at"] = now
            approved_count   += 1
    _save_events(events)
    return jsonify({"ok": True, "approved": approved_count, "dismissed": dismissed_count})


@app.route("/api/events/prune", methods=["POST"])
def prune_events():
    """
    Remove events past their useful life:
      - pending / approved : pruned once their date has passed
      - dismissed          : pruned 60 days after their event date
    Events with no/unparseable date are left alone.
    """
    from datetime import timedelta, date as date_type
    events     = _load_events()
    today      = datetime.now().date()
    cutoff_dis = today - timedelta(days=60)
    kept, pruned = [], 0
    for ev in events:
        d      = ev.get("date", "")
        status = ev.get("status", "pending")
        if not d or len(d) < 10:
            kept.append(ev); continue
        try:
            ev_date = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            kept.append(ev); continue
        if status == "dismissed":
            if ev_date >= cutoff_dis: kept.append(ev)
            else: pruned += 1
        elif ev_date >= today: kept.append(ev)
        else: pruned += 1
    _save_events(kept)
    return jsonify({"ok": True, "pruned": pruned, "remaining": len(kept)})


@app.route("/api/events/<event_id>/dismiss", methods=["POST"])
def dismiss_event(event_id):
    """Mark an event as dismissed — won't re-appear after future scrapes."""
    events = _load_events()
    for ev in events:
        if str(ev.get("id", "")) == event_id or ev.get("scraper_id") == event_id:
            ev["status"] = "dismissed"
            ev["dismissed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break
    else:
        return jsonify({"error": "event not found"}), 404
    _save_events(events)
    return jsonify({"ok": True})


# ── RSS Feed ─────────────────────────────────────────────────────────────────
@app.route("/feed.rss")
@app.route("/feed/")
def rss_feed():
    """
    Serve approved events as an RSS 2.0 feed.
    Consumers: other websites, podcast apps, calendar tools.
    """
    events = [e for e in _load_events() if e.get("status") == "approved"]
    # Most recent first
    events.sort(key=lambda e: e.get("date", ""), reverse=True)

    def _esc(s: str) -> str:
        """Minimal XML character escaping."""
        return (str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    now_rfc = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    site_url = request.host_url.rstrip("/")

    items_xml = []
    for ev in events[:100]:   # cap at 100 items
        title   = _esc(ev.get("title", ""))
        link    = _esc(ev.get("url") or f"{site_url}/#events")
        desc    = _esc(ev.get("description", ""))
        date    = ev.get("date", "")
        time    = ev.get("time", "")
        loc     = _esc(ev.get("location", ""))
        source  = _esc(ev.get("source", ""))
        tags    = ev.get("tags", [])
        cats    = "".join(f"    <category>{_esc(t)}</category>\n" for t in tags) if tags else ""

        # pubDate: use event date if available
        pub_date = now_rfc
        if date:
            try:
                from datetime import timezone, timedelta
                dt = datetime.strptime(date, "%Y-%m-%d")
                pub_date = dt.strftime("%a, %d %b %Y 00:00:00 -0700")
            except Exception:
                pass

        loc_line = f"    <description>{_esc(f'{time} — {loc} — {desc}' if loc else f'{time} — {desc}')}</description>\n" if (time or loc or desc) else f"    <description>{desc}</description>\n"

        items_xml.append(f"""  <item>
    <title>{title}</title>
    <link>{link}</link>
    <guid isPermaLink="false">{_esc(ev.get('scraper_id', link))}</guid>
    <pubDate>{pub_date}</pubDate>
    <source url="{site_url}/feed.rss">{source}</source>
{cats}{loc_line}  </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Nevada County Experience — Events</title>
    <link>{site_url}</link>
    <description>Upcoming events in Nevada County, California</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{site_url}/feed.rss" rel="self" type="application/rss+xml"/>
{chr(10).join(items_xml)}
  </channel>
</rss>"""

    return Response(feed, mimetype="application/rss+xml")


# ── Sources API ───────────────────────────────────────────────────────────────
@app.route("/api/sources")
def get_sources():
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify([])


@app.route("/api/sources", methods=["POST"])
def save_sources():
    """Replace the full sources list."""
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "expected JSON array"}), 400
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({"ok": True, "count": len(data)})


# ── Scrape API ────────────────────────────────────────────────────────────────
@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    """Start the scraper in a background thread (non-blocking)."""
    with _scrape_lock:
        if _scrape_status["running"]:
            return jsonify({"ok": False, "message": "Scrape already running"}), 409
        _scrape_status["running"] = True
        _scrape_status["last_error"] = None

    thread = threading.Thread(target=_run_scraper, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Scrape started"})


@app.route("/api/scrape/status")
def scrape_status():
    return jsonify(dict(_scrape_status))


# ── AI Categorize API ────────────────────────────────────────────────────────
@app.route("/api/ai/categorize", methods=["POST"])
def trigger_ai_categorize():
    """Run ai_categorize.py as a background thread.

    Optional JSON body:
      { "limit": 5, "force": false, "source": "KVMR" }
    """
    with _ai_lock:
        if _ai_status["running"]:
            return jsonify({"ok": False, "message": "AI categorization already running"}), 409
        _ai_status["running"] = True
        _ai_status["last_error"] = None

    body  = request.get_json(silent=True) or {}
    limit = body.get("limit")
    force = bool(body.get("force"))
    src   = body.get("source")

    thread = threading.Thread(
        target=_run_ai_categorize, args=(limit, force, src), daemon=True
    )
    thread.start()
    return jsonify({"ok": True, "message": "AI categorization started"})


@app.route("/api/ai/status")
def ai_status():
    # Detect whether an API key is configured (env var or scraper/config.py)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not has_key:
        try:
            sys.path.insert(0, SCRAPER_DIR)
            import config as _cfg
            has_key = bool(getattr(_cfg, "ANTHROPIC_API_KEY", None))
        except Exception:
            pass
    out = dict(_ai_status)
    out["has_key"] = has_key
    return jsonify(out)


def _run_ai_categorize(limit=None, force=False, source=None):
    """Run ai_categorize.py as a subprocess."""
    try:
        cmd = [sys.executable, "-X", "utf8", AI_PY]
        if limit:  cmd += ["--limit", str(int(limit))]
        if force:  cmd += ["--force"]
        if source: cmd += ["--source", str(source)]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, encoding="utf-8"
        )
        import re
        proc_m = re.search(r"Processed\s*:\s*(\d+)", result.stdout)
        fail_m = re.search(r"Failed\s*:\s*(\d+)",    result.stdout)

        with _ai_lock:
            _ai_status["running"]        = False
            _ai_status["last_run"]       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _ai_status["last_processed"] = int(proc_m.group(1)) if proc_m else 0
            _ai_status["last_failed"]    = int(fail_m.group(1)) if fail_m else 0
            if result.returncode != 0:
                _ai_status["last_error"] = (result.stderr[:500]
                                            or result.stdout[-500:]
                                            or "Non-zero exit code")
    except Exception as e:
        with _ai_lock:
            _ai_status["running"]    = False
            _ai_status["last_run"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _ai_status["last_error"] = str(e)


def _run_scraper():
    """Run event_scraper.py as a subprocess."""
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", SCRAPER_PY],
            capture_output=True, text=True, timeout=300, encoding="utf-8"
        )
        # Parse counts from stdout
        import re
        scraped_m = re.search(r"Scraped this run\s*:\s*(\d+)", result.stdout)
        added_m   = re.search(r"New \(added\)\s*:\s*(\d+)", result.stdout)
        total_m   = re.search(r"Total in queue\s*:\s*(\d+)", result.stdout)

        with _scrape_lock:
            _scrape_status["running"]    = False
            _scrape_status["last_run"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _scrape_status["last_added"] = int(added_m.group(1)) if added_m else 0
            _scrape_status["last_total"] = int(total_m.group(1)) if total_m else 0
            if result.returncode != 0:
                _scrape_status["last_error"] = result.stderr[:500] or "Non-zero exit code"
    except Exception as e:
        with _scrape_lock:
            _scrape_status["running"]    = False
            _scrape_status["last_run"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _scrape_status["last_error"] = str(e)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--host", type=str, default="127.0.0.1")
    args = ap.parse_args()

    print("=" * 56)
    print("  Nevada County Experience — Local Server")
    print(f"  http://{args.host}:{args.port}/")
    print("  Press Ctrl+C to stop")
    print("=" * 56)
    app.run(host=args.host, port=args.port, debug=False)

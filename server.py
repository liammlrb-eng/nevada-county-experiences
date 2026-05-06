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
from flask import Flask, jsonify, request, send_from_directory, abort

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.join(BASE_DIR, "scraper")
OUT_DIR     = os.path.join(BASE_DIR, "scraper_output")
EVENTS_FILE = os.path.join(OUT_DIR, "events.json")
SOURCES_FILE= os.path.join(SCRAPER_DIR, "sources.json")
SCRAPER_PY  = os.path.join(SCRAPER_DIR, "event_scraper.py")

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

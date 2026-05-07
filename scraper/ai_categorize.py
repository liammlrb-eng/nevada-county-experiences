#!/usr/bin/env python3
"""
Nevada County Experience — AI Event Categorizer
================================================
Enriches scraped events with AI-derived tags, area, venue, and event_type
using Claude Haiku 3.5 via the Anthropic API.

Why this exists:
    Scrapers produce raw events with keyword-based tags. Some sources (KVMR)
    label everything area="Nevada County" with no venue and weak tags.
    This script reads each event's title + description and uses Claude Haiku
    to fill in the gaps without losing the originals.

Output fields added (all prefixed `ai_` to preserve scraper data):
    ai_tags        list[str]   — refined tag list from controlled vocabulary
    ai_area        str         — Nevada City | Grass Valley | Truckee | …
    ai_venue       str         — extracted venue name (or "")
    ai_event_type  str         — Music venue | Art event | Workshop | …
    ai_summary     str         — one-line clean blurb (no scraper boilerplate)
    ai_quality     str         — high | medium | low (low → consider auto-dismiss)
    ai_categorized_at  str     — timestamp; presence means "already processed"

Usage:
    # Default: categorize all pending events without ai_tags
    python ai_categorize.py

    # Test run — only process 5 events
    python ai_categorize.py --limit 5

    # Re-categorize everything (override existing ai_* fields)
    python ai_categorize.py --force

    # Process only events from one source
    python ai_categorize.py --source KVMR

API key:
    Set environment variable ANTHROPIC_API_KEY.  In PowerShell:
        $env:ANTHROPIC_API_KEY = "sk-ant-..."
    Or place it in scraper/config.py as ANTHROPIC_API_KEY = "sk-ant-..."

Cost (Haiku 3.5 @ $0.80/M input, $4/M output):
    ~150 input + ~120 output tokens per event ≈ $0.0006 / event.
    460 events ≈ $0.28 for a full re-categorization run.
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import time
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
ROOT_DIR    = SCRIPT_DIR.parent
EVENTS_FILE = ROOT_DIR / "scraper_output" / "events.json"

# ── Controlled vocabulary (must match THEMES tags in index.html) ──────────────
ALLOWED_TAGS = [
    # Arts, Culture & Music
    "Music", "Theater", "Film", "Dance", "Art", "Festival", "Artistic",
    # Hands-on
    "Hands-on", "Workshop", "Craft", "Lecture",
    # Foodie
    "Foodie", "Food & Drink", "Market",
    # Active & Outdoors
    "Active", "Scenic", "Sport", "Nature", "Outdoor", "Environment",
    "Hiking", "Biking", "Running", "Swimming", "Boating", "Fishing",
    # Wellness & Spiritual
    "Spiritual", "Wellness",
    # Family / Community
    "Family", "Community", "Holiday", "Social",
    # Historic
    "Historic", "Gold Rush",
    # Other
    "Fundraiser",
]

ALLOWED_AREAS = [
    # Western Nevada County (the focus of this build)
    "Nevada City", "Grass Valley", "Penn Valley", "North San Juan",
    "Rough and Ready", "Washington", "Chicago Park", "Cedar Ridge",
    "Smartsville", "Near Nevada City",
    # Adjacent areas commonly visited
    "Colfax",         # Placer County, immediately adjacent
    # Generic fallbacks
    "Nevada County",  # county-wide / unknown
    "Online",
]

ALLOWED_EVENT_TYPES = [
    "Music venue", "Art event", "Theater", "Film",
    "Workshop", "Lecture", "Class", "Festival",
    "Outdoor", "Wellness", "Restaurant", "Brewery",
    "Tasting room", "Winery", "Bakery", "Gallery",
    "Museum", "Historic site", "Activity",
    "Community Event", "Fundraiser",
]

# Common boilerplate to strip from descriptions before sending to AI
_BOILERPLATE_FRAGMENTS = [
    "The post",
    "appeared first on KVMR",
    "appeared first on KVMR Community Radio",
]


# ── Config / API key loading ──────────────────────────────────────────────────
def get_api_key() -> str | None:
    """Read API key from env var first, then config.py as fallback."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key.strip()
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import config
        return getattr(config, "ANTHROPIC_API_KEY", None)
    except Exception:
        return None


# ── Event loader / writer ─────────────────────────────────────────────────────
def load_events() -> list[dict]:
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events(events: list[dict]) -> None:
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


# ── Prompt construction ───────────────────────────────────────────────────────
def _clean_description(desc: str) -> str:
    """Strip scraper boilerplate before sending to API."""
    if not desc:
        return ""
    out = desc
    for frag in _BOILERPLATE_FRAGMENTS:
        idx = out.find(frag)
        if idx > 0:
            out = out[:idx].rstrip(" .•")
    return out[:500]  # cap length to control input cost


def build_batch_prompt(events: list[dict]) -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for a batch of events.
    Returns JSON list of enrichments, one per event, in the same order.
    """
    system = f"""You are an event categorizer for a Nevada County, California tourism site.
For each event, return a JSON object with refined metadata.

Constraints:
- tags: choose 1-4 from this exact list (case-sensitive):
  {", ".join(ALLOWED_TAGS)}
- area: choose ONE from this exact list:
  {", ".join(ALLOWED_AREAS)}
  Use "Nevada County" only when no specific community can be inferred.
  This site covers WESTERN Nevada County (Gold Country foothills) — events
  located in Truckee or other Sierra-side communities are out of scope and
  should be marked quality="low".
  Recognize western Nevada County venues:
   - Center for the Arts, Holbrooke Hotel, Empire Mine → Grass Valley
   - Miners Foundry, Nevada Theatre, Hardy Books, Nat'l Exchange → Nevada City
   - Lake Wildwood, Western Gateway Park, Penn Valley Rodeo → Penn Valley
   - Rollins Lake area, Greenhorn Campground → Chicago Park
   - Englebright Lake → Smartsville
- venue: extract the venue NAME if mentioned (e.g. "Center for the Arts"),
  empty string if not.
- event_type: choose ONE from this exact list:
  {", ".join(ALLOWED_EVENT_TYPES)}
- summary: a single sentence describing the event in ≤25 words. No scraper
  boilerplate ("The post...", "appeared first on...").
- quality: "high" for clear, well-described events; "medium" for thin info;
  "low" for spam/test/duplicate/unintelligible items that should be auto-dismissed.

Return ONLY a JSON array, no prose. Each array element corresponds to the
same-index input event."""

    items = []
    for i, ev in enumerate(events):
        items.append({
            "i": i,
            "title": ev.get("title", "")[:200],
            "description": _clean_description(ev.get("description", "")),
            "source_area": ev.get("area", ""),
            "source_location": ev.get("location", ""),
            "source_category": ev.get("category", ""),
            "source_tags": ev.get("tags", []),
        })

    user = (
        "Categorize these events. Return a JSON array of objects, "
        "one per input event, each with keys: tags, area, venue, "
        "event_type, summary, quality.\n\n"
        f"Events:\n{json.dumps(items, ensure_ascii=False, indent=2)}"
    )
    return system, user


# ── API call ──────────────────────────────────────────────────────────────────
def call_claude(api_key: str, system: str, user: str,
                model: str = "claude-haiku-4-5",
                max_tokens: int = 4000) -> str:
    """
    Call Anthropic Messages API. Returns the text content.
    Uses requests instead of the SDK to avoid an extra dependency.
    """
    import requests
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    # Concatenate all text blocks
    return "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")


def parse_response(text: str, expected_count: int) -> list[dict]:
    """Parse JSON array from model response. Handles markdown code fences."""
    s = text.strip()
    # Strip markdown code fences if present
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.rsplit("```", 1)[0].strip()
    # Find the array bounds
    start = s.find("[")
    end   = s.rfind("]")
    if start < 0 or end < 0:
        raise ValueError(f"No JSON array in response: {text[:200]}")
    arr = json.loads(s[start:end + 1])
    if not isinstance(arr, list):
        raise ValueError("Response is not a JSON array")
    if len(arr) != expected_count:
        print(f"  WARN: expected {expected_count} items, got {len(arr)}")
    return arr


# ── Validation / sanitization ─────────────────────────────────────────────────
def sanitize(item: dict) -> dict:
    """Clamp fields to allowed values."""
    out = {}
    # Tags: keep only allowed, dedup, max 4
    raw_tags = item.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    seen = set()
    clean_tags = []
    for t in raw_tags:
        if t in ALLOWED_TAGS and t not in seen:
            seen.add(t)
            clean_tags.append(t)
        if len(clean_tags) >= 4:
            break
    out["tags"] = clean_tags

    # Area
    a = item.get("area", "Nevada County")
    out["area"] = a if a in ALLOWED_AREAS else "Nevada County"

    # Venue: free string, capped
    out["venue"] = (item.get("venue") or "").strip()[:120]

    # Event type
    et = item.get("event_type", "")
    out["event_type"] = et if et in ALLOWED_EVENT_TYPES else "Activity"

    # Summary: capped
    out["summary"] = (item.get("summary") or "").strip()[:240]

    # Quality
    q = (item.get("quality") or "medium").lower()
    out["quality"] = q if q in ("high", "medium", "low") else "medium"
    return out


# ── Main loop ─────────────────────────────────────────────────────────────────
def categorize_batch(events: list[dict], api_key: str, model: str) -> list[dict]:
    system, user = build_batch_prompt(events)
    text = call_claude(api_key, system, user, model=model)
    raw = parse_response(text, len(events))
    return [sanitize(item) for item in raw]


def select_targets(events: list[dict], force: bool, source: str | None,
                   limit: int | None) -> list[int]:
    """Return indices of events to categorize."""
    indices = []
    for i, ev in enumerate(events):
        if source and ev.get("source") != source:
            continue
        if not force and ev.get("ai_categorized_at"):
            continue
        indices.append(i)
        if limit and len(indices) >= limit:
            break
    return indices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="Process only N events (for testing)")
    ap.add_argument("--force", action="store_true",
                    help="Re-categorize even if ai_* fields exist")
    ap.add_argument("--source", type=str, default=None,
                    help="Only process events from this source (e.g. 'KVMR')")
    ap.add_argument("--batch-size", type=int, default=15,
                    help="Events per API call (default: 15)")
    ap.add_argument("--model", type=str, default="claude-haiku-4-5",
                    help="Anthropic model name (default: claude-haiku-4-5)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be processed, don't call API")
    args = ap.parse_args()

    api_key = get_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  PowerShell:  $env:ANTHROPIC_API_KEY = 'sk-ant-...'")
        print("  Or paste into scraper/config.py as ANTHROPIC_API_KEY = 'sk-ant-...'")
        sys.exit(1)

    print("=" * 56)
    print("  Nevada County -- AI Event Categorizer")
    print(f"  Model      : {args.model}")
    print(f"  Batch size : {args.batch_size}")
    if args.force:  print("  Mode       : FORCE (re-categorize all)")
    if args.source: print(f"  Source     : {args.source}")
    if args.limit:  print(f"  Limit      : {args.limit}")
    if args.dry_run: print("  DRY RUN    : no API calls")
    print("=" * 56)

    events = load_events()
    targets = select_targets(events, args.force, args.source, args.limit)
    print(f"\nFound {len(targets)} event(s) to categorize "
          f"(of {len(events)} total).\n")

    if args.dry_run:
        for i in targets[:10]:
            ev = events[i]
            print(f"  [{i}] {ev.get('source','?'):20s} "
                  f"{ev.get('title','')[:60]}")
        if len(targets) > 10:
            print(f"  ... and {len(targets) - 10} more")
        return

    if not targets:
        print("Nothing to do.")
        return

    processed = 0
    failed = 0
    started = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for batch_start in range(0, len(targets), args.batch_size):
        batch_idx  = targets[batch_start:batch_start + args.batch_size]
        batch_evs  = [events[i] for i in batch_idx]

        print(f"  Batch {batch_start//args.batch_size + 1}: "
              f"{len(batch_evs)} events ... ", end="", flush=True)
        try:
            results = categorize_batch(batch_evs, api_key, args.model)
            for offset, enriched in enumerate(results):
                if offset >= len(batch_idx):
                    break
                i = batch_idx[offset]
                events[i]["ai_tags"]            = enriched["tags"]
                events[i]["ai_area"]            = enriched["area"]
                events[i]["ai_venue"]           = enriched["venue"]
                events[i]["ai_event_type"]      = enriched["event_type"]
                events[i]["ai_summary"]         = enriched["summary"]
                events[i]["ai_quality"]         = enriched["quality"]
                events[i]["ai_categorized_at"]  = timestamp
                processed += 1
            # Save incrementally — so a failure mid-run doesn't lose progress
            save_events(events)
            print(f"OK  ({processed} done)")
        except Exception as e:
            failed += len(batch_evs)
            print(f"FAIL: {e}")

    elapsed = time.time() - started
    print(f"\n{'=' * 56}")
    print(f"  Processed  : {processed}")
    print(f"  Failed     : {failed}")
    print(f"  Elapsed    : {elapsed:.1f}s")
    print(f"  Saved -> {EVENTS_FILE.relative_to(ROOT_DIR)}")
    print(f"{'=' * 56}")


if __name__ == "__main__":
    main()

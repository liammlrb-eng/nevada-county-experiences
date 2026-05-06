#!/usr/bin/env python3
"""
Nevada County Experience — Scraper
===================================
Discovers new candidate experiences via Google Places API
and checks existing entry URLs for dead links.

Outputs:
  scraper_output/candidates.json  — new businesses to review in the app
  scraper_output/updates.json     — existing entries flagged for review

Run:
  cd scraper
  pip install -r requirements.txt
  python scraper.py
"""

import os, sys, json, re, time, math, requests
from datetime import datetime

# ── PATHS ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(SCRIPT_DIR)
INDEX_HTML   = os.path.join(ROOT_DIR, 'index.html')
OUTPUT_DIR   = os.path.join(ROOT_DIR, 'scraper_output')
CANDIDATES_F = os.path.join(OUTPUT_DIR, 'candidates.json')
UPDATES_F    = os.path.join(OUTPUT_DIR, 'updates.json')

# ── CONFIG ────────────────────────────────────────────────────────────────────
sys.path.insert(0, SCRIPT_DIR)
from config import (
    GOOGLE_PLACES_API_KEY as API_KEY,
    CENTER_LAT, CENTER_LNG, RADIUS_M,
    MIN_RATINGS, MIN_RATING,
)

PLACES_NEARBY = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'

# Google place types to search + the category label used in the app
SEARCH_TYPES = [
    ('winery',             'Winery'),
    ('restaurant',         'Restaurant'),
    ('museum',             'Museum'),
    ('art_gallery',        'Gallery'),
    ('tourist_attraction', 'Activity'),
    ('spa',                'Wellness'),
    ('bakery',             'Bakery'),
    ('lodging',            'Lodging'),
    ('park',               'Outdoor'),
    ('campground',         'Outdoor'),
    ('bar',                'Brewery'),   # filtered below to only keep breweries
]

# Rough bounding box for Nevada County — filters out Google results
# that technically match the type but are in Sacramento, Placer, etc.
LAT_MIN, LAT_MAX = 38.9,  39.5
LNG_MIN, LNG_MAX = -121.4, -120.5


# ── PARSE INDEX.HTML ──────────────────────────────────────────────────────────

def load_existing_names():
    """Return a set of lowercase experience names already in the database."""
    try:
        with open(INDEX_HTML, 'r', encoding='utf-8') as f:
            html = f.read()
        names = re.findall(r"name:\s*['\"]([^'\"]+)['\"]", html)
        return set(n.lower().strip() for n in names)
    except Exception as e:
        print(f"  WARN: Could not parse existing names: {e}")
        return set()


def load_existing_experiences():
    """Return list of {id, name, url} for all experiences in index.html."""
    exps = []
    try:
        with open(INDEX_HTML, 'r', encoding='utf-8') as f:
            html = f.read()
        # Each experience is a JS object literal — extract id, name, url fields
        for m in re.finditer(
            r'\{\s*id:\s*(\d+)[^}]*?name:\s*[\'"]([^\'"]+)[\'"][^}]*?url:\s*[\'"]([^\'"]*)[\'"]',
            html, re.DOTALL
        ):
            exps.append({
                'id':   int(m.group(1)),
                'name': m.group(2),
                'url':  m.group(3),
            })
    except Exception as e:
        print(f"  WARN: Could not parse existing experiences: {e}")
    return exps


# ── DEDUPLICATION ─────────────────────────────────────────────────────────────

def is_duplicate(name, existing_names):
    """Return True if name is already in the database (case-insensitive, partial match)."""
    n = name.lower().strip()
    if n in existing_names:
        return True
    for existing in existing_names:
        if n in existing or existing in n:
            return True
    return False


# ── URL HEALTH CHECK ──────────────────────────────────────────────────────────

def check_url(url, timeout=20):
    """Return (alive: bool, status: str)."""
    if not url or not url.startswith('http'):
        return None, 'no_url'
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; NCE-scraper/1.0)'}
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        alive = r.status_code < 400
        return alive, str(r.status_code)
    except Exception:
        pass
    try:  # some servers reject HEAD — fall back to GET
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers, stream=True)
        r.close()
        return r.status_code < 400, str(r.status_code)
    except Exception as e:
        return False, str(e)[:60]


# ── GOOGLE PLACES ─────────────────────────────────────────────────────────────

def fetch_nearby_page(place_type, page_token=None):
    """Fetch one page of nearby places from the Google Places API."""
    if page_token:
        params = {'pagetoken': page_token, 'key': API_KEY}
    else:
        params = {
            'location': f'{CENTER_LAT},{CENTER_LNG}',
            'radius':   RADIUS_M,
            'type':     place_type,
            'key':      API_KEY,
        }
    r = requests.get(PLACES_NEARBY, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def score_place(rating, n_ratings):
    """Relevance score: rating * log10(reviews). Higher = better."""
    if not rating or not n_ratings:
        return 0.0
    return round(rating * math.log10(max(n_ratings, 1)), 2)


def discover_candidates(existing_names):
    """Query Google Places for each category and return new candidates."""
    candidates  = []
    seen_ids    = set()

    for place_type, category_label in SEARCH_TYPES:
        print(f"  [{category_label:15s}] searching Google Places...")
        page_token = None
        pages      = 0

        while pages < 3:   # max 60 results per type (3 pages × 20)
            try:
                data = fetch_nearby_page(place_type, page_token)
            except Exception as e:
                print(f"    ERROR fetching {place_type}: {e}")
                break

            status = data.get('status', '')
            if status == 'ZERO_RESULTS':
                break
            if status != 'OK':
                print(f"    API returned: {status} — {data.get('error_message', '')}")
                break

            for place in data.get('results', []):
                pid  = place.get('place_id', '')
                name = place.get('name', '')

                # Dedup within this run
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                # Breweries: only keep if "brew" appears in the name
                if place_type == 'bar' and 'brew' not in name.lower():
                    continue

                # Already in the database
                if is_duplicate(name, existing_names):
                    continue

                # Outside Nevada County bounding box
                loc = place.get('geometry', {}).get('location', {})
                lat = loc.get('lat', 0)
                lng = loc.get('lng', 0)
                if not (LAT_MIN < lat < LAT_MAX and LNG_MIN < lng < LNG_MAX):
                    continue

                rating    = place.get('rating')
                n_ratings = place.get('user_ratings_total', 0)

                # Filter low-quality results
                if (rating or 0) < MIN_RATING or n_ratings < MIN_RATINGS:
                    continue

                candidates.append({
                    'place_id':    pid,
                    'name':        name,
                    'vicinity':    place.get('vicinity', ''),
                    'category':    category_label,
                    'google_type': place_type,
                    'rating':      rating,
                    'n_ratings':   n_ratings,
                    'score':       score_place(rating, n_ratings),
                    'lat':         lat,
                    'lng':         lng,
                    'maps_url':    f'https://www.google.com/maps/place/?q=place_id:{pid}',
                    'discovered':  datetime.now().strftime('%Y-%m-%d'),
                    'status':      'pending',   # pending | approved | dismissed
                })

            page_token = data.get('next_page_token')
            if not page_token:
                break

            pages += 1
            time.sleep(2)   # Google requires a short pause before using next_page_token

        time.sleep(0.4)   # be polite between category requests

    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates


# ── FRESHNESS CHECK ───────────────────────────────────────────────────────────

def check_freshness(experiences):
    """Check each experience URL and flag dead links."""
    issues = []
    total  = sum(1 for e in experiences if e.get('url'))
    done   = 0

    for exp in experiences:
        url = exp.get('url', '')
        if not url:
            continue

        done += 1
        alive, status = check_url(url)
        tag = 'OK  ' if alive else 'DEAD'
        print(f"  [{done:3d}/{total}] {tag} [{status:>5}]  {exp['name']}")

        if not alive:
            issues.append({
                'id':        exp['id'],
                'name':      exp['name'],
                'field':     'url',
                'issue':     'dead_link',
                'old_value': url,
                'new_value': None,
                'http_status': status,
                'checked':   datetime.now().strftime('%Y-%m-%d'),
                'status':    'pending',   # pending | fixed | dismissed
            })

        time.sleep(0.3)   # don't hammer venue websites

    return issues


# ── MERGE WITH EXISTING OUTPUT ────────────────────────────────────────────────

def load_existing_output(path):
    """Load previously saved candidates/updates so we preserve dismissed items."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def merge_candidates(old_list, new_list):
    """
    Keep dismissed/approved items from a previous run.
    New items with the same place_id don't overwrite manual status changes.
    """
    old_by_id = {item['place_id']: item for item in old_list if 'place_id' in item}
    merged    = []
    for item in new_list:
        pid = item.get('place_id')
        if pid and pid in old_by_id and old_by_id[pid]['status'] != 'pending':
            merged.append(old_by_id[pid])   # preserve user's decision
        else:
            merged.append(item)
    return merged


def merge_updates(old_list, new_list):
    """Keep dismissed updates, don't re-flag them."""
    old_dismissed = {
        (item['id'], item['field'])
        for item in old_list
        if item.get('status') == 'dismissed'
    }
    return [
        item for item in new_list
        if (item['id'], item['field']) not in old_dismissed
    ]


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY or API_KEY == 'PASTE_YOUR_KEY_HERE':
        print("ERROR: Open scraper/config.py and paste your Google Places API key.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 50)
    print("Nevada County Experience — Scraper")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # ── Load existing data ────────────────────────────────
    print("\nParsing index.html...")
    existing_names = load_existing_names()
    existing_exps  = load_existing_experiences()
    print(f"  {len(existing_names)} experience names loaded")
    print(f"  {len(existing_exps)} entries with URLs found")

    # ── Discovery ─────────────────────────────────────────
    print("\n--- DISCOVERY ---")
    new_candidates = discover_candidates(existing_names)
    old_candidates = load_existing_output(CANDIDATES_F)
    candidates     = merge_candidates(old_candidates, new_candidates)
    pending        = sum(1 for c in candidates if c.get('status') == 'pending')
    print(f"\n  {len(new_candidates)} new candidates found this run")
    print(f"  {pending} pending review (total in queue)")

    # ── Freshness ─────────────────────────────────────────
    print("\n--- FRESHNESS CHECK ---")
    new_updates = check_freshness(existing_exps)
    old_updates = load_existing_output(UPDATES_F)
    updates     = merge_updates(old_updates, new_updates)
    print(f"\n  {len(new_updates)} issues found this run")
    print(f"  {len(updates)} total issues in queue")

    # ── Write output ──────────────────────────────────────
    with open(CANDIDATES_F, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    with open(UPDATES_F, 'w', encoding='utf-8') as f:
        json.dump(updates, f, indent=2, ensure_ascii=False)

    print(f"\nOK candidates.json -- {len(candidates)} entries ({pending} pending)")
    print(f"OK updates.json    -- {len(updates)} issues")
    print("\nDone. Open the app → Manage Database → Review to process results.")


if __name__ == '__main__':
    main()

"""
ingest_trails.py — pull Nevada County trail geometry from OpenStreetMap
=======================================================================
For each curated trail in the TRAILS list below, fetch its OSM
relation (or ways) via the Overpass API and convert to a GeoJSON
LineString / MultiLineString feature. Output:

    data/trails.geojson      ← FeatureCollection consumed by index.html

The TRAILS list in index.html stores all the *editorial* metadata
(name, difficulty, blurb, dog/bike-friendly flags, etc.). This file
only handles geometry — the two are joined by `id` at render time.

Rerun this script any time we want to refresh the OSM geometry
(or, eventually, replace it with Nevada County ArcGIS data — the
output schema is the contract).

Usage:
    python tools/ingest_trails.py

Requires:
    pip install requests
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

import requests


# ── Curated trails ───────────────────────────────────────────────────────────
# Each entry maps a stable trail id (matching TRAILS[].id in index.html)
# to its OSM identifier(s).
#
#   - 'relation': a single OSM relation id (the route relation).
#                 Used when OSM tags this as a route/hiking relation.
#   - 'ways':     a list of OSM way ids. Used when the trail is only
#                 represented as ways (no parent relation).
#
# Refresh by running an Overpass search for the trail name. See
# README in this file's docstring for the search pattern.

TRAILS = [
    {
        "id": "independence-trail",
        "relation": 7018072,
    },
    {
        "id": "south-yuba-trail",
        "relation": 3439511,
    },
    {
        "id": "pioneer-trail",
        "relation": 11797251,
    },
    {
        "id": "tribute-trail",
        # Deer Creek Tribute Trail — main loop ways
        "ways": [245388331, 245388332, 245389977, 245389978, 541815065,
                 533380947, 1491698056],
    },
    {
        "id": "buttermilk-bend",
        "ways": [53331211, 53331212, 1432190604, 1432190605],
    },
    {
        "id": "hirschmans-trail",
        "ways": [455805338, 1486729834, 1486729835, 1486729836, 1486729837],
    },
    {
        "id": "cascade-canal-trail",
        "ways": [758449051, 760851580, 760851582, 760851584, 760851585,
                 760851586],
    },
]


# ── Overpass API ─────────────────────────────────────────────────────────────
_OVERPASS = "https://overpass-api.de/api/interpreter"
_HEADERS  = {
    "User-Agent": "NevadaCountyExp/1.0 trail-ingest (https://gonevadacounty.com)",
    "Accept":     "application/json",
}


def _overpass(query: str) -> dict:
    """POST a query to Overpass and return parsed JSON."""
    r = requests.post(_OVERPASS, data={"data": query}, headers=_HEADERS, timeout=180)
    r.raise_for_status()
    return r.json()


def _fetch_relation(rel_id: int) -> dict:
    """Fetch a relation with full member geometry inline."""
    q = f"[out:json][timeout:60];rel({rel_id});(._;>;);out body;"
    return _overpass(q)


def _fetch_ways(way_ids: list[int]) -> dict:
    """Fetch a list of ways with their node geometry inline."""
    refs = ",".join(str(w) for w in way_ids)
    q = f"[out:json][timeout:60];(way(id:{refs});>;);out body;"
    return _overpass(q)


# ── OSM → GeoJSON conversion ─────────────────────────────────────────────────
def _build_node_index(elements: list) -> dict[int, tuple[float, float]]:
    """Map OSM node id → (lon, lat) for quick lookup when stitching ways."""
    return {
        n["id"]: (n["lon"], n["lat"])
        for n in elements
        if n.get("type") == "node"
    }


def _way_coords(way: dict, nodes: dict) -> list[list[float]]:
    """OSM way → ordered list of [lon, lat] pairs."""
    return [list(nodes[nid]) for nid in way.get("nodes", []) if nid in nodes]


def _collect_way_lines(elements: list) -> list[list[list[float]]]:
    """All ways in `elements`, each as a coord list."""
    nodes = _build_node_index(elements)
    ways  = [e for e in elements if e.get("type") == "way"]
    lines = []
    for w in ways:
        coords = _way_coords(w, nodes)
        if len(coords) >= 2:
            lines.append(coords)
    return lines


def _haversine_miles(a: tuple, b: tuple) -> float:
    """Great-circle distance between two (lon, lat) points, in miles."""
    from math import asin, cos, radians, sin, sqrt
    lon1, lat1 = a
    lon2, lat2 = b
    R = 3958.7613   # earth radius in miles
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    h  = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(h))


def _line_length_miles(line: list[list[float]]) -> float:
    return sum(
        _haversine_miles(tuple(a), tuple(b))
        for a, b in zip(line, line[1:])
    )


# ── Build one trail's GeoJSON feature ────────────────────────────────────────
def build_feature(trail: dict) -> dict | None:
    """Fetch + convert one curated trail. Returns a GeoJSON Feature or None."""
    tid = trail["id"]
    print(f"  [{tid}] fetching OSM…", flush=True)

    try:
        if "relation" in trail:
            d = _fetch_relation(trail["relation"])
        else:
            d = _fetch_ways(trail["ways"])
    except Exception as e:
        print(f"  [{tid}] ERROR: {e}")
        return None

    lines = _collect_way_lines(d.get("elements", []))
    if not lines:
        print(f"  [{tid}] WARN: no usable geometry")
        return None

    total_miles = sum(_line_length_miles(l) for l in lines)

    if len(lines) == 1:
        geom = {"type": "LineString", "coordinates": lines[0]}
        trailhead = lines[0][0]
    else:
        geom = {"type": "MultiLineString", "coordinates": lines}
        # Use the start of the longest segment as a rough trailhead.
        longest = max(lines, key=_line_length_miles)
        trailhead = longest[0]

    feat = {
        "type": "Feature",
        "id": tid,
        "geometry": geom,
        "properties": {
            "id": tid,
            "length_miles": round(total_miles, 2),
            "trailhead": {"lon": trailhead[0], "lat": trailhead[1]},
            "source": "OpenStreetMap (ODbL)",
        },
    }
    print(f"  [{tid}] {len(lines)} segment(s), {total_miles:.2f} mi total")
    return feat


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    root  = Path(__file__).resolve().parent.parent
    out   = root / "data" / "trails.geojson"
    out.parent.mkdir(exist_ok=True)

    features = []
    for i, trail in enumerate(TRAILS):
        feat = build_feature(trail)
        if feat:
            features.append(feat)
        # Courtesy delay — Overpass is a free shared resource.
        if i < len(TRAILS) - 1:
            time.sleep(0.6)

    fc = {
        "type": "FeatureCollection",
        "generator": "tools/ingest_trails.py",
        "license": "ODbL · OpenStreetMap contributors",
        "features": features,
    }
    out.write_text(json.dumps(fc, indent=2), encoding="utf-8")
    print(f"\nwrote {out}  ({out.stat().st_size:,} bytes, {len(features)} trails)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

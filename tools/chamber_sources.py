"""
chamber_sources.py — mine chamber member directories for event SOURCES
=======================================================================
A chamber of commerce isn't a useful events feed (its events page is thin
and hand-typed — see docs/scraper_buildout.md). What it IS is a directory
of every local business and organization — i.e. a list of candidate event
*sources*. This harvests both chambers' member directories for
name + website, then (optionally) runs each website through the platform
probe. The filter is elegant: a towing company's site has no events page;
a brewery's runs Tribe Events. The probe finds the difference.

Pipeline:
    chamber directory  ->  {name, website}  ->  platform_probe  ->  candidates

Directories (worked out 2026-06):
    Nevada City  GrowthZone/MicroNet at business.nevadacitychamber.com.
                 URL pagination is client-side, but FindStartsWith?term=<L>
                 returns one server-rendered page per letter — iterate A-Z
                 (+ '0') for full coverage. Member website is the card's
                 first external <a class=card-link>.
    Grass Valley WordPress 'gvclisting' custom post type. Not REST-exposed,
                 but ?post_type=gvclisting&feed=rss2&paged=N gives a normal
                 paginated RSS feed of listing titles + permalinks. The
                 member's own website lives on the listing detail page.

Usage:
    python tools/chamber_sources.py --harvest        # names + sites, fast
    python tools/chamber_sources.py --probe          # + platform per site (slow)
    python tools/chamber_sources.py --probe --limit 40
"""
from __future__ import annotations
import argparse
import re
import sys
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, "tools")
import platform_probe as pp  # reuse probe + the _COVERED / _NOT_EVENT_ORGS sets

_H = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0.0.0 Safari/537.36")}
_TIMEOUT = 20

_SOCIAL = ("facebook", "instagram", "twitter", "linkedin", "youtube",
           "yelp", "google.", "growthzone", "cdnjs", "fonts.", "tripadvisor",
           "nextdoor", "pinterest", "tiktok")

# Member-site platforms that imply NO scrapable events even if reachable —
# these are the probe's "hosted" / non-event outcomes; harvested for the
# record but not flagged as build candidates.
_NON_EVENT_PLATFORMS = {"static", "unreachable", "none", "wordpress"}


def _host(u: str) -> str:
    try:
        return urlparse(u if "//" in u else "https://" + u).netloc.replace("www.", "").lower()
    except Exception:
        return ""


def _external(href: str, chamber_host: str) -> bool:
    h = (href or "").lower()
    return (h.startswith("http") and chamber_host not in h
            and not any(s in h for s in _SOCIAL)
            and "weatherwidget" not in h and "forecast7" not in h)


# ── Nevada City (GrowthZone) ──────────────────────────────────────────────────

def harvest_nevada_city() -> list[dict]:
    base = "https://business.nevadacitychamber.com/member-directory/FindStartsWith?term="
    out: dict[str, dict] = {}
    letters = list("0ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for L in letters:
        try:
            r = requests.get(base + L, headers=_H, timeout=_TIMEOUT)
        except Exception as e:
            print(f"  [NC {L}] error: {e}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("[class*=card]"):
            name_el = card.select_one("[class*=card-title], [class*=title], h3, h4, h5")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name or len(name) > 90:
                continue
            web = ""
            for a in card.find_all("a", href=True):
                if _external(a["href"], "nevadacitychamber"):
                    web = a["href"]
                    break
            out.setdefault(name, {"name": name, "website": web,
                                  "host": _host(web), "chamber": "Nevada City"})
        time.sleep(0.25)
    return list(out.values())


# ── Grass Valley (WordPress gvclisting RSS) ───────────────────────────────────

def harvest_grass_valley(with_sites: bool = True) -> list[dict]:
    feed = "https://www.grassvalleychamber.com/?post_type=gvclisting&feed=rss2&paged="
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, 25):
        try:
            r = requests.get(feed + str(page), headers=_H, timeout=_TIMEOUT)
        except Exception as e:
            print(f"  [GV p{page}] error: {e}")
            break
        soup = BeautifulSoup(r.text, "xml")
        items = soup.find_all("item")
        if not items:
            break
        for it in items:
            title = (it.find("title").get_text(strip=True) if it.find("title") else "")
            link = (it.find("link").get_text(strip=True) if it.find("link") else "")
            if not title or title in seen:
                continue
            seen.add(title)
            out.append({"name": title, "website": "", "host": "",
                        "chamber": "Grass Valley", "listing": link})
        time.sleep(0.25)

    # The member's own website lives on each listing detail page. Fetch them
    # (lightly) to fill in `website` — that's what the probe needs.
    if with_sites:
        for rec in out:
            try:
                r = requests.get(rec["listing"], headers=_H, timeout=_TIMEOUT)
                s = BeautifulSoup(r.text, "html.parser")
                for a in s.select("a[href]"):
                    if _external(a["href"], "grassvalleychamber"):
                        rec["website"] = a["href"]
                        rec["host"] = _host(a["href"])
                        break
            except Exception:
                pass
            time.sleep(0.15)
    return out


# ── Filtering + probing ───────────────────────────────────────────────────────

def _already_known(rec: dict) -> bool:
    nl = rec["name"].lower()
    return (any(c in nl for c in pp._COVERED)
            or any(n in nl for n in pp._NOT_EVENT_ORGS))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--harvest", action="store_true", help="list members + websites")
    ap.add_argument("--probe", action="store_true", help="also detect each site's platform")
    ap.add_argument("--limit", type=int, default=0, help="cap probes (0 = all)")
    args = ap.parse_args()
    if not (args.harvest or args.probe):
        print(__doc__)
        return 1

    print("Harvesting Nevada City (GrowthZone, A-Z)…", flush=True)
    nc = harvest_nevada_city()
    print(f"  {len(nc)} members ({sum(1 for r in nc if r['website'])} with websites)")
    print("Harvesting Grass Valley (gvclisting RSS + detail pages)…", flush=True)
    gv = harvest_grass_valley(with_sites=args.probe)
    print(f"  {len(gv)} members ({sum(1 for r in gv if r['website'])} with websites)")

    members = nc + gv
    with_site = [r for r in members if r["host"] and not _already_known(r)]
    print(f"\n{len(members)} total members; {len(with_site)} with a website and not already covered.")

    if not args.probe:
        print("\n(harvest only — run with --probe to detect event platforms)")
        for r in sorted(with_site, key=lambda x: x["name"].lower()):
            print(f"  {r['chamber'][:2]}  {r['name'][:44]:<46} {r['host']}")
        return 0

    # Probe each unique host once.
    by_host: dict[str, dict] = {}
    for r in with_site:
        by_host.setdefault(r["host"], r)
    targets = list(by_host.values())
    if args.limit:
        targets = targets[:args.limit]

    print(f"\nProbing {len(targets)} unique sites for event platforms…\n", flush=True)
    candidates = []
    for i, r in enumerate(targets, 1):
        verdict = pp.probe(r["website"])
        plat = verdict["platform"]
        is_candidate = (plat not in _NON_EVENT_PLATFORMS
                        and not plat.startswith("hosted:"))
        tag = "★ EVENT SOURCE" if is_candidate else "  ·"
        print(f"  {i:>3}/{len(targets)} {tag:<15} {plat:<16} {r['name'][:38]:<40} {r['host']}")
        if is_candidate:
            r["platform"] = plat
            r["next_step"] = verdict["next_step"]
            candidates.append(r)
        time.sleep(0.3)

    print(f"\n{'='*64}\n{len(candidates)} candidate event sources found "
          f"(member sites running a real event platform):\n")
    for r in sorted(candidates, key=lambda x: x["platform"]):
        print(f"  [{r['platform']:<15}] {r['name'][:40]:<42} {r['host']}")
        print(f"      → {r['next_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

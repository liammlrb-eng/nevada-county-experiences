"""
Nevada County Experience — Automatic Event Tagger
==================================================
Maps event title + description + category keywords to database tag names.

Usage:
    from auto_tagger import tag_event

    event = {...}               # dict from make_event()
    event["tags"] = tag_event(event)

Tags correspond to your database taxonomy.  Add new keywords freely —
the matching is case-insensitive substring search against the combined
"title + description + category" text.
"""

from __future__ import annotations
import json
import os
import re

# ── Tag rules ─────────────────────────────────────────────────────────────────
#
# Each entry:  ("Tag Name", [keyword, ...])
#
# Keywords are matched as case-insensitive substrings against the combined
# title + description + category string.  A keyword can be a plain word or
# a short phrase.  To require a whole-word match, prefix with "\b" and the
# entry will be treated as a regex pattern.
#
_TAG_RULES: list[tuple[str, list[str]]] = [

    # ── Performing Arts ───────────────────────────────────────────────────────
    # Short keywords get \b word boundaries to avoid substring false-positives.
    # ("opera" without \b matched "operate"/"operational" and tagged every
    # Curious Forge "Learn to Use a Wood Lathe" / sewing-machine class as Music;
    # "band" matched "abandoned"/"bandwidth"; "folk" matched "folks"; etc.)
    ("Music",           [r"\bconcert\b", "live music", r"\bband\b", "orchestra", "symphony",
                         "bluegrass", "jazz", r"\bfolk\b", r"\bblues\b", "country music",
                         "recital", "choir", "choral", r"\bopera\b", "acoustic",
                         "singer-songwriter", "singer songwriter", "open mic",
                         "music festival", "caroling", "karaoke",
                         "drum circle", "jam session",
                         # Performance signals
                         "performs at", "performing at", "live at",
                         "tribute to", "tribute show", "album release",
                         "record release", "album live",
                         # Group format hints (X Trio at Y, X Duo in Y, X Quartet)
                         "trio at", "trio in", "duo at", "duo in",
                         "quartet", "quintet", "ensemble at",
                         # Devotional / world music
                         "kirtan", "mariachi", "tribute album",
                         # Major Western NC music venues (artist@venue is music)
                         "at the center for the arts", "at the miners foundry",
                         "at the nevada theatre", "at bunce", "at barmhaus",
                         "at alibi", "at 5 mile house", "at the stone house",
                         # NevadaCity.Rocks venue coverage — "Artist at Venue"
                         # is the dominant title pattern there, and every
                         # listing on that site is by definition live music.
                         "at friar tucks", "at friar tuck", "at the national",
                         "at national hotel", "at crazy horse",
                         "at grass valley brewery", "at five-mile house",
                         "at five mile house", "at uncle sonnys",
                         "at uncle sonny", "at seven stars",
                         "at smoked owl", "at gold vibe", "at the smoked owl",
                         "at golden era", "at nevada city winery",
                         "at miners harmony", "at odd fellows",
                         "at the holbrooke", "at lola",
                         # Music industry signals
                         "rhythm kings", "song contest", "records presents"]),

    ("Theater",         ["theater", "theatre", "play", "musical", "improv",
                         "comedy show", "stand-up", "standup", "cabaret",
                         "one-woman show", "one-man show", "monologue",
                         "drama", "shakespeare", "performance"]),

    ("Film",            ["film", "movie", "cinema", "screening", "documentary",
                         "short film", "film festival", "drive-in"]),

    ("Dance",           ["dance", "ballet", "salsa", "swing dance", "ballroom",
                         "contra dance", "flamenco", "tap dance", "line dance"]),

    # ── Visual & Creative Arts ────────────────────────────────────────────────
    ("Art",             ["art exhibit", "gallery", "art show", "opening reception",
                         "art walk", "art fair", "sculpture", "photography exhibit",
                         "mural", "ceramics", "pottery", "printmaking",
                         "watercolor", "oil painting", "mixed media",
                         "artist talk", "art auction"]),

    ("Craft",           ["craft fair", "craft show", "makers market", "artisan",
                         "handmade", "quilting", "weaving", "knitting",
                         "woodworking", "jewelry making", "fiber arts"]),

    # ── Community & Social ────────────────────────────────────────────────────
    ("Community",       ["community meeting", "town hall", "city council",
                         "neighborhood", "volunteer", "fundraiser", "benefit",
                         "charity", "nonprofit", "local government",
                         "planning commission", "public hearing", "voter"]),

    ("Social",          ["mixer", "networking", "social hour", "happy hour",
                         "meetup", "meet-up", "gathering", "potluck",
                         "block party", "street fair", "reunion",
                         "trivia", "chess night", "chess club",
                         "death cafe", "tea party", "tea social",
                         "community-centered", "community picnic",
                         "first friday", "art walk", "sidewalk sale"]),

    ("Market",          ["farmers market", "flea market", "swap meet",
                         "pop-up market", "holiday market", "craft market",
                         "night market", "market day", "plant and market",
                         "marketplace"]),

    # ── Garden & Plants ──────────────────────────────────────────────────────
    ("Garden",          ["plant sale", "garden tour", "garden workshop",
                         "garden club", "master gardener", "herbal medicine",
                         "remedy garden", "butterfly garden", "wildflower walk",
                         "wildflower", "botanical", "garden of remembrance",
                         "calscape", "horticulture"]),

    # ── Family & Kids ─────────────────────────────────────────────────────────
    ("Family",          ["family", "kids", "children", "child-friendly",
                         "all ages", "family friendly", "youth", "toddler",
                         "parent", "school age", "storytime", "story time",
                         "halloween", "fourth of july", "july 4",
                         "adoption day", "pet adoption", "kitty adoption",
                         "doggy adoption"]),

    # ── Education & Workshops ─────────────────────────────────────────────────
    ("Workshop",        ["workshop", "class", "seminar", "webinar", "tutorial",
                         "training", "course", "lesson", "clinic",
                         "certification", "bootcamp", "boot camp"]),

    ("Lecture",         ["lecture", "talk", "speaker", "presentation",
                         "panel discussion", "symposium", "keynote",
                         "author reading", "book club", "book signing"]),

    # ── Nature & Outdoors ─────────────────────────────────────────────────────
    ("Nature",          ["hike", "hiking", "nature walk", "trail", "birding",
                         "bird walk", "wildflower", "wildlife", "conservation",
                         "stewardship", "river restoration", "watershed",
                         "forest", "botanical", "garden tour",
                         "star gazing", "stargazing", "astronomy",
                         "syrcl", "nevada irrigation"]),

    ("Outdoor",         ["outdoor", "camping", "kayak", "paddleboard", "rafting",
                         "cycling", "bike ride", "mountain biking",
                         "rock climbing", "fishing", "hunting", "skiing",
                         "snowshoeing", "snowshoe"]),

    # ── Sports & Fitness ─────────────────────────────────────────────────────
    ("Sport",           ["game", "tournament", "race", "marathon", "run", "5k",
                         "triathlon", "lacrosse", "softball", "baseball",
                         "volleyball", "basketball", "soccer", "football",
                         "tennis", "swim meet", "rodeo", "sport"]),

    ("Wellness",        ["yoga", "meditation", "mindfulness", "wellness",
                         "fitness class", "pilates", "tai chi", "qi gong",
                         "sound bath", "breathwork", "retreat",
                         "mental health", "self-care",
                         "mindful movement", "music-assisted",
                         "compassionate care"]),

    # ── Spiritual & Contemplative ─────────────────────────────────────────────
    ("Spiritual",       ["spiritual", "prayer", "church",
                         "interfaith", "sacred", "blessing",
                         "dharma", "buddhist", "zen", "quaker",
                         "celebration of life", "vigil", "sanctuary",
                         "congregation", "worship", "sermon",
                         "ananda", "expanding light"]),

    # ── History & Heritage ────────────────────────────────────────────────────
    ("Historic",        ["historic", "history", "heritage", "gold rush",
                         "victorian", "pioneer", "museum", "historical society",
                         "cemetery tour", "walking tour", "preservation",
                         "civil war", "native american", "indigenous",
                         "nisenan", "maidu"]),

    # ── Food & Drink ─────────────────────────────────────────────────────────
    ("Food & Drink",    ["wine tasting", "beer festival", "food festival",
                         "tasting room", "dinner", "gala dinner", "brunch",
                         "cooking class", "farm dinner", "harvest dinner",
                         "chocolate", "cheese", "food tour", "culinary",
                         "brewery", "winery", "distillery tour"]),

    # ── Holiday & Seasonal ────────────────────────────────────────────────────
    ("Holiday",         ["christmas", "hanukkah", "kwanzaa", "thanksgiving",
                         "halloween", "easter", "fourth of july", "july 4",
                         "independence day", "memorial day", "labor day",
                         "veterans day", "mothers day", "fathers day",
                         "new year", "valentine", "holiday celebration",
                         "seasonal", "solstice", "equinox"]),

    # ── Parade & Festival ─────────────────────────────────────────────────────
    ("Festival",        ["festival", "faire", "fair", "parade", "carnival",
                         "celebration", "jubilee", "gala", "expo",
                         "renaissance faire", "harvest festival"]),

    # ── Environment & Sustainability ─────────────────────────────────────────
    ("Environment",     ["sustainability", "environment", "climate", "green",
                         "recycling", "composting", "solar", "regenerative",
                         "earth day", "clean up", "cleanup", "restoration",
                         "pollinator", "habitat"]),

    # ── Hands-on & Interactive ────────────────────────────────────────────────
    ("Hands-on",        ["hands-on", "hands on", "interactive", "make your own",
                         "diy", "do it yourself", "create", "craft night",
                         "maker", "build", "experiment", "tinker"]),

    # ── Fundraiser ────────────────────────────────────────────────────────────
    ("Fundraiser",      ["fundraiser", "fundraising", "benefit concert",
                         "auction", "raffle", "gala", "pledge", "donate",
                         "annual fund"]),
]

# Pre-compile patterns for performance
_COMPILED: list[tuple[str, list[re.Pattern]]] = []
for _tag_name, _keywords in _TAG_RULES:
    patterns = []
    for kw in _keywords:
        flag = re.IGNORECASE
        if kw.startswith(r"\b"):
            patterns.append(re.compile(kw, flag))
        else:
            patterns.append(re.compile(re.escape(kw), flag))
    _COMPILED.append((_tag_name, patterns))


# ── Per-source override rules ───────────────────────────────────────
# Loaded once at import time from scraper_overrides.json. Each rule is an
# admin-authored exception that fires AFTER the regex tagging pass and
# can add or remove tags. Rationale + schema docs live in the JSON file
# itself.
#
# Example use cases:
#   - "Every event from NevadaCity.Rocks at venue 'Friar Tucks' should
#      always carry the Music tag, even if the title looks like a one-off."
#   - "Events scraped from the Curious Forge whose title contains 'movie
#      night' should NOT be tagged Workshop."
#
# This is the events-side equivalent of the per-venue pill_in override
# system in index.html — surgical exceptions without forcing a regex
# change that might affect other events.

_OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "scraper_overrides.json")

def _load_overrides() -> list[dict]:
    try:
        with open(_OVERRIDES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        rules = data.get("rules", []) or []
        # Pre-compile any regex fields for speed.
        for r in rules:
            if r.get("if_source_regex"):
                r["_re_source"] = re.compile(r["if_source_regex"], re.I)
            if r.get("if_title_regex"):
                r["_re_title"]  = re.compile(r["if_title_regex"], re.I)
        return rules
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"  [auto_tagger] WARNING: scraper_overrides.json failed to load: {e}")
        return []

_OVERRIDE_RULES = _load_overrides()


def _rule_matches(rule: dict, event: dict) -> bool:
    """All `if_*` conditions on a rule must match for it to apply."""
    src = (event.get("source") or "")
    title = (event.get("title") or event.get("name") or "")
    loc = (event.get("location") or "").lower()
    url = (event.get("url") or "").lower()

    if "_re_source" in rule:
        if not rule["_re_source"].search(src): return False
    elif rule.get("if_source"):
        if rule["if_source"] != src: return False

    if "_re_title" in rule:
        if not rule["_re_title"].search(title): return False

    if rule.get("if_venue_contains"):
        if rule["if_venue_contains"].lower() not in loc: return False

    if rule.get("if_url_contains"):
        if rule["if_url_contains"].lower() not in url: return False

    return True


def _apply_overrides(event: dict, tags: list[str]) -> list[str]:
    """Run every matching override rule and apply its tag mods. Returns
    the modified tag list. Operations are order-independent; adds always
    precede removes within a single rule so an explicit remove wins if
    both happen to mention the same tag."""
    if not _OVERRIDE_RULES:
        return tags
    out = list(tags)
    for rule in _OVERRIDE_RULES:
        if not _rule_matches(rule, event):
            continue
        for t in (rule.get("force_add_tags") or []):
            if t not in out:
                out.append(t)
        for t in (rule.get("force_remove_tags") or []):
            if t in out:
                out.remove(t)
    return out


def tag_event(event: dict) -> list[str]:
    """
    Return a list of tag names that apply to the event.
    Looks at title + description + category, then applies any
    admin-authored overrides from scraper_overrides.json.
    """
    text = " ".join([
        event.get("title", ""),
        event.get("description", ""),
        event.get("category", ""),
        event.get("location", ""),
    ])

    matched: list[str] = []
    for tag_name, patterns in _COMPILED:
        for pat in patterns:
            if pat.search(text):
                matched.append(tag_name)
                break   # only add tag once

    return _apply_overrides(event, matched)


def tag_events(events: list[dict]) -> list[dict]:
    """In-place tag a list of events. Returns the same list."""
    for ev in events:
        ev["tags"] = tag_event(ev)
    return events

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
    ("Music",           ["concert", "live music", "band", "orchestra", "symphony",
                         "bluegrass", "jazz", "folk", "blues", "country music",
                         "recital", "choir", "choral", "opera", "acoustic",
                         "singer-songwriter", "singer songwriter", "open mic",
                         "music festival", "caroling", "karaoke",
                         "drum circle", "jam session"]),

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
                         "block party", "street fair", "reunion"]),

    ("Market",          ["farmers market", "flea market", "swap meet",
                         "pop-up market", "holiday market", "craft market",
                         "night market", "market day"]),

    # ── Family & Kids ─────────────────────────────────────────────────────────
    ("Family",          ["family", "kids", "children", "child-friendly",
                         "all ages", "family friendly", "youth", "toddler",
                         "parent", "school age", "storytime", "story time"]),

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
                         "mental health", "self-care"]),

    # ── Spiritual & Contemplative ─────────────────────────────────────────────
    ("Spiritual",       ["spiritual", "prayer", "church",
                         "interfaith", "sacred", "blessing",
                         "dharma", "buddhist", "zen", "quaker",
                         "celebration of life", "vigil", "sanctuary",
                         "congregation", "worship", "sermon"]),

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


def tag_event(event: dict) -> list[str]:
    """
    Return a list of tag names that apply to the event.
    Looks at title + description + category.
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

    return matched


def tag_events(events: list[dict]) -> list[dict]:
    """In-place tag a list of events. Returns the same list."""
    for ev in events:
        ev["tags"] = tag_event(ev)
    return events

# Direct-scraper build-out queue

**Why this exists:** consolidators (KVMR, the chambers, Eventbrite) may
go away — *especially if this site succeeds* and organizers stop
submitting to them. Their APIs are also not contracts. So consolidators
are bridges, not foundations: we use them for breadth today and steadily
build direct scrapers for the sources underneath. The cross-source
URL+date dedup in `event_scraper.py` makes this side-effect-free — a
direct scraper for a KVMR-covered venue produces zero duplicates, the
direct copy simply wins.

**Where this list comes from:** KVMR's REST data names the organizer and
original website for every event it republishes. That census, plus
platform detection, regenerates with:

```powershell
python tools/platform_probe.py --census          # ranked census + platforms
python tools/platform_probe.py <url> [...]       # probe any single site
```

Census snapshot 2026-06-12 (430 in-region KVMR events). The "platform"
column is the probe's *hypothesis*; the "verified" column is what a
follow-up check actually found — and the gap between them is the real
lesson (see below).

| # | Organizer | Events | Probe says | Verified reality |
|---|---|---|---|---|
| 1 | Mountain Stream Meditation | 90 | Squarespace | recurring sittings → Experience, not events |
| 2 | Inner Path | 28 | WooCommerce | recurring classes → Experience |
| 3 | Fly HiFi Stereo | 26 | static | http-only, no inline feed; JS/subpage — custom |
| 4 | Nevada City Odd Fellows | 12 | WordPress | "events" are **blog posts** about gallery shows; no event feed — KVMR adds the dates |
| 5 | Sammie's Friends | 12 | Wix | ❌ **not an event org** — animal rescue; business self-promo |
| 6 | Soulspace Collective | 9 | hosted: Momence | keep via KVMR |
| 7 | Nevada County Democrats | 7 | hosted: Mobilize | keep via KVMR |
| 8 | Off Broadstreet Theatre | 6 | static | **403s** direct requests (like Miners Foundry) — Selenium |
| 9 | Gold Country Ultimate | 6 | none | KVMR-only |
| 10 | California Solar Electric Co-op | 6 | Squarespace | ❌ **not an event org** — solar co-op; business self-promo |
| 11 | NorCal Resist | 6 | Google Calendar ICS | promising — gold_vibe.py pattern |
| 12 | Lyric Rose Theatre Company | 5 | static | external ticketing widget (`olspage=cart`) — parse the widget |

**Not event organizers (don't build, and arguably filter from KVMR):**
Sammie's Friends (animal rescue) and California Solar Electric Co-op
(solar business) appear in KVMR's calendar as self-promotion — adoption
days, info sessions, sales — not visit-driving events. They're a third
category beyond "build a scraper" / "keep via KVMR": *noise we may want
KVMR to stop importing.* See "Open question" below.

## What verification revealed (the actual strategic finding)

**There is no pile of 20-minute wins in this batch.** The two
mechanical truths, both useful:

- The *easy-platform* sources (Squarespace, WooCommerce) are
  **recurring-class content** — Mountain Stream's 90 daily sittings,
  Inner Path's 28 classes. Per the editorial direction these belong as
  recurring **EXPERIENCES** (one entry + a schedule + a story), not
  hundreds of scraped near-duplicate events. KVMR covers them fine
  meanwhile.
- The *editorially-core* venues (the theatres, the music room) live on
  **bot-protected, http-only, or external-ticketing** sites — real
  custom work each, not a platform drop-in. The probe correctly flagged
  these as "static/custom"; verification just priced them.

So the build-out is a deliberate, medium-effort campaign, not a quick
sweep — and KVMR's coverage is genuinely "good enough" for most of
these until each is individually worth the work. That's the opposite of
discouraging: it means the consolidator bridge is load-bearing for now
and we replace planks intentionally, highest editorial value first.

## The next few (verified, re-ranked)

1. **NorCal Resist** — the one clean technical win left: a public
   Google Calendar, so the `gold_vibe.py` ICS pattern applies directly
   (~20 min). Modest editorial weight, but proves the pipeline and
   removes a real source from KVMR-dependence.
2. **Off Broadstreet Theatre** — canonical Nevada City dessert theatre;
   high editorial value. 403s direct requests, so it needs the Selenium
   path (the Edge driver already works) — a real but known job.
3. **Fly HiFi Stereo** — highest-volume core venue (26, Grass Valley
   music). Needs a look at where the listings actually render
   (http-only base, likely a JS subpage) before estimating.
4. **Lyric Rose Theatre Company** — second theatre; events live in an
   embedded ticketing widget — identify the widget vendor, parse its
   feed.
5. *(was Sammie's Friends / Cal Solar — removed; they're businesses, not
   event organizers.)*

Re-run `python tools/platform_probe.py --census` after any scrape to
refresh volumes and catch new organizers entering the calendar.

## Open question: filtering business self-promo out of KVMR

Sammie's Friends and Cal Solar showing up at all means KVMR's calendar
carries business self-promotion (adoption days, solar info sessions,
retail sales) that isn't visit-driving and probably shouldn't be on the
public grid. The census makes these easy to spot by organizer. Options
when we decide to act:

- **Organizer blocklist** in `kvmr.py` — cheapest; a small set of
  organizer names whose events are skipped. Brittle as the list grows.
- **AI categorizer signal** — let the existing AI pass flag
  "business-promo / not-a-public-event" so it works across *all*
  sources, not just KVMR. More robust, fits the editorial-quality
  direction, but more work.

Deferred until we see how much of the queue this actually is. Flagging
here so the pattern isn't forgotten.

## Experience candidates, not event scrapers

Mountain Stream Meditation (90) and Inner Path (28) dominate by volume,
but their "events" are recurring sittings/classes — per the editorial
direction those belong as recurring **EXPERIENCES** (one entry, a
schedule, a story) rather than hundreds of near-identical scraped
events. KVMR coverage suffices until those entries are written.

## Chambers as a SOURCE-DISCOVERY tool (2026-06-12)

The better use of a chamber isn't its events page — it's its **member
directory**, a list of every local business and organization, i.e.
candidate event *sources*. `tools/chamber_sources.py` harvests both:

- Nevada City (GrowthZone) — `FindStartsWith?term=<A-Z>`, 331 members
- Grass Valley (`gvclisting` RSS) — 239 members

…then probes each member's website and keeps those running a real event
platform. ~570 members, 443 unique sites probed.

**Honest caveat:** the probe flags platform *presence*, not an actual
events calendar. A Shopify jerky shop and a WooCommerce chocolate shoppe
run that software but host no events — so the raw "191 candidates" is
mostly false positives. WooCommerce/Shopify are stores; discount them
entirely. The real signal is event-PLUGIN platforms, and even those need
an "does it have upcoming events?" check.

After that check (query each plugin's feed for events in the next 120
days), the genuinely actionable shortlist is small and high-confidence:

| Source | Platform | Upcoming | Pattern | Notes |
|---|---|---|---|---|
| **California Bluegrass Association** | Tribe REST | 302 | tribe_events.py | on-brand; but CBA runs statewide — needs region filter |
| **North Columbia Schoolhouse Cultural Center** | Event Organiser iCal | 107 | bylt.py | real San Juan Ridge cultural venue — high value |
| **Congregation B'nai Harim** | Event Organiser iCal | 64 | bylt.py | |
| **Eastern Sierra Interpretive Association** | Tribe REST | 48 | tribe_events.py | nature/interpretive; check locality |
| **Gold Country Senior Services** | Event Organiser iCal | 15 | bylt.py | |

Everything else flagged had 0 upcoming events (plugin installed, dormant:
Inn Town Campground, Avanguardia Wines, Roamin' Angels, Alta Sierra Wine
Shop, Classic Cars West) or is a store. North Columbia Schoolhouse is the
standout — a genuine cultural venue we don't cover, on the easy bylt.py
iCal pattern. Re-run `tools/chamber_sources.py --probe` periodically to
catch members who add calendars later.

## Chamber audit (2026-06-12) — the other consolidators

Ran the KVMR-style audit on both chamber scrapers. Unlike KVMR, **neither
has a structured backend**: no event post type, no Tribe REST, no embedded
ChamberMaster/GrowthZone widget. Events are hand-typed into WordPress pages
(Nevada City = Essential Grid items; Grass Valley = bare Elementor
headings). So there is no API to upgrade to — the fragile HTML parsing is
the only option, and these are the most brittle sources we have.

What they actually contribute today:

- **Nevada City Chamber** — 11 events, but only 4 parse to real dates; the
  other 7 are raw strings ("April 2026", "2025 Concert Dates",
  "October – November"). Those 7 are the city's *signature recurring
  events*: Farmers Market, Sidewalk Sale, First Friday Art Walks, Hot
  Summer Nights, Victorian Christmas, Fall Colors, Fourth of July. Only 1
  duplicate (Film Festival, via NCAC). Editorially gold, but trapped in
  unparseable data and recurring by nature.
  → **Better home: curated EXPERIENCES** (annual canon, hand-authored with
  real dates), then retire the scraper. Matches the "essentials canon"
  editorial idea.

- **GV Chamber** — page now holds just 2 events, and neither has a title
  heading, so the scraper's fallback grabs junk ("Please join the Greater
  Grass Valley Chamber o…", "FREE COMMUNITY EVENT"). Not broken code — the
  page is nearly empty and unstructured. Near-zero value; chamber
  mixers/meetings aren't visit-driving anyway.
  → **Recommend disabling** until/unless the chamber rebuilds its events
  page on a real platform. Re-probe periodically with platform_probe.

Net: the chambers confirm the thesis harder than KVMR did. KVMR at least
had a clean API; the chambers are thin, structureless, and shedding
content to venue-direct + KVMR already. Their best contribution
(NC Chamber's signature events) belongs as hand-curated canon, not scraping.

## Keep via KVMR (no independent site to scrape)

Hosted platforms (Momence, Mobilize, Facebook-only organizers, WeTravel
retreats) and organizers with no website. If KVMR disappears before
these get homes, they drop — acceptable; none are editorially core.

## When a scraper lands

Move its row out of the census table, add the source to
`scraper/sources.json`, and register it in `ALL_SCRAPERS` **above** the
consolidators block (direct sources must run before KVMR for the dedup
to prefer them).

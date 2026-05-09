# Western Nevada County Experience — one-page summary

A working tourism-planning platform for Western Nevada County (Gold Country
foothills). Built, deployed, ready to demo.

## Geographic scope

**In scope:** Nevada City, Grass Valley, Penn Valley, North San Juan,
Rough & Ready, Washington, Chicago Park, Smartsville, Cedar Ridge, Alta
Sierra, Lake of the Pines, plus adjacent Colfax (Placer County, but
shares the Gold Country identity).

**Out of scope:** Truckee, Kings Beach, Tahoe City, Donner — the
Sierra-side communities are a fundamentally different market.

## What's in the system

| Category | Count |
|---|---|
| Curated experiences | 161 |
| Live-scraped events (in queue) | ~980 |
| Visitor personas served | 9 |
| Themed vibes (top-level filters) | 9 |
| Working scrapers | 8 |
| Disabled scrapers (Cloudflare / unreachable) | 2 |

## Data sources (8 working scrapers)

1. **Nevada City Chamber** — static HTML (Essential Grid plugin)
2. **Grass Valley Chamber** — static HTML (Elementor)
3. **KVMR Public Radio** — Tribe Events RSS feed
4. **The Union** — newspaper RSS (paywall-fallback)
5. **Eventbrite Nevada** — React-rendered cards (Selenium)
6. **Center for the Arts** — Elementor (~20 concerts at a time)
7. **Miners Foundry** — Selenium (site 403s direct HTTP)
8. **Nevada County Arts Council (NCAC)** — Trumba JSON feed, 540 events spanning 16 months

## Key features

- **Discovery:** themed vibes → vibe-level pills → category dropdown → activity tags → date filter → area filter
- **Day-by-day itinerary** with per-day "Tonight's Stay" lodging slot
- **Smart Suggestions** in the itinerary, tag + geography aware
- **Mixed events + experiences** in one itinerary
- **Native share** via phone share sheet, email, text, or copy URL
- **Print view** with long-form per-day layout
- **Admin layer:** scraper queue (approve/dismiss), AI categorize button (Claude Haiku), inline experience editor, tag taxonomy editor
- **Public RSS feed** at `/feed.rss` for partner republishing

## Privacy posture

- No analytics, no cookies, no third-party trackers (default state)
- Itinerary save is opt-in only — explicit consent banner on first add
- "Forget on this device" link wipes saved data anytime
- No accounts, no email collection, no sign-up
- Chamber sees zero personal information about visitors
- No GDPR / CCPA banners required (because nothing is collected)

## Tech stack

- **Frontend:** vanilla HTML + JavaScript (no framework, no build step)
- **Scrapers:** Python (requests + BeautifulSoup + Selenium where needed)
- **AI:** Claude Haiku via Anthropic API (~$0.50–$1.00 / month)
- **Hosting:** designed for $6/mo VPS (DigitalOcean droplet) or free GitHub Pages
- **Open source:** owned outright, no vendor lock-in

## Cost scenarios

| Tier | Monthly | What you get |
|---|---|---|
| Lean | $0–$50 | GitHub Pages + AI off, manual scrape run |
| Typical | $80–$150 | $6/mo VPS + weekly scrape + AI categorize |
| Premium | $300–$500 | Managed hosting + daily scrape + nightly AI |
| Commercial alternative | $5,000–$30,000 | CrowdRiff / Simpleview / similar |

## Status

- ✅ Built and working (production-ready)
- ✅ Live demo at https://liammlrb-eng.github.io/nevada-county-experiences/
- ✅ Open source, full repo at https://github.com/liammlrb-eng/nevada-county-experiences
- ⏳ Awaiting county / chamber decision on adoption

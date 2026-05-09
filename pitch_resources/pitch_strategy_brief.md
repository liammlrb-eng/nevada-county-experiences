# Context for a strategy conversation about a tourism-platform pitch deck

> Paste this as the first message in a fresh Claude.ai chat session.

## What I want from this chat

I'm presenting a working tourism platform to a group of Nevada County, CA tourism / county / chamber stakeholders. I have a 15-slide pitch deck already built. Before the meeting I want to:

1. **Stakeholder map** — who's likely in the room, what each person actually cares about, and what their unspoken concerns might be.
2. **Predictable objections per stakeholder type** — vendor lock-in, "who maintains it after you leave?", ADA / Spanish-language compliance, equitable representation of small/rural members, displacement of existing platforms (Simpleview, CrowdRiff, etc.).
3. **A 5-question discovery script** I can either send by email pre-meeting or use to open the meeting.
4. **Help deciding whether to reorder the deck** — e.g., should I lead with the strategic insight (lodging-revenue framing), with cost/sustainability, or with build-status?
5. *Optional, last 15 minutes:* role-play me through a hostile-questioner version of the meeting so I'm ready.

I don't have a confirmed attendee list yet — just titles. The county is small enough that the same 8–12 people show up to anything tourism-related.

## What I built

A purpose-built tourism-planning platform for Western Nevada County (Gold Country foothills — Nevada City, Grass Valley, Penn Valley, North San Juan, Rough & Ready). Combines:

- **161 curated experiences** across 11 communities (lodging, food, hands-on, outdoor, wellness, etc.)
- **~980 live-scraped events** from 8 sources (KVMR, Eventbrite, NC Chamber, GV Chamber, Center for the Arts, Miners Foundry, NCAC's Trumba feed, The Union)
- **Day-by-day itinerary builder** with per-day "Tonight's Stay" lodging slot, opt-in save, native share
- **Privacy-first**: no analytics, no cookies, no account required, opt-in localStorage save, "Forget on this device" link
- **Admin layer**: scraper queue, AI categorize button (Claude Haiku), inline experience editor, taxonomy editor

Tech: static HTML+JS frontend, Python/Selenium scrapers, deploys on a $6/mo VPS. Owned outright (open source). Single-developer maintenance for now (me). Live demo at https://liammlrb-eng.github.io/nevada-county-experiences/.

## Likely audience (my guess — please challenge)

For a Nevada County tourism conversation, the room is probably some mix of:

- Nevada City Chamber of Commerce ED
- Grass Valley Chamber ED
- Nevada County Economic Resource Council (runs gonevadacounty.com)
- Nevada County Arts Council (NCAC) rep
- A County Supervisor or econ-dev staff
- Possibly: County IT / GIS
- Possibly: Sierra Business Council
- Possibly: TOT-administering city official (Nevada City or GV)

## Current deck (15 slides, 16:9, .pptx)

1. Title
2. What this is — by-the-numbers
3. Who this serves — 9 visitor personas
4. How visitors discover — 7 paths (themed vibes, vibe sub-pills, category dropdown, activity tags, date filter, area filter, smart suggestions)
5. Day-by-day itinerary builder — 8 features + visual mock
6. UX design decisions — 8 decisions w/ "why it matters"
7. Privacy posture — 8 points
8. Behind the scenes — admin/operations features
9. AI tag refinement — what it fixes + cost (~$1/mo)
10. Cost — 4 scenarios ($0–$50, $80–$150, $300–$500, $5K–$30K commercial alternatives)
11. Migration to county server — 9 phases
12. **What the chamber needs to do next** — 3 columns (data partnerships, member outreach, ops)
13. Strategic insight — "optimize for lodging bookings, not site visits"
14. The 8-min demo flow
15. Thank you / leave-behind

Every feature on slides 4–9 and 13 has an inline "↳ scenario" italic sub-line under it (e.g. *"Spouse on phone moves Friday's hike to Saturday in two taps"*).

## Hard constraints

- The platform is built and working. This is **not** "should we build this?" — it's "should the county adopt / host / brand this?"
- Single-developer maintenance for now; no salaried tech staff at any chamber
- Western Nevada County only — Truckee / Tahoe explicitly out of scope
- Tone: confident but not salesy; this is an offer, not a sales pitch

## Where I'd like you to start

Give me your first cut at a stakeholder map: rows = roles in the audience, columns = *"what they care about most"* / *"predictable objection"* / *"the slide that will land for them"* / *"the slide that will fall flat."* Then we'll iterate. If you want to see actual slide content, I can paste any slide's text on request — or I have a markdown outline (`deck_outline.md`) I can share.

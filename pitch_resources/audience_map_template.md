# Audience map — fill in after Claude.ai chat returns its first cut

## Confirmed attendees

| Name | Title | Org | Role in the meeting |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

## Stakeholder priorities

For each attendee (or attendee TYPE if names aren't known yet), fill in:

### [Role / name]

- **What they care about most:**
- **Predictable objection:**
- **The slide that will land:**
- **The slide that will fall flat:**
- **A thing to mention by name:**

---

### [Role / name]

- **What they care about most:**
- **Predictable objection:**
- **The slide that will land:**
- **The slide that will fall flat:**
- **A thing to mention by name:**

---

## Pre-call discovery questions

Five questions from chat-Claude's strategy session. Best framing: have these
come from the ERC head (or whoever convened the meeting) so they feel like
a group exercise she's facilitating, not your sales setup.

1. **"When a visitor finds our area online right now, what's the first thing
   they hit — and does it help them plan a trip or just tell them we exist?"**
   *Opens the gap between current platforms and actual trip-planning utility.*

2. **"How many of our member businesses have events or experiences that aren't
   showing up on any shared calendar right now?"**
   *Surfaces the data-partnership problem without blaming anyone.*

3. **"If we could measure one thing about how visitors use a tourism platform,
   what would matter most — page views, itineraries built, or lodging nights
   booked?"**
   *Sets up your strategic insight (slide 2) without you having to say it yourself.*

4. **"What's the biggest thing that stalled the experience group this past
   year — was it technology, budget, consensus, or something else?"**
   *Gets the real blocker on the table. Your prototype may answer one but not all.*

5. **"If someone built a working prototype tomorrow, what would you need to
   see before you'd feel comfortable putting the county's name on it?"**
   *Directly surfaces adoption criteria — ADA, branding, data accuracy,
   maintenance — before you present.*

## Deck reorder decisions

The current order (already applied in `demo_pitch.pptx`) is:

1. Title
2. **Strategic insight** *(was slide 13 — now leads the deck)*
3. What this is
4. Discovery
5. Itinerary
6. **Let me show you (live demo cue)** *(was "8-minute demo flow")*
7. Personas
8. UX decisions
9. Privacy
10. Behind the scenes
11. AI tag refinement
12. Cost
13. **Where the group can take this** *(retitled from "What the chamber needs to do next")*
14. Thank you
15. **Appendix A1**: Migration *(moved to appendix — pull up only if IT is in the room or asked)*

Open decisions:

- [x] ~~Keep migration as slide 14 or move to backup-only~~ — moved to appendix (Slide A1)
- [x] ~~Add a Plausible Analytics fallback option to slide 9 (Privacy)~~ — shipped
- [x] ~~Adjust the Maker Traveler / Curious Forge callout on slide 7~~ — genericized brand mention + reordered Maker Traveler last in over-serve list
- [ ] Anything else after the discovery call?

## Talking points to memorize

- For [stakeholder]: "___________________"
- For [stakeholder]: "___________________"
- Universal opener: "___________________"
- Universal closer: "___________________"

## Hostile-question prep

| Likely question | Pre-baked answer |
|---|---|
| **"How do we measure whether this is working?"** *(TOT official)* | Privacy posture is genuine, but offer Plausible Analytics as middle ground (privacy-respecting, no cookies, GDPR-compliant, open source). Aggregate metrics — itineraries built, lodging-card click-throughs, share-link generations — without per-visitor tracking. |
| **"What happens when you (Liam) leave?"** | The platform is plain HTML/JS + Python; any developer who can run a Linux server can maintain it. Code is owned outright (open source), no vendor lock-in. The operator guide PDF documents day-to-day operations. AI-categorize has a hard $5/month cap. |
| **"How does this work with our existing platform [Simpleview / CrowdRiff / etc.]?"** | This is complementary — it solves the trip-planning workflow that brochure-style sites don't. We can RSS-feed events into other platforms, embed a planner widget, or run side-by-side. |
| **"Is this ADA-compliant? Spanish-language?"** | ADA: WCAG 2.1 AA passing on the demo. Spanish: not yet — auto-translate is straightforward to add (~1 day) but human-translated content is the right answer for production. |
| **"Who decides what gets listed?"** | Curated experiences are editable inline by chamber staff; events come from public scrapers + admin queue. Member-equity is operations work — who reviews the queue, who flags missing venues. The platform doesn't make those calls; the chamber does. |
|  |  |
|  |  |

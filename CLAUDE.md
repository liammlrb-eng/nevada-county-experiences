# Nevada County Experience Project — Claude Context

## What this is
A single-page HTML web app for discovering experiences in Nevada County, California (Gold Country).
Targeted at visitors and locals. Deployable as a static site (GitHub Pages).

**Live file:** `index.html` (2,439 lines, self-contained — no build step, no dependencies to install)
**Inventory spreadsheet:** `inventory.xlsx` (source data / planning reference)

---

## Design system
| Token | Value | Use |
|---|---|---|
| `--gold` | `#C9A84C` | Accents, borders, active states |
| `--gold-light` | `#E8C96A` | Lighter accent |
| `--brown` | `#6B4A2A` | Section headings |
| `--cream` | `#F5F0E8` | Page background |
| `--dark` | `#1E1508` | Hero bg, modal bg |
| `--forest` | `#3A5A3A` | Subtle green accents |
| `--rust` | `#8B4A2A` | Warm accent |
| `--slate` | `#4A5568` | Body text |
| `--fog` | `#EDE8DE` | Alternate bg |

Fonts: `Playfair Display` (headings, display — serif, italic) + `Josefin Sans` (UI, labels — sans, letter-spaced)

---

## Architecture (all inline in index.html)

### Data arrays (in `<script>` block, ~line 1163)
- **`THEMES[]`** — 16 experience themes, each with `id, name, tagline, tags[], photo`
  - Rustic, Historic, Artistic, Romantic, Music & Nightlife, Foodie, Active & Outdoors, Family, Spiritual & Wellness, Social, Opulent, Hands-On Creative, Scenic & Nature, Film & Culture, Gold Rush, Sport & Recreation
- **`EXPERIENCES[]`** — 50+ venues/activities, each with:
  `id, name, sub, area, type, tags[], hours, notes, icon, url, directions, lat, lng, photo, season`
  - Areas: Nevada City, Grass Valley, Near Nevada City, North San Juan, Nevada County
- **`ITINERARIES[]`** — Curated multi-stop day/overnight plans (e.g. "Romantic Getaway 2 Days")
- **`EVENTS[]`** — 19 upcoming events with dates, venues, tags, URLs

### UI sections / tabs
1. **Hero** — dark gradient background, gold pattern overlay, county title
2. **Theme selector** — card grid (16 themes); clicking filters the experience cards below
3. **Tabs** — Experiences | Itineraries | Events
   - Experiences tab: filtered card grid
   - Itineraries tab: curated day-trip plans with timed stops
   - Events tab: upcoming events grid with date/venue/tags
4. **FAB** ("My Itinerary") — floating button, shows count of saved items

### Modals
- **My Itinerary modal** — saved experiences list; has map button
- **Map modal** — Leaflet map with markers for saved itinerary items
- **Manage Data modal** — in-browser experience editor: sortable table, inline editing, tag-pill editor, add/delete rows. Changes saved to localStorage.
- **Tag Manager modal** — edit master tag list used across all experiences

### Key JS functions (approximate line numbers)
- `renderThemes()` — draws theme card grid
- `renderExperiences()` — filters and draws experience cards based on selected themes
- `toggleTheme(id)` — selects/deselects a theme filter
- `getActiveThemeTags()` — returns the union of tags for selected themes
- `openModal() / closeModal()` — My Itinerary modal
- `openMap() / closeMap()` — Leaflet map modal
- `openManageData() / closeManageData()` — experience editor modal
- `openTagManager() / closeTagManager()` — tag editor modal
- `renderManageTable()` — builds sortable editable table in Manage Data modal
- `handleOverlayClick()` — closes modals on backdrop click

---

## What was built across the 22 iterations
Version 1 → 22 represents an iterative build. Key milestones:
- Core theme + experience card UI
- Events calendar section
- Curated itineraries section
- "My Itinerary" save list with count badge
- Leaflet map integration for saved items
- Manage Data modal (full in-browser DB editor)
- Tag Manager modal
- Sortable columns in manage table
- Tag-pill editor with dropdown in manage table
- Season labels on experience cards
- Photo images via Unsplash CDN

---

## Known issues / things to watch
- Unsplash photos are hotlinked (no local copies) — if Unsplash changes URLs, photos break
- No persistence beyond localStorage (no backend, by design for static hosting)
- `inventory.xlsx` is a planning reference; the live data is in the JS arrays in `index.html`

---

## Deployment
- GitHub Pages compatible — just push `index.html` to a repo and enable Pages
- No build step required
- All fonts/maps loaded from CDN (Fonts.google.com, Cloudflare/Leaflet)

---

## How to continue
When picking up this project, open `index.html` in a browser to see the current state, then tell Claude:
- What you want to add or change
- Which section (themes, experiences, events, itineraries, UI, modals)

Common next steps the user has not yet done (possible backlog):
- Print / share itinerary as PDF
- Filter by area (Nevada City vs Grass Valley)
- Season filter (Spring / Summer / Fall / Winter / Year-Round)
- Mobile hamburger menu if nav grows
- "Suggest an experience" form
- More itineraries added to `ITINERARIES[]`
- More experiences added to `EXPERIENCES[]`

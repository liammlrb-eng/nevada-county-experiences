# Manual QA checklist

Run this before any substantial release (new feature, layout change,
county hand-off milestone). It covers what the automated suite can't:
visual judgment, mobile feel, and multi-step interaction chains.
Budget ~20 minutes. Log anything off in [bug_log.md](bug_log.md) as you
go — don't stop to fix mid-run.

Automated tests come first; this list assumes they're already green:

```powershell
pytest              # smoke + combo (~30s)
pytest -m visual    # pixel baselines — this machine only
```

## 1. First impressions (desktop)

- [ ] Cold load (Ctrl+Shift+R): no flash of unstyled content, no console
      errors, town strip photos all render (no broken-image icons)
- [ ] Clicking a lane tab *immediately* after load either works or shows
      the loading state — never a dead click (see `switchTab` in bug log)
- [ ] Page feels responsive within ~2s; nothing visibly "pops in" late

## 2. Lanes & editorial

- [ ] All four lanes — Explore / Suggested / Local Guides / Help Me Plan —
      open and show the right *kind* of content (hand-picked vs. authored
      vs. generated; the three-lanes distinction should be felt)
- [ ] Suggested Experiences: pick one and read it end-to-end — dates, links,
      and venue names still true (editorial rot check)
- [ ] Local Guides: images load, author voice intact, no truncated text

## 3. Filtering (the combo sweep checks errors; you check *sense*)

- [ ] Select 2–3 vibes in turn: the cards that appear actually match the
      vibe's promise (editorial fit, not just no-crash)
- [ ] Pills narrow believably — a pill that returns very few cards should
      feel scarce-but-right, not broken
- [ ] Deselect everything: grid returns to the full default set
- [ ] Search: type a town and a venue name; results appear as you type;
      clearing the search restores the grid

## 4. Events

- [ ] Today-boundary: no event dated yesterday or earlier anywhere in
      the grid
- [ ] Open 3 random event links from different sources — each lands on the
      venue's real page for *that* event (the NC Winery 404 class)
- [ ] An ongoing multi-day program (e.g. BYLT installations) reads
      sensibly — "On now through …" not a past date
- [ ] Calendar chips: text readable, dates correct, images load

## 5. Modal chains

- [ ] Help modal: open → close (X), open → close (click outside), open →
      close (Esc) — page scroll position survives all three
- [ ] Detail modal → close → open a different card: shows the new card's
      content, not stale data
- [ ] No scroll-behind: page under an open modal must not scroll

## 6. Mobile feel (real phone, not just DevTools)

- [ ] Load the GitHub Pages URL on your phone: layout intact at ~390px
- [ ] Town strip and vibe tiles: swipe/tap feel right, tap targets big
      enough to hit one-thumbed
- [ ] Calendar chip text wraps instead of overflowing
- [ ] Modals fill sensibly; close buttons reachable; background locked
- [ ] Rotate to landscape once: nothing breaks catastrophically

## 7. Trail map

- [ ] Map page loads, tiles render, trail lines draw (trails.geojson)
- [ ] Tap a trail: popup/detail content correct; pan + zoom smooth

## 8. Admin (Flask server running)

- [ ] Events Queue loads with counts; pending → approve → shows in
      approved filter immediately
- [ ] "Update Now" flips to "⏳ Scraping…" instantly; status bar shows
      progress and a clean one-line error if something fails
- [ ] QA Scan panel runs and reports

## 9. Feeds & sharing

- [ ] `feeds/events.ics` imports into a calendar app without complaint
- [ ] `feeds/events.rss` opens in a reader / validates
- [ ] Share a card link (if applicable): preview image + title look right
      in a messaging app

## 10. Cross-browser quick pass

- [ ] Edge (this laptop's daily driver): sections 1–3 spot-check
- [ ] Phone browser (Safari or Chrome): already covered by section 6
- [ ] Anything weird → bug log with browser noted

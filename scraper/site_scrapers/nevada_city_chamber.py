"""
Nevada City Chamber of Commerce — Community Calendar
====================================================
Public calendar page:
    https://www.nevadacitychamber.com/nevada-city-events/calendar-of-events/

The chamber's REAL events calendar runs on Trumba (webName
"nevada-city-chamber") — the same platform as the Nevada County Arts
Council. The structured JSON feed carries ~800 events: Off Broadstreet
Theatre runs, Rockin' the Gateway, historic walking tours, RailBus rides,
Malakoff Diggins programs, winery/restaurant events, gallery shows.

History: this scraper used to parse the chamber's hand-coded Essential
Grid page at /nevada-city-events/ (`li.eg-events-wrapper`), which only
exposed ~11 signature events with mostly unparseable dates. The Trumba
feed supersedes it entirely, so we point at that instead. All logic lives
in the shared TrumbaCalendarScraper base.

NOTE: This is a CONSOLIDATOR and overlaps NCAC + our direct scrapers
heavily; it runs late in ALL_SCRAPERS and merge() dedupes by
(title, date, area) so direct copies win.
"""
from __future__ import annotations

from .trumba import TrumbaCalendarScraper


class NevadaCityChamberScraper(TrumbaCalendarScraper):
    name     = "Nevada City Chamber"
    url      = "https://www.nevadacitychamber.com/nevada-city-events/calendar-of-events/"
    web_name = "nevada-city-chamber"

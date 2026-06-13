"""
Nevada County Arts Council — Arts & Culture Calendar
====================================================
Public page: https://www.nevadacountyarts.org/calendar/

NCAC bills its calendar as "the most comprehensive, accurate, and
up-to-date calendar of arts & culture events in Nevada County" and syncs
with other community calendars. It runs on Trumba (webName
"nevada-county-arts-council"), so all the work lives in the shared
TrumbaCalendarScraper base — this is just the config.
"""
from __future__ import annotations

from .trumba import TrumbaCalendarScraper


class NCACCalendarScraper(TrumbaCalendarScraper):
    name     = "NCAC Calendar"
    url      = "https://www.nevadacountyarts.org/calendar/"
    web_name = "nevada-county-arts-council"

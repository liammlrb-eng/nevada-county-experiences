"""
Generate a printable PDF: feature inventory + click-by-click demo script
for a Nevada County tourism-body presentation.

Run:   python generate_demo_pdf.py
Out:   demo_pitch.pdf  (in project root)
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem, Preformatted,
)
from reportlab.pdfgen import canvas
from datetime import date as _date
from pathlib import Path

# ── Brand colors ───────────────────────────────────────────────────────────
BROWN   = colors.HexColor('#5C3A1F')
GOLD    = colors.HexColor('#C9A84C')
SLATE   = colors.HexColor('#4A5568')
FOG     = colors.HexColor('#F5EFE2')
DARK    = colors.HexColor('#1E1508')
RULE    = colors.HexColor('#D4C9B0')

# ── Styles ─────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

H_TITLE = ParagraphStyle('Title', parent=styles['Title'],
    fontName='Helvetica-Bold', fontSize=26, leading=30,
    textColor=BROWN, alignment=TA_LEFT, spaceAfter=4)
H_SUB = ParagraphStyle('Subtitle', parent=styles['Normal'],
    fontName='Helvetica', fontSize=12, leading=16,
    textColor=SLATE, alignment=TA_LEFT, spaceAfter=18)
H1 = ParagraphStyle('H1', parent=styles['Heading1'],
    fontName='Helvetica-Bold', fontSize=18, leading=22,
    textColor=BROWN, spaceBefore=14, spaceAfter=8)
H2 = ParagraphStyle('H2', parent=styles['Heading2'],
    fontName='Helvetica-Bold', fontSize=13, leading=17,
    textColor=GOLD, spaceBefore=10, spaceAfter=4,
    letterSpacing=0.5)
H3 = ParagraphStyle('H3', parent=styles['Heading3'],
    fontName='Helvetica-Bold', fontSize=11, leading=15,
    textColor=DARK, spaceBefore=8, spaceAfter=2)
BODY = ParagraphStyle('Body', parent=styles['BodyText'],
    fontName='Helvetica', fontSize=9.5, leading=13.5,
    textColor=DARK, alignment=TA_LEFT, spaceAfter=4)
BODY_TIGHT = ParagraphStyle('BodyTight', parent=BODY,
    fontSize=9, leading=12, spaceAfter=2)
BULLET = ParagraphStyle('Bullet', parent=BODY,
    fontSize=9.5, leading=13, leftIndent=14, spaceAfter=2)
QUOTE = ParagraphStyle('Quote', parent=BODY,
    fontName='Helvetica-Oblique', fontSize=10.5, leading=14,
    textColor=BROWN, leftIndent=18, rightIndent=18,
    spaceBefore=4, spaceAfter=8, borderPadding=4)
SMALL = ParagraphStyle('Small', parent=BODY,
    fontSize=8.5, leading=11, textColor=SLATE)
LABEL = ParagraphStyle('Label', parent=BODY,
    fontName='Helvetica-Bold', fontSize=8, leading=11,
    textColor=GOLD, spaceBefore=2, spaceAfter=2)
CODE = ParagraphStyle('Code', parent=styles['Code'],
    fontName='Courier', fontSize=8, leading=10.5,
    textColor=DARK, backColor=colors.HexColor('#FBF7EE'),
    borderColor=RULE, borderWidth=0.5, borderPadding=6,
    leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8)

# ── Helpers ───────────────────────────────────────────────────────────────
def b(text):       return f'<b>{text}</b>'
def i(text):       return f'<i>{text}</i>'
def code(text):    return f'<font face="Courier" color="#5C3A1F">{text}</font>'
def goldhl(text):  return f'<font color="#C9A84C"><b>{text}</b></font>'

def section_rule(color=GOLD, width=6.5*inch, thickness=2):
    """Horizontal rule via a 1x1 table with a top border."""
    t = Table([['']], colWidths=[width], rowHeights=[thickness])
    t.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), thickness, color),
        ('LEFTPADDING',(0,0),(-1,-1),0), ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0), ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    return t

def build_table(rows, col_widths, header=True, zebra=True, body_size=9):
    """Standard styled table."""
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('FONT',       (0,0), (-1,-1), 'Helvetica', body_size),
        ('TEXTCOLOR',  (0,0), (-1,-1), DARK),
        ('LEFTPADDING',(0,0), (-1,-1), 6),
        ('RIGHTPADDING',(0,0),(-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LINEBELOW',  (0,0), (-1,0), 1.5, GOLD) if header else
            ('LINEBELOW', (0,0), (-1,0), 0, colors.white),
    ]
    if header:
        style += [
            ('FONT',      (0,0), (-1,0), 'Helvetica-Bold', body_size),
            ('TEXTCOLOR', (0,0), (-1,0), BROWN),
            ('BACKGROUND',(0,0), (-1,0), FOG),
        ]
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == (1 if header else 0):
                style.append(('BACKGROUND', (0,r), (-1,r), colors.HexColor('#FBF7EE')))
    style.append(('BOX', (0,0), (-1,-1), 0.5, RULE))
    style.append(('LINEBELOW', (0,0), (-1,-1), 0.25, RULE))
    t.setStyle(TableStyle(style))
    return t


# ── Page templates with footer ────────────────────────────────────────────
def page_footer(canv, doc):
    canv.saveState()
    canv.setFont('Helvetica', 8)
    canv.setFillColor(SLATE)
    canv.drawString(0.75*inch, 0.5*inch,
        'Nevada County Experience — County Demo Pitch')
    canv.drawRightString(LETTER[0]-0.75*inch, 0.5*inch,
        f'Page {doc.page}')
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(1)
    canv.line(0.75*inch, 0.7*inch, LETTER[0]-0.75*inch, 0.7*inch)
    canv.restoreState()


# ── Build the document ────────────────────────────────────────────────────
def build():
    out = Path(__file__).resolve().parent / 'demo_pitch.pdf'
    doc = SimpleDocTemplate(str(out), pagesize=LETTER,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.85*inch,
        title='Nevada County Experience — Demo Pitch',
        author='Nevada County Experience')

    flow = []

    # ──────────── COVER / OVERVIEW ────────────────────────────────────────
    flow.append(Paragraph('Nevada County Experience', H_TITLE))
    flow.append(Paragraph(
        'Visitor planning platform for <b>Western Nevada County</b> — '
        'feature overview &amp; demonstration script',
        H_SUB))
    flow.append(section_rule(GOLD, thickness=3))
    flow.append(Spacer(1, 14))

    flow.append(Paragraph('What this is', H1))
    flow.append(Paragraph(
        'A purpose-built tourism platform for <b>Western Nevada County</b> — the Gold Country '
        'foothills region centered on Nevada City and Grass Valley, with full coverage of '
        'Penn Valley, North San Juan, Rough &amp; Ready, Washington, Chicago Park, '
        'Smartsville, and adjacent Colfax. (Truckee and the Sierra-side areas of Nevada '
        'County are out of scope for this build.)',
        BODY))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(
        'The platform combines <b>161 curated experiences</b> with <b>460+ live-scraped '
        'events</b> from KVMR, Eventbrite, the Nevada City Chamber, the Grass Valley '
        'Chamber, and other local sources. Visitors discover what to do; the chamber team '
        'curates and approves what they see; the system runs without ongoing developer '
        'involvement.',
        BODY))
    flow.append(Spacer(1, 8))

    summary_rows = [
        ['Geographic scope',         'Western Nevada County (Gold Country foothills) + adjacent Colfax'],
        ['Total experiences',        '161 across 11 communities'],
        ['Live event sources',       '6 — KVMR, Eventbrite, NC Chamber, GV Chamber, The Union, Go Nevada'],
        ['Event count (approved)',   '460+'],
        ['Discovery vibes',          '9 themed + photo cards'],
        ['Filter dimensions',        'Area, Category (with sub-pills), Vibe, Date range'],
        ['Tag taxonomy',             '~30 unique tags'],
        ['Privacy posture',          'No tracking · no analytics · no cookies. Itinerary save is opt-in only with explicit consent banner. Visitor never identified.'],
        ['Hosting requirement',      'Any Linux/Windows server with Python; no database'],
        ['Recurring monthly cost',   '$5–$20 typical (hosting + ~$0.50/mo AI). See Cost Breakdown for detail.'],
        ['First-year total',         '~$80–$150 typical. ~$0 possible on free hosting tiers.'],
    ]
    flow.append(build_table(
        [['', '']] + summary_rows,  # empty header row spacer
        col_widths=[1.9*inch, 4.6*inch],
        header=False, zebra=True))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('How to use this document', H2))
    flow.append(Paragraph(
        'Pages 2–3 list every feature, organized by audience. Pages 4–5 walk through an '
        'eight-minute demo, click by click, that you can perform live. Page 6 is talking '
        'points to handle questions and last-minute prep notes.', BODY))

    flow.append(PageBreak())

    # ──────────── FEATURE INVENTORY — VISITORS ────────────────────────────
    flow.append(Paragraph('Feature Inventory', H_TITLE))
    flow.append(Paragraph('Everything the platform does today — built and tested.', H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('For Visitors', H1))

    flow.append(Paragraph('Discovery &amp; Filtering', H2))
    visitor_disc = [
        ['Area filter',          'Nevada City, Grass Valley, Penn Valley, North San Juan, Rough &amp; Ready, Washington, Chicago Park, Smartsville, plus adjacent Colfax and county-wide'],
        ['Category dropdown',    '15 categories — Lodging, Outdoor, Restaurant, Music venue, Wellness, etc.'],
        ['Sub-pills',            '7 categories show contextual sub-types (e.g. Lodging → Hotels, B&amp;Bs, Glamping, Campgrounds, RV)'],
        ['Themed vibes',         '9 photo cards: Historic, Arts &amp; Music, Hands-On, Foodie, Active, Relaxed, Wellness, Family, Festivals'],
        ['Date filter',          'Free range + quick presets: Today, This Weekend, This Week'],
        ['Auto-season hiding',   'Visiting in November? Summer-only experiences disappear automatically'],
        ['Active filter chips',  'Each active filter shown as a chip — one-click clear'],
        ['Tag-based search',     'Six new activity tags (Hiking, Biking, Running, Swimming, Fishing, Boating) attached to every relevant entry'],
    ]
    flow.append(build_table(
        [['Feature', 'Description']] + visitor_disc,
        col_widths=[1.7*inch, 4.8*inch]))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph('Planning Tools', H2))
    visitor_plan = [
        ['"Add to My List"',     'Heart on every card; floating itinerary button shows running count'],
        ['My Itinerary modal',   'Numbered stops, removable, with hours and direct links'],
        ['🔒 Opt-in device save', '<b>Privacy-by-default.</b> On first add, visitor is asked: "Save your itinerary on this device?" Yes → survives tab close, browser restart, and phone sleep. No → session only. Revocable anytime from the modal ("Forget on this device"). No data leaves the device, no account, no email, no tracking.'],
        ['📤 Share / Save link', 'One tap → native phone share sheet (text, email, AirDrop, copy link). The link restores the entire itinerary on any device. <b>Works without consent</b> — it\'s just a URL.'],
        ['Cross-device handoff',  'Build on phone in the morning, text the link to yourself, open on iPad in the car. No login, no sync service.'],
        ['Map view',             'Leaflet/OpenStreetMap with custom gold pin markers'],
        ['Print itinerary',      'One click — formatted for paper hand-off (also "Save as PDF" from print dialog)'],
        ['✨ Smart Suggestions', 'Algorithmic — finds nearby experiences and matching events; shows "0.3 mi away" labels'],
        ['Events inline',        'Upcoming events show alongside places, filtered by the same vibe and dates'],
        ['Google Maps pin',      'Custom SVG drop-pin button on each card opens directions'],
        ['RSS feed',             '/feed.rss publishes approved events for partner sites and aggregators'],
        ['Mobile responsive',    'All features work on phone &amp; tablet'],
    ]
    flow.append(build_table(
        [['Feature', 'Description']] + visitor_plan,
        col_widths=[1.7*inch, 4.8*inch]))

    flow.append(PageBreak())

    # ──────────── FEATURE INVENTORY — ADMIN ───────────────────────────────
    flow.append(Paragraph('For the Tourism Body / Admin', H1))

    flow.append(Paragraph('Content Management', H2))
    admin_content = [
        ['Inline experience editor', 'Sortable table of all 161 entries — edit, add, delete in browser'],
        ['Tag taxonomy editor',      'Add/remove/rename tags; changes propagate to filtering immediately'],
        ['Drag-drop itinerary builder', 'Three-panel UI: itineraries · stops · browse'],
        ['Events Queue',             'Pending / Approved / Dismissed with filter buttons'],
        ['Approve all',              'One-click bulk approval of pending events; auto-dismisses past dates'],
        ['Auto-prune',               'Past events removed nightly; dismissed items purged after 60 days'],
        ['Source management',        'Add/edit/disable scraper source URLs without touching code'],
    ]
    flow.append(build_table(
        [['Feature', 'Description']] + admin_content,
        col_widths=[1.9*inch, 4.6*inch]))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph('Automation', H2))
    admin_auto = [
        ['6 scrapers',           'KVMR, Eventbrite Nevada, NC Chamber, GV Chamber, The Union (RSS first), Go Nevada'],
        ['Auto-tagging',         'Keyword pipeline — every scraped event gets baseline tags'],
        ['🤖 AI Categorize',     'Claude Haiku refines tags, infers area &amp; venue, scores quality (~$0.20 per full run)'],
        ['On-demand scraping',   '"Update Now" button fires the scrape pipeline; status bar shows progress'],
        ['Idempotent processing','AI never re-categorizes already-processed events; cheap on subsequent runs'],
        ['Graceful degradation', 'Site works without the server (static fallback); without an API key (no AI)'],
    ]
    flow.append(build_table(
        [['Feature', 'Description']] + admin_auto,
        col_widths=[1.9*inch, 4.6*inch]))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph('Architecture &amp; Operations', H2))
    admin_ops = [
        ['No database',          'JSON files — easy backup, version control, no DBA needed'],
        ['Python &amp; Flask',   'Single small server; runs on any Linux/Windows VPS'],
        ['No vendor lock-in',    'No SaaS subscription; full code, full data ownership'],
        ['Self-hostable',        'Works behind Apache/Nginx; integrates with existing chamber infrastructure'],
        ['Static-friendly',      'Public site can be served as plain HTML if API isn\'t needed'],
        ['Open standards',       'OpenStreetMap, RSS 2.0, plain JSON — no proprietary formats'],
    ]
    flow.append(build_table(
        [['Feature', 'Description']] + admin_ops,
        col_widths=[1.9*inch, 4.6*inch]))

    flow.append(PageBreak())

    # ──────────── DEMO SCRIPT — INTRO + ACT 1 + ACT 2 ─────────────────────
    flow.append(Paragraph('Demonstration Script', H_TITLE))
    flow.append(Paragraph(
        'Eight-minute live walkthrough — visitor experience first, admin second.', H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('Setup (before the meeting)', H1))
    setup_items = [
        f'Run {code("python server.py")} in the project folder',
        f'Open {code("http://localhost:5000")} in a fresh browser window',
        'Confirm <b>My Itinerary</b> is empty (refresh / clear if needed)',
        'Have a second tab ready on the public view, but DON\'T show admin until Act 4',
        'Confirm the date is set in 2026 so seasonal experiences behave correctly',
    ]
    for s in setup_items:
        flow.append(Paragraph(f'• {s}', BULLET))

    flow.append(Spacer(1, 12))

    # Act 1
    flow.append(Paragraph('Act 1 — "I\'m a visitor planning a trip" · 2 min', H1))
    flow.append(Paragraph(
        '<i>"Pretend you\'re a couple from Sacramento planning a romantic November getaway."</i>',
        QUOTE))

    act1 = [
        ['Click "This Weekend" date preset',
         'Notice the trail and outdoor experiences that are summer-only just disappeared. The system knows what\'s actually available in November.'],
        ['Click the Festivals &amp; Celebrations vibe card',
         'Cornish Christmas, Victorian Christmas, and Mardi Gras appear at the top — exactly the things people travel here for in winter.'],
        ['Pause on a card',
         'Point out: real photo (pulled from the property website), tags, hours, notes, the More Info link, and the Add-to-List button.'],
    ]
    flow.append(build_table(
        [['Click', 'What to say']] + act1,
        col_widths=[2.2*inch, 4.3*inch]))

    flow.append(Spacer(1, 12))

    # Act 2
    flow.append(Paragraph('Act 2 — "Let me narrow further" · 90 sec', H1))
    act2 = [
        ['Clear date filter (X on the chip)',
         'Filter chips and dates clear instantly.'],
        ['Click Relaxed vibe (alongside Festivals)',
         '"You can layer multiple vibes. The grid recombines on the fly."'],
        ['Category dropdown → Lodging',
         'Sub-pills appear: Hotels · B&amp;Bs/Inns · Glamping · Campgrounds · RV Parks.'],
        ['Click 🏡 B&amp;Bs / Inns pill',
         '"These are real Victorian B&amp;Bs in Nevada City — Broad Street Inn, Flume\'s End, Piety Hill — every photo pulled directly from the property\'s own website."'],
        ['Add 2-3 favorites to the list',
         'The heart icon flips, the floating itinerary count increments.'],
    ]
    flow.append(build_table(
        [['Click', 'What to say']] + act2,
        col_widths=[2.2*inch, 4.3*inch]))

    flow.append(PageBreak())

    # ──────────── DEMO SCRIPT — ACTS 3, 4, 5 ───────────────────────────────
    flow.append(Paragraph('Act 3 — "Building my weekend" · 2 min', H1))

    act3 = [
        ['Clear the Lodging filter',
         'Back to the full grid.'],
        ['Switch to Foodie vibe',
         'Restaurants, wineries, breweries, and food festivals appear together.'],
        ['Add Lola Restaurant + Three Forks Bakery',
         'Heart fills, count goes up.'],
        ['Switch to Historic &amp; Gold Rush vibe',
         'Empire Mine, Narrow Gauge Railroad Museum surface to the top.'],
        ['Add Empire Mine to the list',
         ''],
        ['Click the My Itinerary floating button',
         'Modal opens. <b>This is the magic moment.</b>'],
        ['Scroll to ✨ More to Explore',
         '"The system noticed everything\'s clustered in Grass Valley + downtown Nevada City — so it\'s suggesting Holbrooke Hotel (0.4 mi away), North Star Mining Museum (0.3 mi away), and a Cornish Christmas event happening that exact weekend. <b>This is algorithmic, not curated.</b>"'],
        ['Click + Add to List on a suggestion',
         'Suggestions instantly recompute — list grows, new neighbors appear.'],
        ['Click 🗺 View on Map',
         'All stops appear on a Leaflet/OSM map with custom numbered gold pins.'],
        ['Add the first item (if fresh visit)',
         '<b>A small banner slides up:</b> "Save your itinerary on this device?" — explicit consent. <b>"Yes"</b> stores it locally; <b>"No thanks"</b> keeps it session-only. Either way, the share link still works. Privacy-respecting by design.'],
        ['Close the map, click 📤 Share / Save',
         '"Now imagine I built this on my phone — I want my partner to see it." On phone the native share sheet opens (text, email, AirDrop). On desktop the link copies to clipboard with a toast confirmation. <b>Paste the link into the URL bar in a private window — the whole itinerary restores instantly.</b>'],
        ['Reopen the modal',
         '"Notice the line at the bottom: <i>Saved on this device · Forget on this device</i>. Visitor can revoke anytime — just like the GDPR-style cookie consent they\'re used to."'],
        ['Click 🖨 Print',
         'Print preview opens — "Or save as PDF and email it. Print it for the fridge."'],
    ]
    flow.append(build_table(
        [['Click', 'What to say']] + act3,
        col_widths=[2.2*inch, 4.3*inch]))

    flow.append(Spacer(1, 12))

    flow.append(Paragraph('Act 4 — "Behind the scenes" · 90 sec', H1))
    flow.append(Paragraph(
        '<i>"Now let me show you what the chamber team would actually use."</i>', QUOTE))

    act4 = [
        ['Click ⚙ Manage Database (top right)',
         'Admin panel opens. Three management tabs: Experiences · Itineraries · Events Queue · Scraper Sources.'],
        ['Stay on the Experiences tab',
         '"All 161 entries — inline editable. No developer needed. Add a new venue, rename it, retag it, drag rows. Saved instantly."'],
        ['Click 📅 Events Queue',
         '"Where chamber staff review what\'s scraped overnight."'],
        ['Show pending count + filter buttons',
         '"KVMR posted twelve new events; click Approve All; done in five seconds."'],
        ['Click 🤖 AI Categorize',
         '"For about 20 cents we can have Claude clean up area names, infer venues for KVMR\'s vague entries, and flag spam — across the entire backlog. One click."'],
        ['Click 🔗 Scraper Sources',
         '"Add a new feed — say SYRCL\'s events RSS — paste the URL, save. The next overnight run picks it up. No developer involvement."'],
    ]
    flow.append(build_table(
        [['Click', 'What to say']] + act4,
        col_widths=[2.2*inch, 4.3*inch]))

    flow.append(Spacer(1, 12))

    flow.append(Paragraph('Act 5 — Close · 60 sec', H1))
    flow.append(Paragraph(
        '<i>"What this gives Nevada County:"</i>', QUOTE))
    closes = [
        '<b>Time saved for visitors</b> — they find Cornish Christmas + a B&amp;B in 30 seconds instead of 30 minutes across five different sites',
        '<b>Local business visibility</b> — every chamber member appears under multiple discovery paths: vibe, area, category, sub-pill, date filter, search-like tags',
        '<b>Privacy without compromise</b> — opt-in itinerary save with explicit consent, cross-device share via link, no tracking, no accounts, no emails. Visitors stay anonymous; the chamber gets credit for respecting them.',
        '<b>No vendor lock-in</b> — open files, no database, no SaaS contract',
        '<b>Self-publishing</b> — the public RSS feed is something other sites and apps can pick up automatically',
        '<b>Modern AI integration</b> — categorization today, smart visitor suggestions next, all opt-in and bounded by cost',
        '<b>Fresh data, low maintenance</b> — scrapers run on a schedule; chamber staff review and approve in minutes a week',
    ]
    for c in closes:
        flow.append(Paragraph(f'• {c}', BULLET))

    flow.append(PageBreak())

    # ──────────── TALKING POINTS / FAQ / WATCH-OUTS ────────────────────────
    flow.append(Paragraph('Talking Points', H_TITLE))
    flow.append(Paragraph('Anticipated questions and the right answers.', H_SUB))
    flow.append(section_rule())

    faq = [
        ['Can we host this ourselves?',
         'Yes — single Python file, runs on any Linux box. Apache or Nginx friendly. The code can sit in a Git repo and deploy in minutes.'],
        ['What if a venue closes or changes hours?',
         'Manage Database → click the row → edit or delete. Saved instantly. No developer. No release process.'],
        ['Can we add events from [specific source]?',
         'Yes — each scraper is a 100-line Python file. New sources are added by writing one matching that pattern.'],
        ['How fresh is the event data?',
         'Last scrape timestamp shows in the admin status bar. Schedule a daily cron job for hands-off freshness.'],
        ['Is the AI tagging accurate?',
         'Claude Haiku gets the obvious cases right (Center for the Arts → Grass Valley). Every AI field is ai_-prefixed; original scraper data is preserved; admins can override.'],
        ['What does it cost monthly?',
         'Typical: $10-$20/month all-in (hosting + AI). Lean setup possible at ~$1/month using a free hosting tier. See the Cost Breakdown section for the full picture and three scenario comparisons.'],
        ['Can we white-label this for the chamber?',
         'Yes — colors, logo, copy, photos all live in the HTML/CSS. No core changes needed.'],
        ['Does it work without internet?',
         'The static site degrades gracefully — visitors see curated experiences but not live events. Useful as a fallback.'],
        ['Privacy / data collection?',
         'No tracking, no analytics, no cookies by default. Visitor itineraries are <b>never stored without explicit consent</b> — visitor sees a banner asking "Save on this device?" and chooses Yes or No. The chamber sees zero personal information about visitors.'],
        ['What if a visitor wants to save / share their itinerary?',
         'Two independent options: (1) <b>Save on this device</b> — opt-in via consent banner; survives tab close + browser restart. Visitor can revoke from the modal anytime. (2) <b>📤 Share link</b> — works without consent, opens the phone\'s native share sheet (text, email, AirDrop) or copies a URL. The link restores the whole itinerary on any device.'],
        ['Accessibility?',
         'Semantic HTML, alt text on photos, keyboard navigation. WCAG-aligned but not formally audited.'],
    ]
    flow.append(build_table(
        [['Question', 'Answer']] + faq,
        col_widths=[1.9*inch, 4.6*inch]))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('Watch out for during the demo', H2))
    watches = [
        '<b>Server must be running</b> — if you forget, the Events tab and AI button will be empty. The site degrades gracefully but the demo is much weaker.',
        '<b>Don\'t open the admin panel first.</b> Visitors first; "and here\'s how easy it is to maintain" second.',
        '<b>Skip the feature-list slides.</b> The live demo IS the pitch. Use this PDF as your prep, not your slides.',
        '<b>Suggestions need 1+ items first.</b> Always add something before opening the My Itinerary modal.',
        '<b>If WiFi is bad,</b> the Leaflet map and any uncached photos may fail. Have a fallback screenshot.',
        '<b>Audience-fit:</b> the Foodie / Festivals / B&amp;Bs combination is most likely to land — they\'re universally appealing categories.',
    ]
    for w in watches:
        flow.append(Paragraph(f'• {w}', BULLET))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('Leave-behind one-liner', H2))
    flow.append(Paragraph(
        '<i>"This isn\'t a website — it\'s a planning workspace for visitors and a living '
        'directory for the chamber, with AI-assisted curation built in. Privacy-respecting '
        'by default, owned by the county outright, maintained in minutes per week."</i>',
        QUOTE))

    flow.append(PageBreak())

    # ──────────── COST BREAKDOWN ──────────────────────────────────────────
    flow.append(Paragraph('Cost Breakdown', H_TITLE))
    flow.append(Paragraph(
        'What it actually costs to run, based on real measured usage.', H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('Recurring monthly costs', H1))
    monthly_rows = [
        ['Web hosting',           'Any small Linux VPS (DigitalOcean, Linode, AWS Lightsail). Static-site option available if no admin features needed.', '$0 – $20'],
        ['Domain name',           'Optional — only if not already using existing chamber domain. Renewed annually at ~$12-15/year.', '$1 – $2'],
        ['SSL certificate',       'Free via Let\'s Encrypt; renews automatically.', '$0'],
        ['AI event categorization', 'Anthropic Claude Haiku API. Per measured usage (~460 events): $0.30 first run, then $0.01-$0.02 per scheduled scrape (only new events processed).', '$0.30 – $1.00'],
        ['Email / user accounts', 'No user accounts in the system. No email service required.', '$0'],
        ['Database',              'No database — JSON files. No DB hosting fees.', '$0'],
        ['Analytics',             'No third-party tracking by default. If desired, free options (Plausible self-hosted, GoatCounter) available.', '$0'],
    ]
    flow.append(build_table(
        [['Line item', 'Notes', 'Monthly cost']] + monthly_rows,
        col_widths=[1.5*inch, 3.5*inch, 1.5*inch]))

    flow.append(Spacer(1, 10))
    summary = [
        ['<b>Realistic monthly total</b>',                '<b>$5 – $25</b>'],
        ['Bare-minimum monthly total (free hosting tier)', '$0.30 – $1.00 (AI only)'],
        ['Typical chamber operation (paid VPS + AI)',     '$10 – $20'],
    ]
    flow.append(build_table(
        [['', '']] + summary,
        col_widths=[5.0*inch, 1.5*inch],
        header=False))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('One-time / annual costs', H1))
    onetime_rows = [
        ['Initial setup &amp; deployment', 'Configure server, install Python, deploy code, set up daily scrape cron, point domain. One person-day if done in-house, or contract dev work.', 'one-time'],
        ['Domain renewal',                'If purchasing new domain (e.g. visitwesternnevada.org).',                                                                          '~$12-15/yr'],
        ['Content review (annual)',       'Walking through all 161 experiences once a year to verify hours, URLs, photos. Roughly 4-6 staff hours; uses Manage Database panel.', '~$200 staff time'],
    ]
    flow.append(build_table(
        [['Line item', 'Notes', 'Cost']] + onetime_rows,
        col_widths=[2.0*inch, 3.5*inch, 1.0*inch]))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('AI cost detail (the only variable expense)', H1))
    flow.append(Paragraph(
        'The AI categorization cost is the only line item that scales with usage. '
        'Here\'s exactly what it costs based on measured token counts:', BODY))
    flow.append(Spacer(1, 4))

    ai_rows = [
        ['First-time bulk categorization (current 460 events)',  '$0.29',  'one-time'],
        ['Daily scrape + categorize (~10-30 new events/day)',    '$0.01 - $0.02 per run',  '$0.30 – $0.60 / mo'],
        ['Weekly scrape + categorize (~70-200 new events/week)', '$0.04 - $0.13 per run',  '$0.16 – $0.52 / mo'],
        ['Quarterly full re-categorize (with --force)',          '$0.30 per run',          '$0.10 / mo equiv.'],
        ['Realistic chamber operation (weekly + occasional re-runs)', 'mix', '<b>~$0.50 – $1.00 / mo</b>'],
    ]
    flow.append(build_table(
        [['Run pattern', 'Per-run cost', 'Monthly equivalent']] + ai_rows,
        col_widths=[3.0*inch, 1.5*inch, 2.0*inch]))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph('Built-in cost protection', H2))
    protections = [
        '<b>Hard usage cap on Anthropic side</b> — recommended $5/month spending limit set in API console. Cannot ever exceed it; emails sent at 50% / 75% / 100%.',
        '<b>Idempotent processing</b> — events that have already been categorized are skipped automatically. No accidental re-billing on the same data.',
        '<b>Optional, not required</b> — the entire AI feature can be turned off (no API key set) and the site still functions on raw scraper data.',
        '<b>Quality filter blocks waste</b> — events flagged "low quality" by AI are auto-hidden from the public site, reducing noise without manual review.',
    ]
    for p in protections:
        flow.append(Paragraph(f'• {p}', BULLET))

    flow.append(PageBreak())

    # ──────────── COMPARISON & TOTAL ───────────────────────────────────────
    flow.append(Paragraph('Annual Cost Summary', H_TITLE))
    flow.append(Paragraph(
        'Three realistic scenarios for the first year of operation.', H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('Three operating scenarios', H1))

    scenario_rows = [
        ['<b>Scenario</b>',                 '<b>Lean</b>',                   '<b>Typical</b>',                 '<b>Premium</b>'],
        ['Hosting',                         'Free tier (e.g. Oracle Cloud)', '$5/mo VPS',                      '$20/mo managed VPS'],
        ['Domain',                          'Use existing chamber domain',   'New domain (~$15/yr)',           'Premium domain'],
        ['AI categorization',               'Disabled or rare',              'Weekly runs (~$0.50/mo)',        'Daily runs + re-runs (~$1/mo)'],
        ['Content review',                  '4 hrs / year staff time',       '6 hrs / year',                   'Quarterly review'],
        ['Backups',                         'Manual quarterly',              'Automated weekly',               'Automated daily off-site'],
        ['<b>First-year total</b>',         '<b>~$0 – $50</b>',              '<b>~$80 – $150</b>',             '<b>~$300 – $500</b>'],
        ['<b>Subsequent annual</b>',        '<b>~$0 – $20</b>',              '<b>~$70 – $130</b>',             '<b>~$280 – $480</b>'],
    ]
    flow.append(build_table(
        scenario_rows,
        col_widths=[1.7*inch, 1.6*inch, 1.6*inch, 1.6*inch],
        header=True, body_size=8.5))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('What this means in practice', H1))
    flow.append(Paragraph(
        'For comparison, a commercial off-the-shelf tourism platform (CrowdRiff, '
        'Simpleview Destination Stack, or similar) typically runs <b>$5,000 – '
        '$30,000 annually</b> with multi-year contracts and per-feature pricing. '
        'The Nevada County Experience build delivers comparable visitor-facing '
        'capability for one to three orders of magnitude less, and the chamber '
        'owns all the code and data.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('What\'s NOT a cost', H2))
    not_costs = [
        '<b>Per-listing fees</b> — every chamber member can be listed at no incremental cost.',
        '<b>Per-event fees</b> — scraped events come in for free; AI categorization is the only variable cost.',
        '<b>Per-visitor fees</b> — no rate-based pricing; if traffic 10×\'s tomorrow, hosting cost barely changes.',
        '<b>License fees</b> — no proprietary software. Python, Flask, Leaflet, OpenStreetMap, all open source.',
        '<b>Vendor termination fees</b> — owned outright. No vendor to leave.',
        '<b>Migration costs</b> — JSON files are portable; can switch hosts in an afternoon.',
        '<b>Privacy compliance overhead</b> — no analytics, cookies, or trackers means no GDPR/CCPA banners, no privacy review, no consent platform fees. Itinerary save is opt-in by design.',
    ]
    for n in not_costs:
        flow.append(Paragraph(f'• {n}', BULLET))

    flow.append(Spacer(1, 12))
    flow.append(Paragraph('Recommended starting budget', H2))
    flow.append(Paragraph(
        '<b>$200 in the first year</b> covers everything: domain ($15), modest VPS '
        'hosting ($60/year), AI categorization ($10), and a small reserve. '
        'Subsequent years drop to ~$85 if domain doesn\'t need renewal that year. '
        'No staff training cost — the admin panel is intentionally simple enough '
        'that anyone who can edit a spreadsheet can maintain it.',
        BODY))

    flow.append(PageBreak())

    # ──────────── MIGRATION TO COUNTY SERVER ──────────────────────────────
    flow.append(Paragraph('Migration to a County Server', H_TITLE))
    flow.append(Paragraph(
        'Step-by-step deployment from local development to production hosting.', H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph(
        'This is the full sequence to move the platform from a developer laptop '
        'to a production server the chamber controls. Estimated effort: '
        '<b>one focused half-day</b> for someone comfortable with Linux, '
        '<b>two days</b> for someone learning as they go. No code changes are '
        'required — the same files run locally and in production.', BODY))

    flow.append(Spacer(1, 8))

    # ── Phase 0 ────
    flow.append(Paragraph('Phase 0 — Decisions before you start', H1))
    flow.append(Paragraph(
        'Lock these down first. Each affects what comes next.', BODY))
    decision_rows = [
        ['Decision',                      'Recommended',                                  'Alternative'],
        ['Hosting provider',              'DigitalOcean ($6/mo droplet) or Linode',       "AWS Lightsail · chamber's existing host · county-IT VM"],
        ['Operating system',              'Ubuntu 24.04 LTS',                             'Debian 12 · RHEL 9 · Windows Server (more work)'],
        ['Domain',                        'New: visitwesternnevada.org (~$15/yr)',        'Subdomain: experience.nevadacountychamber.com'],
        ['Server account owner',          'Chamber / county directly',                    'Contracted dev (lock-out risk)'],
        ['SSL certificate',               "Free Let's Encrypt (auto-renew)",              'Paid cert (no real benefit)'],
        ['Backups',                       'Provider snapshots + monthly off-site copy',   'Snapshots only · weekly tar to chamber NAS'],
    ]
    flow.append(build_table(decision_rows,
        col_widths=[1.5*inch, 2.4*inch, 2.6*inch],
        header=True, body_size=8.5))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph(
        '<b>Decision-point:</b> if the county already has a web server (Apache or '
        'nginx running on a county-IT box), you can run this <i>next to</i> the '
        'existing site. If not, a fresh small VPS is cleaner and the cost is trivial.',
        BODY))

    flow.append(Spacer(1, 12))

    # ── Phase 1 ────
    flow.append(Paragraph('Phase 1 — Pre-flight checklist', H1))
    flow.append(Paragraph('Confirm all of these before continuing:', BODY))
    preflight = [
        'Domain registered (or subdomain delegated)',
        'DNS access confirmed — you can edit A records',
        'Anthropic API key created at console.anthropic.com (with $5/mo cap set)',
        'SSH key generated locally (id_ed25519 or id_rsa)',
        'You can SSH and copy files between your laptop and the server',
        'Cloudflare or similar set up (optional — adds free DDoS + caching)',
    ]
    for p in preflight:
        flow.append(Paragraph(f'☐ &nbsp; {p}', BULLET))

    flow.append(PageBreak())

    # ── Phase 2 ────
    flow.append(Paragraph('Phase 2 — Provision the server', H1))

    flow.append(Paragraph('2a. Buy the droplet', H2))
    flow.append(Paragraph(
        'DigitalOcean → Create → Droplet → <b>Ubuntu 24.04 LTS</b> → Basic plan, $6/mo '
        '(1 GB RAM, 25 GB SSD) → datacenter near the West Coast (San Francisco 3) → '
        'add your SSH key → name it <font face="Courier">nevada-county-experience</font> → Create.',
        BODY))

    flow.append(Paragraph('2b. First login + lockdown', H2))
    flow.append(Preformatted("""# From your laptop
ssh root@<droplet-ip>

# Create a non-root user, give them sudo
adduser ncexp
usermod -aG sudo ncexp
mkdir -p /home/ncexp/.ssh
cp ~/.ssh/authorized_keys /home/ncexp/.ssh/
chown -R ncexp:ncexp /home/ncexp/.ssh
chmod 700 /home/ncexp/.ssh
chmod 600 /home/ncexp/.ssh/authorized_keys

# Disable root SSH login
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
exit

# From now on, SSH as ncexp
ssh ncexp@<droplet-ip>""", CODE))

    flow.append(Paragraph('2c. System packages', H2))
    flow.append(Preformatted("""sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv \\
                    nginx git ufw certbot python3-certbot-nginx \\
                    chromium-browser chromium-chromedriver

# Firewall: SSH + HTTPS only
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable""", CODE))

    flow.append(PageBreak())

    # ── Phase 3 ────
    flow.append(Paragraph('Phase 3 — Deploy the application', H1))

    flow.append(Paragraph('3a. Get the code onto the server', H2))
    flow.append(Paragraph(
        '<b>Recommended:</b> push to a private GitHub repo from your laptop, '
        'clone on the server. <b>Alternative:</b> zip the folder and use scp.', BODY))
    flow.append(Preformatted("""# On your laptop (one-time)
cd "C:\\Users\\Curious Forge\\Documents\\nevada-county-experience"
git init
git add .
git commit -m "Initial commit"
gh repo create nevada-county-experience --private --source=. --push

# On the server
cd /home/ncexp
git clone https://github.com/<your-user>/nevada-county-experience.git
cd nevada-county-experience""", CODE))

    flow.append(Paragraph('3b. Python environment', H2))
    flow.append(Preformatted("""cd /home/ncexp/nevada-county-experience
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests beautifulsoup4 lxml selenium \\
            webdriver-manager python-dateutil reportlab
deactivate""", CODE))

    flow.append(Paragraph('3c. Create the secrets file', H2))
    flow.append(Paragraph(
        '<font face="Courier">scraper/config.py</font> is gitignored, so the keys '
        'never leave this server.', BODY))
    flow.append(Preformatted("""cat > scraper/config.py <<'EOF'
GOOGLE_PLACES_API_KEY = "<paste from your local config.py>"
ANTHROPIC_API_KEY = "sk-ant-api03-..."
CENTER_LAT = 39.2350
CENTER_LNG = -121.038
RADIUS_M = 35000
MIN_RATINGS = 5
MIN_RATING = 3.5
EOF
chmod 600 scraper/config.py""", CODE))

    flow.append(Paragraph('3d. Smoke test', H2))
    flow.append(Preformatted("""source .venv/bin/activate
python server.py
# Should show "Running on http://127.0.0.1:5000"
# Press Ctrl+C
deactivate""", CODE))

    flow.append(PageBreak())

    # ── Phase 4 ────
    flow.append(Paragraph('Phase 4 — Run as a persistent service', H1))
    flow.append(Paragraph(
        'systemd auto-starts the server on reboot and auto-restarts if it '
        'crashes. Logs go to <font face="Courier">journalctl</font>.', BODY))
    flow.append(Preformatted("""sudo tee /etc/systemd/system/ncexp.service > /dev/null <<'EOF'
[Unit]
Description=Nevada County Experience web app
After=network.target

[Service]
Type=simple
User=ncexp
WorkingDirectory=/home/ncexp/nevada-county-experience
Environment="PATH=/home/ncexp/nevada-county-experience/.venv/bin"
ExecStart=/home/ncexp/nevada-county-experience/.venv/bin/python \\
          server.py --host 127.0.0.1 --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ncexp
sudo systemctl start ncexp
sudo systemctl status ncexp     # should show "active (running)"

# View logs anytime:
journalctl -u ncexp -f""", CODE))

    flow.append(Spacer(1, 8))

    # ── Phase 5 ────
    flow.append(Paragraph('Phase 5 — Reverse proxy + HTTPS', H1))
    flow.append(Paragraph(
        'Flask shouldn\'t face the internet directly. nginx sits in front and '
        'terminates HTTPS via Let\'s Encrypt.', BODY))

    flow.append(Paragraph('5a. Point DNS to the server', H2))
    flow.append(Preformatted("""# At your registrar:
A     visitwesternnevada.org       -> <droplet-ip>
A     www.visitwesternnevada.org   -> <droplet-ip>

# Wait 5-30 min, then verify from your laptop:
dig visitwesternnevada.org""", CODE))

    flow.append(Paragraph('5b. nginx config', H2))
    flow.append(Preformatted("""sudo tee /etc/nginx/sites-available/ncexp > /dev/null <<'EOF'
server {
    listen 80;
    server_name visitwesternnevada.org www.visitwesternnevada.org;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Cache static assets aggressively
    location ~* \\.(jpg|jpeg|png|webp|gif|svg|css|js|woff2|ico)$ {
        proxy_pass http://127.0.0.1:5000;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/ncexp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx""", CODE))

    flow.append(Paragraph('5c. Add HTTPS', H2))
    flow.append(Preformatted("""sudo certbot --nginx -d visitwesternnevada.org -d www.visitwesternnevada.org
# Enter email, agree to TOS, choose "redirect HTTP to HTTPS" """, CODE))
    flow.append(Paragraph(
        'Certbot adds a cron job that auto-renews certificates 30 days before '
        'expiry. Set and forget.', BODY))

    flow.append(PageBreak())

    # ── Phase 6 ────
    flow.append(Paragraph('Phase 6 — Schedule the scraper', H1))
    flow.append(Paragraph(
        'Nightly scrape at 3 AM, AI categorization 30 minutes later. '
        'Chamber staff review pending events the next morning.', BODY))
    flow.append(Preformatted("""# Edit the user's crontab
crontab -e

# Add these two lines:
0 3 * * * cd /home/ncexp/nevada-county-experience && \\
   .venv/bin/python scraper/event_scraper.py >> /var/log/ncexp-scrape.log 2>&1
30 3 * * * cd /home/ncexp/nevada-county-experience && \\
   .venv/bin/python scraper/ai_categorize.py >> /var/log/ncexp-ai.log 2>&1

# Make the log files writable
sudo touch /var/log/ncexp-scrape.log /var/log/ncexp-ai.log
sudo chown ncexp:ncexp /var/log/ncexp-scrape.log /var/log/ncexp-ai.log

# Run the scraper once manually to verify Selenium + Chromium work:
cd /home/ncexp/nevada-county-experience
.venv/bin/python scraper/event_scraper.py --site "Nevada City Chamber" """, CODE))

    flow.append(Spacer(1, 8))

    # ── Phase 7 ────
    flow.append(Paragraph('Phase 7 — Backups', H1))
    flow.append(Paragraph(
        'Two layers: provider snapshots for full-system recovery, '
        'plus a daily JSON dump for granular event/itinerary recovery.', BODY))

    flow.append(Paragraph('7a. Provider snapshots ($1/mo on DigitalOcean)', H2))
    flow.append(Paragraph(
        'DO Console → Droplet → Backups → Enable. Weekly automatic, 4-week retention.',
        BODY))

    flow.append(Paragraph('7b. Daily JSON backup', H2))
    flow.append(Preformatted("""mkdir -p /home/ncexp/backups
cat > /home/ncexp/backup.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
cd /home/ncexp/nevada-county-experience
tar czf /home/ncexp/backups/ncexp-$DATE.tar.gz \\
    scraper_output/events.json scraper/sources.json scraper/config.py
# Keep only last 30 days
find /home/ncexp/backups/ -name 'ncexp-*.tar.gz' -mtime +30 -delete
EOF
chmod +x /home/ncexp/backup.sh

# Schedule daily at 4 AM (after scrape + AI complete)
crontab -e
# Add:
0 4 * * * /home/ncexp/backup.sh""", CODE))

    flow.append(Paragraph('7c. Off-site copy (optional but recommended)', H2))
    flow.append(Paragraph(
        'Once a month, copy the latest backup tarball to chamber NAS, '
        'Google Drive, or another cloud. Even a manual quarterly download '
        'protects against catastrophic provider loss.', BODY))

    flow.append(PageBreak())

    # ── Phase 8 ────
    flow.append(Paragraph('Phase 8 — Test &amp; cutover', H1))
    test_rows = [
        ['Public site loads at https://...',
         'Browse to the domain. Confirm padlock + "https" + green/normal cert.'],
        ['All vibes show experiences',
         'Click each of the 9 vibe cards; each should return matches.'],
        ['Events tab populates',
         'Should show ~460 approved events. If empty, server isn\'t reaching events.json.'],
        ['Date filter works',
         'Pick "This Weekend" — events filter; some experiences hide based on season.'],
        ['Mobile share works',
         'On a phone, build a list, hit Share. Native share sheet should appear.'],
        ['Admin panel accessible',
         'Click ⚙ Manage Database. All four tabs should render.'],
        ['Scraper runs by hand',
         'sudo -u ncexp .venv/bin/python scraper/event_scraper.py --site "Nevada City Chamber"'],
        ['AI Categorize button works',
         'Manage Database → Events Queue → 🤖 AI Categorize → enter 3 → confirm enrichment appears in events.json.'],
        ['Cron jobs scheduled',
         'sudo crontab -u ncexp -l should show the 3 AM and 3:30 AM lines.'],
        ['Backups running',
         'Wait until tomorrow morning, confirm /home/ncexp/backups has a new file.'],
        ['Service restarts',
         'sudo systemctl restart ncexp; site comes back within 2 seconds.'],
        ['HTTPS auto-renews',
         'sudo certbot renew --dry-run should report success on all certs.'],
    ]
    flow.append(build_table(
        [['Test', 'How to verify']] + test_rows,
        col_widths=[2.0*inch, 4.5*inch],
        header=True, body_size=8.5))

    flow.append(Spacer(1, 12))

    # ── Phase 9 ────
    flow.append(Paragraph('Phase 9 — Handoff to chamber', H1))
    flow.append(Paragraph(
        'After the technical setup, hand the chamber team a small kit so they '
        'can operate the system day-to-day.', BODY))
    handoff = [
        '<b>Admin URL bookmarked</b> on the chamber\'s computers — they only need to remember the public URL; the admin panel is reached from a button on the home page',
        '<b>Anthropic billing alerts</b> set up to email the chamber\'s ops manager at 50% / 75% / 100% of monthly cap',
        '<b>One-page cheat sheet</b> covering: how to approve events, how to add a venue, how to revoke an event after approval, how to trigger a manual scrape',
        '<b>Emergency contact</b> identified — who fixes it if the server is down? County IT? A contractor on retainer? The original developer?',
        '<b>Annual review on the calendar</b> — once a year, walk through all 161 experiences, verify hours/URLs/photos, prune anything closed',
        '<b>Backup test</b> — once before going live, restore from a backup to a test droplet to confirm the recovery process works',
        '<b>Domain renewal calendar reminder</b> — set 90 days before expiry so it never lapses',
    ]
    for h in handoff:
        flow.append(Paragraph(f'• {h}', BULLET))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('Estimated effort &amp; timeline', H2))
    timeline_rows = [
        ['Confident Linux admin',         '4 hours (single afternoon)',  '~$400 contracted'],
        ['Self-taught learner',           '2 days (with research time)', 'time only'],
        ['County IT department',          'Schedule-dependent',          'internal'],
        ['Hosted-by-developer option',    'Same day',                    '~$50/mo managed'],
    ]
    flow.append(build_table(
        [['Path', 'Time to live', 'Approximate cost']] + timeline_rows,
        col_widths=[2.2*inch, 2.5*inch, 1.8*inch]))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('Common pitfalls to watch for', H2))
    pitfalls = [
        '<b>Selenium / ChromeDriver version mismatch</b> — if scrapes fail with "session not created", apt usually keeps chromium-browser and chromium-chromedriver in sync, but a manual chromedriver download may be needed',
        '<b>Firewall too tight</b> — make sure ports 80 and 443 are open via ufw before running certbot, or HTTPS setup will fail',
        '<b>Time zone</b> — server defaults to UTC; cron jobs run in UTC. Either set the server to America/Los_Angeles or schedule jobs in UTC (3 AM PT = 11 AM UTC)',
        '<b>File permissions on scraper output</b> — events.json must be writable by the ncexp user, or the scraper silently fails',
        '<b>Anthropic API key in repo</b> — confirm scraper/config.py is gitignored before first git push',
    ]
    for p in pitfalls:
        flow.append(Paragraph(f'• {p}', BULLET))

    # ──────────── BUILD ──────────────────────────────────────────────────
    doc.build(flow,
        onFirstPage=page_footer,
        onLaterPages=page_footer)
    print(f'Wrote: {out}')
    return out


if __name__ == '__main__':
    build()

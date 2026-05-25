"""
Generate operator_guide.pdf — day-to-day operations manual for whoever
maintains the Nevada County Experience platform (chamber staff or contractor).

Run:   python generate_operator_guide.py
Out:   operator_guide.pdf  (in project root)
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Preformatted,
)
from pathlib import Path

# ── Brand colors (match demo_pitch.pdf) ───────────────────────────────────
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
    textColor=SLATE, spaceAfter=18)
H1 = ParagraphStyle('H1', parent=styles['Heading1'],
    fontName='Helvetica-Bold', fontSize=18, leading=22,
    textColor=BROWN, spaceBefore=14, spaceAfter=8)
H2 = ParagraphStyle('H2', parent=styles['Heading2'],
    fontName='Helvetica-Bold', fontSize=13, leading=17,
    textColor=GOLD, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle('Body', parent=styles['BodyText'],
    fontName='Helvetica', fontSize=10, leading=14, textColor=DARK, spaceAfter=4)
BULLET = ParagraphStyle('Bullet', parent=BODY,
    fontSize=10, leading=14, leftIndent=14, spaceAfter=2)
QUOTE = ParagraphStyle('Quote', parent=BODY,
    fontName='Helvetica-Oblique', fontSize=10.5, leading=14,
    textColor=BROWN, leftIndent=18, rightIndent=18,
    spaceBefore=4, spaceAfter=8)
CODE = ParagraphStyle('Code', parent=styles['Code'],
    fontName='Courier', fontSize=8.5, leading=11.5,
    textColor=DARK, backColor=colors.HexColor('#FBF7EE'),
    borderColor=RULE, borderWidth=0.5, borderPadding=6,
    leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8)
WARN = ParagraphStyle('Warn', parent=BODY,
    fontSize=9.5, leading=13, textColor=colors.HexColor('#8B0000'),
    backColor=colors.HexColor('#FFF8E1'), borderColor=GOLD,
    borderWidth=1, borderPadding=8, spaceBefore=6, spaceAfter=8)


def section_rule(color=GOLD, width=6.5*inch, thickness=2):
    t = Table([['']], colWidths=[width], rowHeights=[thickness])
    t.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), thickness, color),
        ('LEFTPADDING',(0,0),(-1,-1),0), ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0), ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    return t


def build_table(rows, col_widths, header=True, zebra=True, body_size=9.5):
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('FONT',       (0,0), (-1,-1), 'Helvetica', body_size),
        ('TEXTCOLOR',  (0,0), (-1,-1), DARK),
        ('LEFTPADDING',(0,0), (-1,-1), 6),
        ('RIGHTPADDING',(0,0),(-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ]
    if header:
        style += [
            ('FONT',      (0,0), (-1,0), 'Helvetica-Bold', body_size),
            ('TEXTCOLOR', (0,0), (-1,0), BROWN),
            ('BACKGROUND',(0,0), (-1,0), FOG),
            ('LINEBELOW', (0,0), (-1,0), 1.5, GOLD),
        ]
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == (1 if header else 0):
                style.append(('BACKGROUND', (0,r), (-1,r), colors.HexColor('#FBF7EE')))
    style.append(('BOX', (0,0), (-1,-1), 0.5, RULE))
    style.append(('LINEBELOW', (0,0), (-1,-1), 0.25, RULE))
    t.setStyle(TableStyle(style))
    return t


def page_footer(canv, doc):
    canv.saveState()
    canv.setFont('Helvetica', 8)
    canv.setFillColor(SLATE)
    canv.drawString(0.75*inch, 0.5*inch,
        'Nevada County Experience — Operator Guide')
    canv.drawRightString(LETTER[0]-0.75*inch, 0.5*inch,
        f'Page {doc.page}')
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(1)
    canv.line(0.75*inch, 0.7*inch, LETTER[0]-0.75*inch, 0.7*inch)
    canv.restoreState()


def build():
    out = Path(__file__).resolve().parent / 'operator_guide.pdf'
    doc = SimpleDocTemplate(str(out), pagesize=LETTER,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.85*inch,
        title='Nevada County Experience — Operator Guide',
        author='Nevada County Experience')
    flow = []

    # ─────────── COVER ──────────────────────────────────────────────────
    flow.append(Paragraph('Operator Guide', H_TITLE))
    flow.append(Paragraph(
        'Day-to-day operations manual for the Nevada County Experience platform.',
        H_SUB))
    flow.append(section_rule(thickness=3))
    flow.append(Spacer(1, 14))

    flow.append(Paragraph('Who this is for', H1))
    flow.append(Paragraph(
        'Whoever runs the platform week to week — chamber staff, county-IT, '
        'or a contractor on retainer. This guide assumes:',
        BODY))
    assumes = [
        'You can use a web browser and File Explorer competently',
        'You can open a terminal (PowerShell or cmd) and type a command',
        'You don\'t need to write code',
    ]
    for a in assumes:
        flow.append(Paragraph(f'• {a}', BULLET))

    flow.append(Spacer(1, 12))
    flow.append(Paragraph('How to use this guide', H1))
    flow.append(Paragraph(
        'Each section is a single, self-contained workflow with copy-paste '
        'commands. The Quick Reference page lists the most common tasks. '
        'When in doubt, jump to Troubleshooting at the end.',
        BODY))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('Quick Reference', H1))
    qr_rows = [
        ['Goal',                                 'Section',                     'Time'],
        ['Start the local server',               'Section 1',                   '30 sec'],
        ['Scrape & approve new events',          'Section 2 + 3',               '5 min'],
        ['Run AI to clean up tags & areas',      'Section 4',                   '~1 min'],
        ['Add or edit an experience',            'Section 5',                   '2 min/entry'],
        ['Update the live demo on GitHub Pages', 'Section 6',                   '2 min'],
        ['Share public feeds with a partner',    'Section 7',                   '1 min'],
        ['Force a venue into a pill (override)',  'Section 5f',                 '30 sec'],
        ['Run a quality scan (monthly)',         'Section 5g',                  '~1 sec'],
        ['Stop the server',                      'Section 1c',                  '5 sec'],
        ['Something\'s broken',                  'Section 8 (Troubleshooting)', 'varies'],
        ['Where do files live?',                 'Section 9 (File map)',        'reference'],
    ]
    flow.append(build_table(qr_rows,
        col_widths=[3.0*inch, 2.0*inch, 1.5*inch], header=True))

    flow.append(PageBreak())

    # ─────────── SECTION 1: SERVER ──────────────────────────────────────
    flow.append(Paragraph('1. Starting &amp; stopping the local server', H_TITLE))
    flow.append(Paragraph(
        'The local Flask server is required for the admin panel, AI Categorize, '
        'and live event scraping.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('1a. Easiest: double-click the launcher', H1))
    flow.append(Paragraph(
        'In the project folder there\'s a file named <font face="Courier">'
        'start_server.bat</font>. <b>Double-click it.</b> A console window '
        'opens, prints "Running on http://127.0.0.1:5000", and stays open '
        'while the server runs.',
        BODY))
    flow.append(Paragraph(
        '<b>Tip:</b> right-click <font face="Courier">start_server.bat</font> → '
        'Send to → Desktop (create shortcut), so you can launch from the desktop.',
        BODY))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph('1b. From PowerShell (alternative)', H1))
    flow.append(Preformatted("""cd "C:\\Users\\<your-user>\\Documents\\nevada-county-experience"
python server.py""", CODE))
    flow.append(Paragraph(
        'You should see:', BODY))
    flow.append(Preformatted("""========================================================
  Nevada County Experience -- Local Server
  http://127.0.0.1:5000/
  Press Ctrl+C to stop
========================================================
 * Running on http://127.0.0.1:5000""", CODE))

    flow.append(Paragraph('1c. To stop the server', H1))
    flow.append(Paragraph(
        'In the console window where it\'s running, press <b>Ctrl+C</b> once. '
        'The window stays open — you can type the start command again, or '
        'just close the window.',
        BODY))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph('1d. Open the site in your browser', H1))
    flow.append(Paragraph(
        'Go to <b>http://localhost:5000</b> while the server is running. '
        'Bookmark it.',
        BODY))

    flow.append(PageBreak())

    # ─────────── SECTION 2: SCRAPE EVENTS ───────────────────────────────
    flow.append(Paragraph('2. Scrape new events', H_TITLE))
    flow.append(Paragraph(
        'Pulls fresh events from 12 active sources — KVMR, NCAC Calendar, '
        'Eventbrite, the Chambers, Center for the Arts, Miners Foundry, '
        'Crazy Horse Saloon, Golden Era Lounge, The Curious Forge, '
        'Wolf Craft Collective, and Nevada County Fairgrounds. Run weekly '
        'or whenever you want fresh data.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('2a. From the admin panel (easiest)', H1))
    steps_2a = [
        'Make sure the server is running (Section 1)',
        'Open http://localhost:5000 in your browser',
        'Click <b>⚙ Manage Database</b> in the top-right corner',
        'Click the <b>📅 Events Queue</b> tab',
        'Click the green <b>🔄 Update Now</b> button (top right)',
        'Wait 30-90 seconds — the status bar shows "⟳ Scraping in progress…"',
        'When it finishes, switch to the <b>Pending</b> tab — new events appear there',
    ]
    for i, s in enumerate(steps_2a, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('2b. From the command line (advanced)', H1))
    flow.append(Preformatted("""cd "C:\\Users\\<your-user>\\Documents\\nevada-county-experience"
python scraper\\event_scraper.py

# Or scrape a single source:
python scraper\\event_scraper.py --site "Nevada City Chamber" """, CODE))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('What gets scraped', H2))
    src_rows = [
        ['NCAC Calendar',          'Trumba JSON feed',                     '~580 events'],
        ['KVMR',                   'Tribe Events RSS feed',                '~490 events'],
        ['The Curious Forge',      'WooCommerce Store API',                '~65 class sessions'],
        ['Crazy Horse Saloon',     'The Events Calendar REST API',         '~25 events'],
        ['Center for the Arts',    'requests + Selenium fallback',         '~20 concerts'],
        ['Eventbrite Nevada',      'Headless Chrome (React)',              '~10 events'],
        ['Nevada City Chamber',    'Static HTML',                          '~10 events'],
        ['Wolf Craft Collective',  'Shopify products.json',                '~10 craft classes'],
        ['Golden Era Lounge',      'Squarespace events JSON',              '~10 events'],
        ['Nevada County Fairgrounds', 'Saffire JSONP (eventsservice.asmx)', '~7 fair/festival events'],
        ['Miners Foundry',         'Headless Chrome (site 403s requests)', '~5-10 events'],
        ['GV Chamber',             'Static HTML (Elementor)',              '~5 events'],
        ['The Union',              'RSS first, Selenium fallback',         'Varies (paywall)'],
    ]
    flow.append(build_table(
        [['Source', 'Method', 'Typical volume']] + src_rows,
        col_widths=[2.0*inch, 2.7*inch, 1.8*inch]))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        '<b>Disabled scrapers</b> (kept in the codebase, off by default): '
        '<i>Go Nevada</i> and <i>Go Nevada Festivals</i> — Cloudflare 403s both '
        'requests and headless Chrome. <i>Nevada Theatre</i> — MEC plugin '
        'archive is AJAX-lazy-loaded and not worth a slow brittle scrape '
        '(KVMR already covers it well).',
        BODY))

    flow.append(PageBreak())

    # ─────────── SECTION 3: APPROVE EVENTS ──────────────────────────────
    flow.append(Paragraph('3. Approve, dismiss, prune events', H_TITLE))
    flow.append(Paragraph(
        'After scraping, new events sit in the Pending queue. Approve to publish; '
        'dismiss to hide permanently.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('3a. Approve individual events', H1))
    flow.append(Paragraph(
        'In the Events Queue → Pending tab:', BODY))
    indiv = [
        '<b>✓ Approve</b> button: event becomes visible to the public',
        '<b>✕ Dismiss</b> button: event hidden permanently. Won\'t come back even if scraped again.',
        'Click the event title to open the source page in a new tab',
    ]
    for s in indiv:
        flow.append(Paragraph(f'• {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('3b. Approve them all at once', H1))
    flow.append(Paragraph(
        'When the queue is mostly noise-free (typical after AI categorization '
        'flags low-quality items), use bulk approval:', BODY))
    flow.append(Paragraph(
        '<b>"Approve All"</b> button — approves everything pending whose date is '
        'today or in the future. Past-dated pending events are auto-dismissed '
        '(prevents stale items from re-appearing).', BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('3c. Filter the queue', H1))
    flow.append(Paragraph(
        'Above the table you\'ll find filter controls:', BODY))
    filt = [
        '<b>Status:</b> Pending / Approved / Dismissed (one tab each)',
        '<b>Source:</b> dropdown — see only KVMR, only Eventbrite, etc.',
        '<b>Date range:</b> two date inputs — narrow to a specific window',
    ]
    for s in filt:
        flow.append(Paragraph(f'• {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('3d. Pruning past events', H1))
    flow.append(Paragraph(
        'The pruner removes:', BODY))
    prune = [
        'Pending or approved events whose date has passed',
        'Dismissed events older than 60 days (long enough to prevent re-import)',
    ]
    for p in prune:
        flow.append(Paragraph(f'• {p}', BULLET))
    flow.append(Paragraph(
        '<b>Note:</b> public visitors never see expired events — the site '
        'filters them out client-side regardless of pruning. Pruning is '
        'queue housekeeping, not a visitor-facing concern.',
        BODY))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        '<b>When pruning runs:</b>', BODY))
    when_prune = [
        '<b>Automatically</b> on every scrape (right before merging fresh events)',
        '<b>Manually</b> via the 🧹 Prune Past button at the top of the Events Queue',
        '<b>Manually</b> via API — <font face="Courier">POST /api/events/prune</font>',
    ]
    for w in when_prune:
        flow.append(Paragraph(f'• {w}', BULLET))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        '<b>Action item — schedule the scraper:</b> the scraper does not run on '
        'a schedule out of the box. Set up a nightly run via Windows Task '
        'Scheduler (chamber laptop) or cron / systemd timer (VPS) so the '
        'queue stays current and pruning fires automatically. Without a '
        'schedule, expired events accumulate in the queue (still hidden '
        'from visitors) until someone clicks Update Now or 🧹 Prune Past.',
        BODY))

    flow.append(PageBreak())

    # ─────────── SECTION 4: AI CATEGORIZE ───────────────────────────────
    flow.append(Paragraph('4. AI Categorize (Claude Haiku)', H_TITLE))
    flow.append(Paragraph(
        'Cleans up tags, infers venue and area, scores quality. Optional but '
        'highly recommended for KVMR events.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('4a. One-time setup (do this once)', H1))
    setup_4a = [
        'Get an Anthropic API key at <b>console.anthropic.com</b>',
        'Set a $5/month spending cap in your Anthropic billing settings (safety net)',
        'Open <font face="Courier">scraper/config.py</font> in a text editor',
        'Add this line at the top: <font face="Courier">ANTHROPIC_API_KEY = "sk-ant-..."</font>',
        'Save the file. Restart the server.',
    ]
    for i, s in enumerate(setup_4a, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('4b. Run it', H1))
    run_steps = [
        'Open the admin Events Queue (Manage Database → Events Queue)',
        'Click the purple <b>🤖 AI Categorize</b> button',
        'A prompt asks how many events to process — leave blank for all, or enter a number for a test run',
        'Status bar shows "🤖 Categorizing…" for ~1-3 minutes',
        'When done, refresh the page — events show refined area, venue, tags',
    ]
    for i, s in enumerate(run_steps, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('4c. Cost', H1))
    cost_rows = [
        ['First-time bulk run (all ~1,240 events)', '~$0.80',        'one-time'],
        ['Weekly: only new events',                 '$0.10 - $0.30', '$0.40 - $1.20/mo'],
        ['Daily: only new events',                  '$0.02 - $0.05', '$0.60 - $1.50/mo'],
    ]
    flow.append(build_table(
        [['Run pattern', 'Per run', 'Monthly equiv']] + cost_rows,
        col_widths=[3.0*inch, 1.7*inch, 1.8*inch]))

    flow.append(Paragraph('4d. What if you don\'t want to use AI?', H1))
    flow.append(Paragraph(
        'Skip the API key setup. The button greys out to <font face="Courier">'
        '🤖 AI (no key)</font>. Everything else still works — events just keep '
        'their basic scraper-assigned tags.',
        BODY))

    flow.append(PageBreak())

    # ─────────── SECTION 5: ADD/EDIT EXPERIENCES ────────────────────────
    flow.append(Paragraph('5. Add or edit an experience', H_TITLE))
    flow.append(Paragraph(
        'The 164 curated experiences (Empire Mine, Lola Restaurant, B&amp;Bs, '
        'campgrounds, etc.) live in an inline-editable table.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('5a. Open the editor', H1))
    open_steps = [
        'Server running, browser open at http://localhost:5000',
        'Click <b>⚙ Manage Database</b> top right',
        'Stay on the <b>Experiences</b> tab (it\'s the default)',
    ]
    for i, s in enumerate(open_steps, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('5b. Edit a field', H1))
    edit_steps = [
        'Find the row by typing in the search input or sorting by clicking a column header',
        'Click directly on the cell you want to change (Name, Description, Hours, etc.)',
        'Type the new value',
        'Click <b>💾 Save All</b> in the toolbar — green flash confirms saved',
    ]
    for i, s in enumerate(edit_steps, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('5c. Add a new entry', H1))
    add_steps = [
        'Click <b>+ Add Experience</b> in the toolbar',
        'A new blank row appears at the bottom',
        'Fill in: Name, Description, Area, Type, Hours, Notes, Tags, Season, URL, Lat, Lng',
        'Click <b>💾 Save All</b>',
    ]
    for i, s in enumerate(add_steps, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))
    flow.append(Paragraph(
        '<b>Required fields for the entry to show:</b> Name, Area, Type, Tags. '
        'Everything else is optional but recommended.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('5d. Manage tags', H1))
    flow.append(Paragraph(
        'Click <b>🏷 Edit Tags</b> in the toolbar to open the tag taxonomy editor. '
        'Add, rename, or delete tags. Changes propagate to all filtering immediately.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('5e. Delete an entry', H1))
    flow.append(Paragraph(
        'Click the × button at the right end of the row. Confirms before deleting. '
        'Click 💾 Save All to persist.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('5f. Force a venue into a pill (override the filter)', H1))
    flow.append(Paragraph(
        'Sometimes a venue should appear under a specific filter pill '
        '(say, <b>Family</b> under the <b>Active</b> vibe) but the pill&apos;s '
        'regex doesn&apos;t catch it. Instead of changing the regex (which '
        'might affect other venues), add a per-venue override.',
        BODY))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('How to add an override', H1))
    ovr_steps = [
        'Open <b>⚙ Manage Database → Experiences</b>',
        'Find the venue row',
        'Click the <b>Pill Overrides</b> cell (next to Tags column)',
        'In the dropdown: check the pill you want to force-include. A small "override" badge appears.',
        'Click <b>💾 Save All</b>',
    ]
    for i, s in enumerate(ovr_steps, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('When to override vs. when to edit the regex', H1))
    flow.append(Paragraph(
        '<b>Override:</b> a single venue (or two) is missing from a pill, '
        'and the regex catches everything else correctly. Surgical fix.',
        BODY))
    flow.append(Paragraph(
        '<b>Edit the regex:</b> several venues with a shared name pattern '
        'are all missing — the regex is systematically wrong. Code change, '
        'ping the developer. (The regex lives in index.html&apos;s '
        'VIBE_PILLS constant.)',
        BODY))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('Reading the dropdown states', H1))
    state_rows = [
        ['Badge',     'Meaning',                                                 'Toggle?'],
        ['regex',     'Pill&apos;s regex already catches this venue automatically.', 'No (info only in v1)'],
        ['override',  'Admin manually force-included this venue. Bold + brown.',     'Yes — uncheck to remove'],
        ['(none)',    'Venue isn&apos;t in this pill. Check to add an override.',     'Yes — check to add'],
    ]
    flow.append(build_table(state_rows,
        col_widths=[0.9*inch, 3.4*inch, 2.2*inch], body_size=8.8))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('Stale overrides', H1))
    flow.append(Paragraph(
        'Over time, the regex may evolve to catch a venue that was previously '
        'overridden. The QA Scan (5g) flags these as <i>stale overrides</i> '
        '— safe-to-remove entries that aren&apos;t doing any work anymore. '
        'About once a year, open the QA Scan, look at the stale list, and '
        'clean up. Keeps the override list lean.',
        BODY))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('Events vs. venues', H1))
    flow.append(Paragraph(
        'The override system above is for <b>venues</b> only. For events '
        '(which are scraped fresh every cycle), the equivalent system is '
        '<i>per-source pattern rules</i> in <font face="Courier">scraper/'
        'scraper_overrides.json</font>. Edit that file when a scraper '
        'consistently mis-tags events the same way (e.g. "every event '
        'from NevadaCity.Rocks at Friar Tucks should carry the Music tag"). '
        'The JSON file&apos;s top has the schema docs.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('5g. Run a quality scan (monthly)', H1))
    flow.append(Paragraph(
        'The <b>🔍 QA Scan</b> tab inside <b>Manage Database</b> crawls every '
        'venue, every event, and every filter pill in about one second and '
        'reports problems that aren&apos;t obvious looking at one card at a '
        'time. Run it about once a month, or after any bulk data edit.',
        BODY))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph('How to run it', H1))
    qa_steps = [
        'Open <b>⚙ Manage Database</b> (top right)',
        'Click the <b>🔍 QA Scan</b> tab (last in the row)',
        'Click <b>▶ Run scan now</b> — takes about one second',
        'Review findings, fix what matters, re-run to confirm clean',
    ]
    for i, s in enumerate(qa_steps, 1):
        flow.append(Paragraph(f'{i}. {s}', BULLET))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph('What it checks', H1))
    qa_rows = [
        ['Severity', 'Check', 'What it catches'],
        ['🔴 Critical', 'Coordinate duplicates',
         'Two venues at the same lat/lng (~11m). Almost always the same physical place added twice. Pick the better entry, delete the other.'],
        ['🔴 Critical', 'Empty pills',
         'A filter pill whose match function returns zero venues. Either the regex is broken or the category went stale.'],
        ['🟡 Warning',  'Same-name venues',
         'Different IDs with the same normalized name. Could be a legitimate multi-location chain or a duplicate — admin decides.'],
        ['🟡 Warning',  'Pill false positives',
         'A pill matched a venue, but the venue&apos;s tags/type don&apos;t corroborate. Catches the kind of bug where the Tennis pill picked up a pickleball venue because the notes happened to cross-reference it.'],
        ['🟡 Warning',  'Over-matched venues',
         'A single venue lit by 8+ pills across the whole filter matrix. Usually means the venue&apos;s tag set is too broad — it&apos;ll surface in lots of unrelated filters.'],
        ['🟡 Warning',  'Cross-source event dupes',
         'Same date + title appearing under two scrapers (e.g. NCR + Friar Tuck&apos;s direct). Frontend display already dedups via Jaccard; admin queue may still show both rows.'],
        ['🟡 Warning',  'Unresolvable overrides',
         'A pill_in entry references a pill that no longer exists in VIBE_PILLS (renamed / deleted). Lists offending venues so the override can be fixed.'],
        ['🟢 Info',     'Stale overrides',
         'A pill_in override the regex now catches on its own — safe to remove. Helps prevent the override list from growing forever.'],
        ['🟢 Info',     'Tag orphans',
         'Tags present on venues but no pill ever references them. Either a typo (won&apos;t surface anywhere) or a category we forgot to add a pill for.'],
    ]
    flow.append(build_table(qa_rows,
        col_widths=[0.85*inch, 1.4*inch, 4.25*inch], body_size=8.8))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('Reading the report', H1))
    flow.append(Paragraph(
        'Findings group by severity. Each finding lists the affected venue '
        'IDs and a short explanation. Use the Experiences tab to jump to '
        'an offending row and fix it inline (then 💾 Save All). Re-run the '
        'scan; resolved findings drop off, anything still present is real.',
        BODY))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('Cadence', H1))
    flow.append(Paragraph(
        'The panel shows when the scan was last run on this device. After '
        '30 days the header goes red with "overdue (monthly cadence)" — '
        'that&apos;s the visual nudge. The scan is fast and free; run it '
        'whenever you&apos;ve done a batch edit or added several new '
        'experiences in one sitting.',
        BODY))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph('What it does <i>not</i> do', H1))
    qa_doesnt = [
        'Auto-fix anything — every finding is an admin decision (some "duplicates" are intentional, like Western Gateway Park entries for tennis vs. disc golf vs. pickleball, which are real separate facilities at one park).',
        'Persist findings across devices — the last-run timestamp is in browser localStorage. Different operator, different timer.',
        'Scan scraper output — events.json health is a separate scrape-time concern. The cross-source event check here only flags display-side redundancy.',
    ]
    for d in qa_doesnt:
        flow.append(Paragraph(f'• {d}', BULLET))

    flow.append(PageBreak())

    # ─────────── SECTION 6: UPDATE LIVE DEMO ────────────────────────────
    flow.append(Paragraph('6. Update the live GitHub Pages demo', H_TITLE))
    flow.append(Paragraph(
        'After scraping fresh events or editing experiences, push the updates '
        'so the public demo at <b>liammlrb-eng.github.io/nevada-county-experiences</b> '
        'reflects them.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('6a. The full refresh workflow', H1))
    flow.append(Preformatted("""# 1. Make sure server is running, then in admin panel:
#      • 🔄 Update Now (scrape fresh events)
#      • Wait for completion
#      • 🤖 AI Categorize (optional, recommended)
#      • Approve All (or review individually)

# 2. From PowerShell, push the updated files to GitHub:
cd "C:\\Users\\<your-user>\\Documents\\nevada-county-experience"
git add scraper_output/events.json
git add index.html                    # if you edited any experiences
git commit -m "events update — <date>"
git push

# 3. Wait ~1 minute. The live demo updates automatically.""", CODE))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('6b. What gets updated where', H1))
    where_rows = [
        ['Public events',                'scraper_output/events.json',  'Yes'],
        ['Curated experiences (161)',    'index.html',                  'Yes'],
        ['Itinerary suggestions (admin)', 'managed via Manage Database', 'Yes'],
        ['Scraper source URLs',          'scraper/sources.json',        'Yes'],
        ['API keys (Google, Anthropic)', 'scraper/config.py',           '<b>NO — gitignored</b>'],
        ['Local backups, cache files',   '.bak, __pycache__',           'NO — gitignored'],
    ]
    flow.append(build_table(
        [['What', 'Where it lives', 'Pushed to GitHub?']] + where_rows,
        col_widths=[2.2*inch, 2.5*inch, 1.8*inch]))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('6c. Cache caveat', H1))
    flow.append(Paragraph(
        'GitHub Pages caches static files for ~10 minutes by default. If a visitor '
        'has the page open while you push an update, they\'ll see the old data '
        'until they hard-refresh (<b>Ctrl+F5</b> on Windows / <b>Cmd+Shift+R</b> '
        'on Mac). New visitors get the latest immediately. Not a problem for '
        'tourism use — visitors don\'t refresh every minute.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('6d. Recommended cadence', H1))
    cadence_rows = [
        ['Just before peak season (Apr, Oct)', 'Full scrape + AI + manual review + push'],
        ['Weekly during season',                'Scrape + Approve All + push'],
        ['Monthly off-season',                  'Scrape + push'],
        ['After major content update',          'Edit experiences locally + push'],
    ]
    flow.append(build_table(
        [['When', 'What']] + cadence_rows,
        col_widths=[2.5*inch, 4.0*inch]))

    flow.append(PageBreak())

    # ─────────── SECTION 7: PUBLIC FEEDS ────────────────────────────────
    flow.append(Paragraph('7. Public feeds — what partners can subscribe to', H_TITLE))
    flow.append(Paragraph(
        'After every scrape, four feed files are regenerated and pushed to '
        'GitHub Pages. Anyone can subscribe — no API key, no rate limit. '
        'Share the URLs with chamber members, partner sites, and event organisers.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Paragraph('7a. The four feed URLs', H1))
    feed_rows = [
        ['iCal (.ics)',
         'feeds/events.ics',
         'Drop into Google Cal / Apple / Outlook as a subscribed calendar'],
        ['RSS 2.0',
         'feeds/events.rss',
         'Newsletters, partner sites, feed readers'],
        ['Events JSON',
         'feeds/events.json',
         'Developers building apps / dashboards / integrations'],
        ['Venues JSON',
         'feeds/venues.json',
         'The 170 curated experiences — stable IDs safe as foreign keys'],
    ]
    flow.append(build_table(
        [['Feed', 'Path under site root', 'For']] + feed_rows,
        col_widths=[1.2*inch, 1.8*inch, 3.5*inch], body_size=9))

    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        '<b>Site root:</b> <font face="Courier">'
        'https://liammlrb-eng.github.io/nevada-county-experiences/</font>',
        BODY))
    flow.append(Paragraph(
        '<b>Public docs page:</b> <font face="Courier">/feeds/</font> '
        '(under the site root) — subscribe instructions, license, JSON '
        'schema, example code. Send this URL to anyone asking "how do I '
        'get your events?"',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('7b. When the feeds refresh', H1))
    flow.append(Paragraph(
        'Automatically. <font face="Courier">generate_feeds.py</font> runs '
        'as the last step of every scrape (after link checking). It reads '
        '<font face="Courier">scraper_output/events.json</font> + the '
        'EXPERIENCES list and rewrites the four feed files under '
        '<font face="Courier">feeds/</font>. As soon as you push the '
        'scrape commit (Section 6), the new feeds go live within '
        '~1 minute (GitHub Pages rebuild). No manual step needed.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('7c. License — CC BY 4.0', H1))
    flow.append(Paragraph(
        'Subscribers may use, redistribute, remix, and build commercial '
        'products on the data provided they credit <b>Nevada County '
        'Experience</b> with a backlink to the homepage. Each event '
        'record also carries a <font face="Courier">source</font> field '
        'naming the original publisher (KVMR, NCAC, etc.) — partners '
        'should preserve that on display whenever practical so the '
        'original venue gets credit too.',
        BODY))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('7d. Sharing with a partner — what to send', H1))
    share_rows = [
        ['Newsletter editor wants our events',
         'Send the RSS URL. Their newsletter tool subscribes; events appear automatically.'],
        ['Partner site wants to embed our calendar',
         'Send the docs page (/feeds/) and the iCal URL. Most CMS calendar widgets accept an .ics URL.'],
        ['Member venue subscribing in their Google Cal',
         'Send the iCal URL. Google Cal → Other Calendars → + → From URL → paste.'],
        ['Developer / integrator',
         'Send the docs page (/feeds/) — it has the JSON schema, examples, and license notes.'],
        ['Someone wants venues on a map',
         'Send the venues.json URL. Each record has lat/lng, name, blurb, tags.'],
    ]
    flow.append(build_table(
        [['Audience / ask', 'What to send']] + share_rows,
        col_widths=[2.8*inch, 3.7*inch], body_size=9))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('7e. What\'s in the feeds (filtering rules)', H1))
    flow.append(Paragraph(
        'The feeds mirror what the public site shows:', BODY))
    filter_rules = [
        '<b>Only approved events</b> — <font face="Courier">'
            'status = "approved"</font>. Pending and dismissed never leave the site.',
        '<b>Only future events</b> — anything whose end date is before today drops off automatically.',
        '<b>AI fields preferred</b> — <font face="Courier">ai_area</font>, '
            '<font face="Courier">ai_venue</font>, <font face="Courier">'
            'ai_summary</font>, <font face="Courier">ai_tags</font> are '
            'used when present; raw scraper fields are the fallback.',
        '<b>Descriptions capped</b> at 600 characters in the JSON feed (full description on the source URL).',
        '<b>Stable IDs</b> — every event has a 12-char hash that survives re-scrapes. Safe to use as a key.',
    ]
    for r in filter_rules:
        flow.append(Paragraph(f'• {r}', BULLET))

    flow.append(PageBreak())

    # ─────────── SECTION 8: TROUBLESHOOTING ─────────────────────────────
    flow.append(Paragraph('8. Troubleshooting', H_TITLE))
    flow.append(Paragraph(
        'Most common issues and how to fix them.',
        H_SUB))
    flow.append(section_rule())

    tbl_rows = [
        ['Server won\'t start: "python is not recognized"',
         'Python isn\'t in your PATH. Reinstall Python from python.org and check "Add Python to PATH" during install. Or use the start_server.bat launcher (it auto-finds Python).'],
        ['Server won\'t start: "Address already in use"',
         'Port 5000 is busy. Either close the previous server window, or run: <font face="Courier">python server.py --port 8080</font> and use http://localhost:8080.'],
        ['Site loads but Events tab is empty',
         'On the local server: open Manage Database → Events Queue → click Approve All on pending events. On GitHub Pages: scraper_output/events.json may not be committed — run section 6a.'],
        ['🔄 Update Now hangs forever',
         'Selenium/Chromium issue. Close the browser, restart server, try again. If persistent, try a single source: <font face="Courier">python scraper\\event_scraper.py --site "Nevada City Chamber"</font> from PowerShell to see the error.'],
        ['🤖 AI Categorize button is greyed out',
         'No Anthropic API key set. See Section 4a. Restart the server after adding the key.'],
        ['🤖 AI Categorize fails with "API error 401"',
         'Invalid API key. Check for typos in scraper/config.py. Generate a new key at console.anthropic.com if needed.'],
        ['🤖 AI Categorize fails with "rate limit"',
         'Hitting Anthropic API limits. Lower batch size (edit ai_categorize.py: --batch-size 5) or wait an hour and retry.'],
        ['Edits aren\'t saving',
         'Click the green 💾 Save All button after editing — auto-save isn\'t enabled for the admin table.'],
        ['Lost an experience after deleting',
         'Browser localStorage keeps a recent backup. Open browser DevTools (F12) → Application → Local Storage → key starting with "ncexp:" — restore manually if needed. Best practice: backup events.json + index.html before bulk edits.'],
        ['GitHub Pages not updating after push',
         'Wait 2 minutes (deploy time). Then hard-refresh (Ctrl+F5). If still stale, check repo Settings → Pages for any deploy errors.'],
        ['"Permission denied" pushing to GitHub',
         'Your GitHub credentials expired or you don\'t have write access. In PowerShell: <font face="Courier">git config --global credential.helper manager</font> then retry — Windows will prompt for login.'],
    ]
    flow.append(build_table(
        [['Symptom', 'Fix']] + tbl_rows,
        col_widths=[2.2*inch, 4.3*inch], body_size=8.8))

    flow.append(PageBreak())

    # ─────────── SECTION 9: FILE MAP ────────────────────────────────────
    flow.append(Paragraph('9. File map — where things live', H_TITLE))
    flow.append(Paragraph(
        'Quick reference for what\'s in the project folder.',
        H_SUB))
    flow.append(section_rule())

    flow.append(Preformatted("""nevada-county-experience/
├── index.html                     ← The whole frontend (everything visitors see)
├── server.py                      ← Flask web server (runs locally)
├── start_server.bat               ← Double-click to start the server
├── scraper/
│   ├── event_scraper.py          ← Main scraper (orchestrates all sources)
│   ├── ai_categorize.py          ← AI cleanup (Claude Haiku)
│   ├── auto_tagger.py            ← Keyword-based pre-tagging
│   ├── generate_feeds.py         ← Builds feeds/ outputs (runs after each scrape)
│   ├── config.py                 ← API KEYS — never committed to GitHub
│   ├── sources.json              ← Scraper source URL list
│   └── site_scrapers/            ← One file per source (or per platform)
│       ├── base.py               ← Shared EventScraper class + RSS autodiscovery
│       ├── kvmr.py               ← Tribe Events RSS
│       ├── ncac_calendar.py     ← Trumba JSON
│       ├── eventbrite_nevada.py ← React via Selenium
│       ├── nevada_city_chamber.py
│       ├── gv_chamber.py
│       ├── the_union.py
│       ├── center_for_arts.py
│       ├── miners_foundry.py
│       ├── fairgrounds.py        ← Saffire JSONP (Nevada County Fairgrounds)
│       ├── tribe_events.py       ← The Events Calendar REST (Crazy Horse)
│       ├── woocommerce.py        ← WooCommerce Store API (Curious Forge)
│       ├── shopify.py            ← Shopify products.json (Wolf Craft)
│       ├── squarespace_events.py ← Squarespace events JSON (Golden Era)
│       ├── nevada_theatre.py     ← MEC plugin (disabled — see event_scraper.py)
│       ├── go_nevada.py          ← disabled (Cloudflare 403s)
│       └── go_nevada_festivals.py ← disabled (Cloudflare 403s)
├── scraper_output/
│   ├── events.json               ← The live event database (committed)
│   ├── candidates.json           ← Scraper debug data (gitignored)
│   └── snapshots/                ← Rendered HTML for selector debug (gitignored)
├── feeds/
│   ├── index.html                ← Public docs page for partners (/feeds/)
│   ├── events.ics                ← iCal feed — calendar app subscribe
│   ├── events.rss                ← RSS 2.0 — newsletters, partner sites
│   ├── events.json               ← JSON — developer integrations
│   └── venues.json               ← The 170 curated experiences
├── demo_pitch.pdf                ← County presentation deck
├── operator_guide.pdf            ← This file
├── generate_demo_pdf.py          ← Source for demo_pitch.pdf
├── generate_operator_guide.py    ← Source for this file
├── CLAUDE.md                     ← Project context for future contributors
├── .gitignore                    ← What never gets committed""", CODE))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('8a. The four files you\'ll touch most', H1))
    touch_rows = [
        ['index.html',                   'Edit experiences via Manage Database (admin panel) — never edit by hand'],
        ['scraper_output/events.json',   'Updated automatically by scraping — commit + push after scrapes'],
        ['scraper/config.py',            'API keys — edit once during setup, never commit'],
        ['scraper/sources.json',         'Add/disable scraper sources — edit via 🔗 Scraper Sources tab'],
    ]
    flow.append(build_table(
        [['File', 'When you touch it']] + touch_rows,
        col_widths=[2.3*inch, 4.2*inch]))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph('8b. Logs &amp; diagnostics', H1))
    flow.append(Paragraph(
        'When something\'s wrong, look here:', BODY))
    log_rows = [
        ['Server console window',     'Live request log + Python errors. Keep visible while debugging.'],
        ['Browser DevTools console',  'F12 → Console tab. Frontend errors and warnings.'],
        ['scraper_output/snapshots/', 'When a scraper fails: <font face="Courier">python scraper/event_scraper.py --discover --site "Source Name"</font> saves the rendered HTML here so you can inspect what the scraper saw.'],
    ]
    flow.append(build_table(
        [['Where', 'What it tells you']] + log_rows,
        col_widths=[2.2*inch, 4.3*inch]))

    flow.append(PageBreak())

    # ─────────── SECTION 10: ANNUAL TASKS + EMERGENCY ────────────────────
    flow.append(Paragraph('10. Annual tasks &amp; emergency contacts', H_TITLE))
    flow.append(section_rule())

    flow.append(Paragraph('10a. Once-a-year checklist', H1))
    annual = [
        '<b>Spring</b>: walk through every experience entry — verify hours, URLs, and that the venue still exists. Use Manage Database → Experiences. Budget 4-6 hours.',
        '<b>Spring</b>: review all 9 vibes — are the photos still working? Are the taglines still accurate? Edit if needed.',
        '<b>Summer</b>: pre-festival-season scrape + AI categorize + manual review. Push to GitHub.',
        '<b>Fall</b>: review the Suggested Experiences — are the published itineraries still relevant? Update photos and stops.',
        '<b>Anytime</b>: domain renewal — set a calendar reminder 90 days before expiry.',
        '<b>Anytime</b>: backup test — once a year, restore events.json from a tarball backup to a test folder, verify the file loads.',
    ]
    for a in annual:
        flow.append(Paragraph(f'• {a}', BULLET))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('10b. Emergency contact ladder', H1))
    flow.append(Paragraph(
        'When something breaks and you need help, in order:', BODY))
    contact = [
        '<b>1. Try Section 7 (Troubleshooting)</b> first — covers 80% of issues',
        '<b>2. Check the GitHub repo Issues tab</b> — has anyone reported this?',
        '<b>3. Original developer / contractor</b> — keep their email pinned',
        '<b>4. County IT</b> — for server-level / hosting issues',
        '<b>5. Anthropic support</b> — for AI billing / API key issues (support@anthropic.com)',
        '<b>6. Hosting provider support</b> — DigitalOcean / Linode / etc., for server downtime',
    ]
    for c in contact:
        flow.append(Paragraph(f'• {c}', BULLET))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('10c. Before calling for help — gather this', H1))
    gather_rows = [
        ['What you tried',                  'List the steps that led to the problem'],
        ['Exact error text',                'Copy-paste from console window or browser. Screenshot if needed.'],
        ['When it started',                 'After a scrape? After a push? After Windows update?'],
        ['Which environment',               'Local server? GitHub Pages? Just the admin panel?'],
        ['Last successful action',          '"Scrape worked yesterday at 3 PM" — helpful baseline'],
    ]
    flow.append(build_table(
        [['Info', 'Why it helps']] + gather_rows,
        col_widths=[2.0*inch, 4.5*inch]))

    flow.append(Spacer(1, 18))
    flow.append(Paragraph('Final note', H1))
    flow.append(Paragraph(
        '<i>"Most problems with this platform aren\'t crises — they\'re small '
        'gaps in process. A scrape fails, a tag goes stale, a photo URL breaks. '
        'The system is designed to keep working even when individual pieces '
        'don\'t. Don\'t panic; check Section 7; ask for help if needed."</i>',
        QUOTE))

    # ─────────── BUILD ──────────────────────────────────────────────────
    doc.build(flow,
        onFirstPage=page_footer,
        onLaterPages=page_footer)
    print(f'Wrote: {out}')
    return out


def _mirror_to_pitch_resources(path):
    """Keep pitch_resources/ snapshot in sync."""
    import shutil
    mirror_dir = Path(__file__).resolve().parent / 'pitch_resources'
    if mirror_dir.is_dir() and Path(path).is_file():
        mirror = mirror_dir / Path(path).name
        shutil.copy2(path, mirror)
        print(f'Mirrored: {mirror}')


if __name__ == '__main__':
    out = build()
    _mirror_to_pitch_resources(out)

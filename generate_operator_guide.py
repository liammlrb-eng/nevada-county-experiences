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
        ['Stop the server',                      'Section 1c',                  '5 sec'],
        ['Something\'s broken',                  'Section 7 (Troubleshooting)', 'varies'],
        ['Where do files live?',                 'Section 8 (File map)',        'reference'],
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
        'Pulls fresh events from KVMR, Eventbrite, NC Chamber, GV Chamber, '
        'and other sources. Run weekly or whenever you want fresh data.',
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
        ['KVMR',              'Tribe Events RSS feed', '~430 events / 6-month window'],
        ['Eventbrite Nevada', 'Headless Chrome',       '~10 events'],
        ['NC Chamber',        'Static HTML page',      '~10 events'],
        ['GV Chamber',        'Elementor page',        '~5 events'],
        ['The Union',         'RSS feed',              'Varies'],
        ['Go Nevada',         'Headless Chrome (often Cloudflare-blocked)', 'Varies'],
    ]
    flow.append(build_table(
        [['Source', 'Method', 'Typical volume']] + src_rows,
        col_widths=[1.6*inch, 2.4*inch, 2.5*inch]))

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
    flow.append(Paragraph('3d. Auto-pruning', H1))
    flow.append(Paragraph(
        'The system automatically removes:', BODY))
    prune = [
        'Pending or approved events whose date has passed (next scrape)',
        'Dismissed events older than 60 days (long enough to prevent re-import)',
    ]
    for p in prune:
        flow.append(Paragraph(f'• {p}', BULLET))
    flow.append(Paragraph(
        'You can trigger a manual prune from the API: '
        '<font face="Courier">POST /api/events/prune</font> '
        '(or just wait for the next scrape — happens automatically).',
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
        ['First-time bulk run (all 460 events)', '~$0.30',           'one-time'],
        ['Weekly: only new events',              '$0.04 - $0.13',    '$0.20-$0.50/mo'],
        ['Daily: only new events',               '$0.01 - $0.02',    '$0.30-$0.60/mo'],
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
        'The 161 curated experiences (Empire Mine, Lola Restaurant, B&amp;Bs, '
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

    # ─────────── SECTION 7: TROUBLESHOOTING ─────────────────────────────
    flow.append(Paragraph('7. Troubleshooting', H_TITLE))
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

    # ─────────── SECTION 8: FILE MAP ────────────────────────────────────
    flow.append(Paragraph('8. File map — where things live', H_TITLE))
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
│   ├── config.py                 ← API KEYS — never committed to GitHub
│   ├── sources.json              ← Scraper source URL list
│   └── site_scrapers/            ← One file per source
│       ├── kvmr.py
│       ├── eventbrite_nevada.py
│       ├── nevada_city_chamber.py
│       ├── gv_chamber.py
│       ├── the_union.py
│       └── ...
├── scraper_output/
│   ├── events.json               ← The live event database (committed)
│   ├── candidates.json           ← Scraper debug data (gitignored)
│   └── snapshots/                ← Rendered HTML for selector debug (gitignored)
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

    # ─────────── SECTION 9: ANNUAL TASKS + EMERGENCY ─────────────────────
    flow.append(Paragraph('9. Annual tasks &amp; emergency contacts', H_TITLE))
    flow.append(section_rule())

    flow.append(Paragraph('9a. Once-a-year checklist', H1))
    annual = [
        '<b>Spring</b>: walk through every experience entry — verify hours, URLs, and that the venue still exists. Use Manage Database → Experiences. Budget 4-6 hours.',
        '<b>Spring</b>: review all 9 vibes — are the photos still working? Are the taglines still accurate? Edit if needed.',
        '<b>Summer</b>: pre-festival-season scrape + AI categorize + manual review. Push to GitHub.',
        '<b>Fall</b>: review the Suggested Itineraries — are they still relevant? Update photos and stops.',
        '<b>Anytime</b>: domain renewal — set a calendar reminder 90 days before expiry.',
        '<b>Anytime</b>: backup test — once a year, restore events.json from a tarball backup to a test folder, verify the file loads.',
    ]
    for a in annual:
        flow.append(Paragraph(f'• {a}', BULLET))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph('9b. Emergency contact ladder', H1))
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
    flow.append(Paragraph('9c. Before calling for help — gather this', H1))
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


if __name__ == '__main__':
    build()

"""
Generate demo_pitch.pptx — a focused 15-slide deck for the county presentation.

Output is .pptx, which:
  - Opens directly in Google Slides (Drive → upload → "Open with Google Slides")
  - Opens in PowerPoint, Keynote, LibreOffice Impress
  - Stays editable; all text/colors live in the source script

Run:   python generate_slides.py
Out:   demo_pitch.pptx

ORGANIZATION
============
Each slide is a self-contained builder function (slide_title, slide_strategic_insight,
slide_what_this_is, etc.) that takes a slide object and adds shapes/text to it.
The narrative order is defined in SLIDE_ORDER at the bottom — reordering the deck
is just reordering that list.

Page footers (X / N) and TOTAL are computed automatically from SLIDE_ORDER, so
nothing breaks when slides move.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pathlib import Path

# ── Brand palette (matches the PDF & site) ──────────────────────────────
BROWN  = RGBColor(0x5C, 0x3A, 0x1F)
GOLD   = RGBColor(0xC9, 0xA8, 0x4C)
GOLD_LIGHT = RGBColor(0xE8, 0xC9, 0x6A)
SLATE  = RGBColor(0x4A, 0x55, 0x68)
FOG    = RGBColor(0xF5, 0xEF, 0xE2)
DARK   = RGBColor(0x1E, 0x15, 0x08)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
RULE   = RGBColor(0xD4, 0xC9, 0xB0)

# 16:9 widescreen
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]


def add_text(slide, text, left, top, width, height, *,
             size=18, bold=False, color=DARK, align=PP_ALIGN.LEFT,
             font='Calibri', anchor=MSO_ANCHOR.TOP, italic=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return box


def add_rect(slide, left, top, width, height, fill, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.5)
    shp.shadow.inherit = False
    return shp


def add_gold_rule(slide, left, top, width):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Pt(2))
    shp.fill.solid()
    shp.fill.fore_color.rgb = GOLD
    shp.line.fill.background()


def slide_header(slide, title, subtitle=None):
    """Standard top-of-slide header: title, gold rule, optional subtitle."""
    add_text(slide, title, Inches(0.6), Inches(0.4), Inches(12.1), Inches(0.7),
             size=32, bold=True, color=BROWN, font='Calibri')
    add_gold_rule(slide, Inches(0.6), Inches(1.18), Inches(12.1))
    if subtitle:
        add_text(slide, subtitle, Inches(0.6), Inches(1.32), Inches(12.1), Inches(0.5),
                 size=14, color=SLATE, italic=True)


def page_footer(slide, page_num, total):
    """Footer with page number + brand line."""
    add_text(slide, 'Western Nevada County Experience',
             Inches(0.6), Inches(7.1), Inches(8), Inches(0.3),
             size=9, color=SLATE)
    add_text(slide, f'{page_num} / {total}',
             Inches(11.5), Inches(7.1), Inches(1.2), Inches(0.3),
             size=9, color=SLATE, align=PP_ALIGN.RIGHT)
    add_gold_rule(slide, Inches(0.6), Inches(7.06), Inches(12.1))


def add_bullets(slide, items, left, top, width, height, *,
                size=14, color=DARK, line_spacing=1.4, bullet_color=GOLD,
                scenario_size=None, scenario_color=None):
    """
    Each item is either a string OR a (text, scenario) tuple.
    Strings render as a single bulleted line.
    Tuples render the item, then an italic gold sub-line "↳ scenario"
    showing how the feature is used in practice.

    scenario_size  defaults to size - 2
    scenario_color defaults to BROWN (the brand brown)
    """
    if scenario_size is None:
        scenario_size = max(size - 2, 8)
    if scenario_color is None:
        scenario_color = BROWN
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)

    para_idx = 0
    for item in items:
        # Allow either plain string or (text, scenario) tuple
        if isinstance(item, tuple):
            text, scenario = item
        else:
            text, scenario = item, None

        # Bullet line
        p = tf.paragraphs[0] if para_idx == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        b = p.add_run()
        b.text = '• '
        b.font.size = Pt(size + 2)
        b.font.bold = True
        b.font.color.rgb = bullet_color
        b.font.name = 'Calibri'
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.name = 'Calibri'
        p.line_spacing = line_spacing
        if para_idx > 0:
            p.space_before = Pt(6 if scenario is None else 4)
        para_idx += 1

        # Optional scenario sub-line: italic, indented, smaller
        if scenario:
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.LEFT
            sr = p2.add_run()
            sr.text = '       ↳  ' + scenario
            sr.font.size = Pt(scenario_size)
            sr.font.italic = True
            sr.font.color.rgb = scenario_color
            sr.font.name = 'Calibri'
            p2.line_spacing = 1.1
            p2.space_before = Pt(0)
            para_idx += 1
    return box


def add_stat_card(slide, left, top, width, height, big_text, label):
    """Featured number + label, like a metric tile."""
    add_rect(slide, left, top, width, height, FOG, RULE)
    # Big number
    add_text(slide, big_text, left, top + Inches(0.2), width, Inches(0.9),
             size=44, bold=True, color=GOLD, align=PP_ALIGN.CENTER, font='Calibri')
    # Label
    add_text(slide, label, left, top + Inches(1.05), width, Inches(0.5),
             size=11, color=SLATE, align=PP_ALIGN.CENTER, font='Calibri')


def two_col_table(slide, headers, rows, top, *, left_w=4.5, right_w=8.0,
                  header_size=11, body_size=10, row_height=0.5,
                  scenario_size=None):
    """
    Simple 2-column table without using actual table shape (more layout control).
    Each row is either a 2-tuple (left, right) or a 3-tuple (left, right, scenario).
    A scenario renders as a second italic line in the right column.
    """
    if scenario_size is None:
        scenario_size = max(body_size - 2, 8)
    left  = Inches(0.6)
    col2  = left + Inches(left_w)
    # Header row
    add_rect(slide, left, top, Inches(left_w + right_w), Inches(0.42), FOG)
    add_text(slide, headers[0], left + Inches(0.1), top + Inches(0.05),
             Inches(left_w - 0.15), Inches(0.32),
             size=header_size, bold=True, color=BROWN)
    add_text(slide, headers[1], col2 + Inches(0.1), top + Inches(0.05),
             Inches(right_w - 0.15), Inches(0.32),
             size=header_size, bold=True, color=BROWN)
    add_gold_rule(slide, left, top + Inches(0.42), Inches(left_w + right_w))
    y = top + Inches(0.46)
    for i, row in enumerate(rows):
        if len(row) == 3:
            a, b, scenario = row
        else:
            a, b = row
            scenario = None

        if i % 2 == 0:
            add_rect(slide, left, y, Inches(left_w + right_w),
                     Inches(row_height), RGBColor(0xFB, 0xF7, 0xEE))

        # Left column — vertically centered when row is tall
        add_text(slide, a, left + Inches(0.1), y + Inches(0.05),
                 Inches(left_w - 0.15), Inches(row_height - 0.05),
                 size=body_size, color=DARK,
                 anchor=MSO_ANCHOR.MIDDLE if scenario else MSO_ANCHOR.TOP)

        if scenario:
            # Right column — explanation on top, scenario in italic below
            half = (row_height - 0.05) / 2
            add_text(slide, b, col2 + Inches(0.1), y + Inches(0.04),
                     Inches(right_w - 0.15), Inches(half),
                     size=body_size, color=DARK)
            add_text(slide, '↳  ' + scenario,
                     col2 + Inches(0.1), y + Inches(half + 0.04),
                     Inches(right_w - 0.15), Inches(half),
                     size=scenario_size, color=BROWN, italic=True)
        else:
            add_text(slide, b, col2 + Inches(0.1), y + Inches(0.05),
                     Inches(right_w - 0.15), Inches(row_height - 0.05),
                     size=body_size, color=DARK)
        y += Inches(row_height)


# ═══════════════════════════ SLIDE BUILDERS ═══════════════════════════════
# Each function takes a slide object and adds content to it (no page_footer,
# no add_slide call — those happen in the main loop). Order is defined by
# SLIDE_ORDER below.

def slide_title(s):
    # Brown band on left
    add_rect(s, 0, 0, Inches(4.5), SLIDE_H, BROWN)
    # Gold accent
    add_rect(s, Inches(4.5), 0, Inches(0.08), SLIDE_H, GOLD)
    add_text(s, 'Western\nNevada\nCounty',
             Inches(0.6), Inches(2.2), Inches(3.7), Inches(2.5),
             size=44, bold=True, color=GOLD_LIGHT, font='Calibri')
    add_text(s, 'Experience Finder',
             Inches(0.6), Inches(4.4), Inches(3.7), Inches(0.7),
             size=22, color=WHITE, italic=True, font='Calibri')
    add_text(s, 'Visitor planning platform — county pitch deck',
             Inches(4.9), Inches(3.0), Inches(7.8), Inches(0.6),
             size=20, color=BROWN, bold=True)
    add_gold_rule(s, Inches(4.9), Inches(3.6), Inches(7.5))
    add_text(s,
        'A purpose-built tourism platform combining 161 curated experiences '
        'with 460+ live-scraped events. Privacy-first, opt-in, no tracking.',
        Inches(4.9), Inches(3.85), Inches(7.8), Inches(2.5),
        size=14, color=SLATE)


def slide_strategic_insight(s):
    """The lodging-revenue framing — leads the deck so everything else has context."""
    slide_header(s, 'The strategic insight',
        'What sets this apart from a generic tourism site.')

    add_text(s,
        'Most tourism sites optimize for visits to the site. The right metric is '
        'lodging bookings driven by the site. Those are different optimization targets.',
        Inches(0.6), Inches(1.85), Inches(12.1), Inches(1.0),
        size=15, color=DARK)

    add_bullets(s, [
        ('Day-by-day itinerary view structurally surfaces the "where do I sleep?" question',
         'Visitor sees Day 2 has no hotel and books one before leaving the page.'),
        ('"Find Lodging" CTA at the top of every itinerary — booking always one click away',
         'No hunting for a button — booking decision is visible on every itinerary view.'),
        ('Empty lodging slots create a visual gap that drives the booking decision',
         'That blank Day 2 stay tile is psychologically jarring; the visitor fills it.'),
        ('New items default to the latest day — no day-1 pile-up; trip naturally fills out',
         'Adding stops naturally extends the trip rather than cramming Day 1.'),
        ('Print view goes long-form per day — visitors who print, follow it',
         'Couple prints the itinerary; the same Day 1 / Day 2 structure follows on paper.'),
        ('Smart suggestions are tag + geography aware — clusters keep visitors close to lodging',
         'After Holbrooke Hotel goes in, suggestions cluster around Mill Street.'),
    ], Inches(0.6), Inches(2.85), Inches(12.1), Inches(3.5),
       size=11, line_spacing=1.2, scenario_size=9)

    # Closing quote
    add_rect(s, Inches(0.6), Inches(6.2), Inches(12.1), Inches(0.7),
             RGBColor(0xFB, 0xF7, 0xEE), GOLD)
    add_text(s,
        '"Convince a visitor to add one more night and you double or triple local revenue."',
        Inches(0.7), Inches(6.25), Inches(11.9), Inches(0.6),
        size=13, italic=True, color=BROWN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def slide_what_this_is(s):
    slide_header(s, 'What this is',
        'A tourism platform for Western Nevada County — Gold Country foothills.')

    # Body intro
    add_text(s,
        'A purpose-built tourism platform for Western Nevada County — '
        'centered on Nevada City and Grass Valley, with full coverage of Penn Valley, '
        'North San Juan, Rough & Ready, Washington, Chicago Park, Smartsville, and '
        'adjacent Colfax. The platform combines curated places with live-scraped '
        'events, so visitors discover what to do AND when it\'s actually happening.',
        Inches(0.6), Inches(1.95), Inches(12.1), Inches(1.4),
        size=13, color=DARK)

    # Stat cards
    add_stat_card(s, Inches(0.6),  Inches(3.5), Inches(2.85), Inches(1.6), '161',  'Curated experiences\nacross 11 communities')
    add_stat_card(s, Inches(3.65), Inches(3.5), Inches(2.85), Inches(1.6), '460+', 'Live events from\n6 sources')
    add_stat_card(s, Inches(6.7),  Inches(3.5), Inches(2.85), Inches(1.6), '9',    'Themed vibes\nfor discovery')
    add_stat_card(s, Inches(9.75), Inches(3.5), Inches(2.85), Inches(1.6), '$5–$20', 'Typical\nmonthly cost')

    # Below: scope footer
    add_text(s,
        'Geographic scope: Western Nevada County (Gold Country foothills) + adjacent Colfax.\n'
        'Truckee and Sierra-side communities are out of scope for this build.',
        Inches(0.6), Inches(5.4), Inches(12.1), Inches(0.7),
        size=11, color=SLATE, italic=True)


def slide_discovery(s):
    slide_header(s, 'How visitors discover',
        'Multiple paths to "I found it" — works for browse-mode and date-mode visitors.')

    two_col_table(s, ['Discovery path', 'What it does'], [
        ('Themed vibes (9 cards)',
         'Historic · Arts · Hands-On · Foodie · Active · Relaxed · Wellness · Family · Festivals',
         'No-plan visitor taps "Foodie" — relevant cards instantly filter in.'),
        ('Vibe-level pills',
         'Pick Foodie → narrow to Restaurants / Wineries / Markets / Bakeries / Food Events',
         'Foodie visitor switches to "Wineries only" without leaving the vibe.'),
        ('Category dropdown + sub-pills',
         'Lodging → Hotels / B&Bs / Glamping / Campgrounds / RV  (and more)',
         'Family of four picks Lodging → B&Bs to find character stays over chains.'),
        ('Activity tags',
         'Hiking · Biking · Swimming · Fishing · Boating · Running on every relevant card',
         'Mountain biker scrolls and immediately spots cards tagged "Biking".'),
        ('Date filter',
         'All Future (default) · Today · Weekend · Week — auto-clears summer-only items in winter',
         'One-tap "Weekend" — only Sat/Sun events remain across every vibe.'),
        ('Area filter',
         'County-wide events show for any local area; city events filter normally',
         'Penn Valley resident filters out Nevada City clutter for a local night out.'),
        ('Tag-aware Smart Suggestions',
         '"More to Explore" panel in the itinerary — geographic + tag scoring',
         'After Empire Mine goes in, the panel surfaces Holbrooke Hotel 0.4 mi away.'),
    ], Inches(1.75), left_w=3.4, right_w=8.7, body_size=10, row_height=0.65,
       scenario_size=8)


def slide_itinerary(s):
    slide_header(s, 'Day-by-day itinerary builder',
        'Visitors think in nights, not stops — the planner reflects that.')

    # Left: feature list
    add_bullets(s, [
        ('Each day has its own card with a numbered header and calendar date',
         'Visitor sees "Day 1: Sat May 17" instead of an undifferentiated stop list.'),
        ('Per-day "Tonight\'s Stay" lodging slot — empty slots prompt for booking',
         'Empty Day 2 stay tile reminds the visitor they haven\'t booked Sunday yet.'),
        ('Drag-free move-between-days dropdown on every item',
         'Spouse on phone moves Friday\'s hike to Saturday in two taps.'),
        ('Add Day → returns visitor to browse mode for the new day',
         'Tap "Add Day," land on cards to pick Day 3 activities — flow continues.'),
        ('Find Lodging button at top of itinerary jumps directly to lodging filter',
         'Six stops in but no hotel — one tap surfaces every nearby B&B.'),
        ('Events go INTO the itinerary first; the visitor decides what to commit to',
         'Bluegrass concert tile lands in My Itinerary, not on KVMR\'s site.'),
        ('15-min add → opt-in save → survives tab close + browser restart',
         'Browser closes, phone reboots — itinerary still there next morning.'),
        ('Share link via native phone share sheet, email, text, or copy URL',
         'Visitor texts the URL to spouse: "this is what I\'m thinking."'),
    ], Inches(0.6), Inches(1.75), Inches(7.0), Inches(5.3),
       size=11, line_spacing=1.2, scenario_size=9)

    # Right: visual mock representation
    mock_x = Inches(7.9); mock_y = Inches(1.85); mock_w = Inches(4.8); mock_h = Inches(5.0)
    add_rect(s, mock_x, mock_y, mock_w, mock_h, RGBColor(0xFB, 0xF7, 0xEE), RULE)
    add_text(s, '2 stops · 2 days / 1 night',
             mock_x + Inches(0.2), mock_y + Inches(0.15), mock_w - Inches(0.4), Inches(0.4),
             size=11, color=SLATE, italic=True)
    # Day 1 mock
    add_rect(s, mock_x + Inches(0.25), mock_y + Inches(0.6), mock_w - Inches(0.5), Inches(2.0),
             WHITE, GOLD)
    add_text(s, 'DAY 1 of 2   Sat, Jun 14',
             mock_x + Inches(0.4), mock_y + Inches(0.7), mock_w - Inches(0.6), Inches(0.3),
             size=11, bold=True, color=BROWN)
    add_text(s, '💤 TONIGHT\'S STAY\nHolbrooke Hotel · Grass Valley',
             mock_x + Inches(0.4), mock_y + Inches(1.1), mock_w - Inches(0.6), Inches(0.7),
             size=10, color=DARK)
    add_text(s, '1.  Empire Mine State Historic Park\n2.  Lola Restaurant',
             mock_x + Inches(0.4), mock_y + Inches(1.85), mock_w - Inches(0.6), Inches(0.7),
             size=10, color=DARK)
    # Day 2 mock
    add_rect(s, mock_x + Inches(0.25), mock_y + Inches(2.75), mock_w - Inches(0.5), Inches(1.6),
             WHITE, GOLD)
    add_text(s, 'DAY 2 of 2   Sun, Jun 15',
             mock_x + Inches(0.4), mock_y + Inches(2.85), mock_w - Inches(0.6), Inches(0.3),
             size=11, bold=True, color=BROWN)
    add_text(s, '💤  No lodging picked for tonight  →  [Find Lodging]',
             mock_x + Inches(0.4), mock_y + Inches(3.2), mock_w - Inches(0.6), Inches(0.5),
             size=9, italic=True, color=SLATE)
    add_text(s, '📅  Father\'s Day Bluegrass — Sat 7:00 PM',
             mock_x + Inches(0.4), mock_y + Inches(3.7), mock_w - Inches(0.6), Inches(0.5),
             size=10, color=GOLD)


def slide_demo_flow(s):
    slide_header(s, 'Let me show you',
        'A live demo: visitor planning a romantic November weekend in Western Nevada County.')

    acts = [
        ('Act 1 · 2 min',  'Set the scene — couple from Sacramento, click "This Weekend" + Festivals vibe'),
        ('Act 2 · 90 sec', 'Layer in Relaxed vibe + Lodging category + B&B sub-pill — real Victorian B&Bs surface'),
        ('Act 3 · 2 min',  'Build the weekend — Cornish Christmas + Holbrooke Hotel + Empire Mine + Lola Restaurant. Open My Itinerary — Smart Suggestions appear with "0.4 mi away" labels. Map view + Print + Share link.'),
        ('Act 4 · 90 sec', 'Behind the scenes — admin Events Queue, Approve All, AI Categorize button, Scraper Sources tab'),
        ('Act 5 · 60 sec', 'Close the value props — time saved, local visibility, privacy, no vendor lock-in, AI integration, low maintenance'),
    ]
    two_col_table(s, ['Act', 'What happens'], acts,
                  Inches(1.85), left_w=2.0, right_w=10.1,
                  body_size=11, row_height=0.85)


def slide_personas(s):
    slide_header(s, 'Who this serves',
        'Nine visitor personas — each searches differently and converts on different content.')

    personas = [
        ('1. Romantic Weekender',     'Couples 35-65, Bay Area / Sac, B&Bs + dining + wineries'),
        ('2. Festival Pilgrim',       'Anchored to a specific event — Cornish Christmas, Wild & Scenic, Bluegrass'),
        ('3. Trail & Lake Seeker',    'Hiking / biking / swimming / paddling — needs distance & difficulty'),
        ('4. Multi-Gen Family',       'Parents with kids 5-15 — "will my 8-year-old be bored?"'),
        ('5. Arts & Heritage Traveler', 'Substance over photos; reads notes; values authenticity'),
        ('6. Wine Country Foodie',    'Napa-alternative — provenance, chef bios, tasting flights'),
        ('7. Wellness Refugee',       'Float, massage, yoga, gardens — filtering for what\'s NOT there'),
        ('8. Local "What\'s Up"',     'Residents — pure events feed, "what\'s on this weekend"'),
        ('9. Maker Traveler  🎯',     'Travels for the workshop — Curious Forge anchors a destination identity'),
    ]
    add_bullets(s, [f'{name}    —    {desc}' for name, desc in personas],
                Inches(0.6), Inches(1.85), Inches(12.1), Inches(4.7),
                size=12, line_spacing=1.4)

    # Strategic call-out
    add_rect(s, Inches(0.6), Inches(6.0), Inches(12.1), Inches(0.85),
             RGBColor(0xFB, 0xF7, 0xEE), GOLD)
    add_text(s,
        'Recommended marketing focus (over-serve four):  Maker Traveler  ·  Festival Pilgrim  ·  Romantic Weekender  ·  Foodie',
        Inches(0.7), Inches(6.05), Inches(11.9), Inches(0.75),
        size=12, bold=True, color=BROWN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def slide_ux_decisions(s):
    slide_header(s, 'Why it\'s easy to use',
        'Friction points where most tourism sites lose visitors — and what we did instead.')

    ux_pairs = [
        ('Day-by-day with lodging anchor',
         'A flat list of stops hides the night question; structured days surface it',
         'Visitor sees Day 2 has no stay tile, books before leaving the page.'),
        ('"Find Lodging" CTA + auto-clear vibes',
         'One-click jump to lodging that doesn\'t fight against active vibes',
         'Foodie-vibe visitor taps Find Lodging; vibes clear so all stays show.'),
        ('Add Day returns to browse',
         'No leaving visitor staring at empty days; flow continues naturally',
         'Day 2 isn\'t an empty container — visitor lands somewhere productive.'),
        ('Events → itinerary first',
         'No hijack to KVMR — visitor compares before clicking through',
         'Three concerts compared side-by-side before committing to one.'),
        ('Vibe sub-pills',
         'Foodie → Restaurants/Markets/Wineries — granular without leaving the vibe',
         'Foodie → Wineries narrows without switching mental contexts.'),
        ('Calendar dates on day headers',
         '"DAY 1 · Sat, May 17" instead of abstract numbers',
         '"Sat, May 17" grounds the trip in real-world weekend planning.'),
        ('Opt-in itinerary save',
         'Survives tab close + restart — no account, no email, explicit consent',
         'Banner appears only after first add — visitor consents knowingly.'),
        ('Auto-season filtering',
         'November visit hides summer-only experiences automatically',
         'December visitor never sees "summer concert series" as a dead lead.'),
    ]
    two_col_table(s, ['Decision', 'Why it matters'], ux_pairs,
                  Inches(1.65), left_w=4.0, right_w=8.1, body_size=9,
                  row_height=0.6, scenario_size=8)


def slide_privacy(s):
    slide_header(s, 'Privacy posture',
        'No tracking. No cookies. Visitors stay anonymous; the chamber gets credit for it.')

    add_bullets(s, [
        ('No analytics, no cookies, no third-party trackers by default',
         'Site loads instantly — no cookie modal between visitor and content.'),
        ('Itinerary save is opt-in only — explicit consent banner on first add',
         'Banner appears only after first card added; visitor knows what they\'re consenting to.'),
        ('"Forget on this device" link revokes consent and wipes saved data anytime',
         'Trip ends — visitor wipes the itinerary in two taps, takes nothing back home.'),
        ('Share-link URL works without any consent — purely a URL fragment',
         'Two friends compare itineraries via shared URLs, neither registered for anything.'),
        ('No account / sign-up / email required to plan a full trip',
         '30 seconds from landing → planning, no email-collection wall.'),
        ('Chamber sees zero personal information about visitors',
         'Aggregate scraper queue tells the chamber what\'s hot; visitor identity stays local.'),
        ('No GDPR / CCPA banners required (because nothing is collected)',
         'EU visitor on holiday gets the site without a banner ambush.'),
        ('No privacy review, no consent-platform fees, no compliance overhead',
         'Annual compliance budget for the platform: $0 — nothing to review.'),
    ], Inches(0.6), Inches(1.7), Inches(12.1), Inches(4.5),
       size=11, line_spacing=1.2, scenario_size=9)

    # Closing quote
    add_rect(s, Inches(0.6), Inches(6.0), Inches(12.1), Inches(0.85),
             RGBColor(0xFB, 0xF7, 0xEE), GOLD)
    add_text(s,
        '"Visitors stay anonymous; the chamber gets credit for respecting them."',
        Inches(0.7), Inches(6.05), Inches(11.9), Inches(0.75),
        size=14, italic=True, color=BROWN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def slide_admin(s):
    slide_header(s, 'Behind the scenes',
        'Chamber-staff operations: live data with minimal effort.')

    add_bullets(s, [
        ('🔄 One-click scraper updates from KVMR, Eventbrite, NC Chamber, GV Chamber, Go Nevada, The Union',
         'Chamber staffer clicks "Run Scrapers" Monday morning; ~50 new events appear.'),
        ('✅ Approve / dismiss events in a queue; bulk-approve is one click',
         'Bulk-approve all KVMR events; dismiss the suspect ones individually.'),
        ('🤖 AI Categorize button (Claude Haiku) — refines area, venue, tags, quality (~$0.20 per full run)',
         'One click after a scrape; 460 events get area + venue + tags fixed for ~20¢.'),
        ('✏️ Inline-editable experience table — anyone who can edit a spreadsheet can maintain it',
         'New cidery opens — staff types one row, hits save, it\'s live on the public site.'),
        ('🏷 Tag taxonomy editor — add/rename/delete tags without code',
         '"Music" splits into "Live Music" and "Open Mic" without a developer.'),
        ('🔗 Source URL management — add a new scraper feed by pasting a URL',
         'New venue website? Paste the URL, pick a parser pattern, done.'),
        ('📅 Auto-prune past events; auto-dismiss internal admin meetings',
         'Saturday\'s farmers market vanishes from the queue Sunday morning.'),
        ('🌐 Public RSS feed at /feed.rss — partners republish without integration work',
         'Local newspaper\'s "this weekend" widget pulls straight from /feed.rss.'),
    ], Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.2),
       size=11, line_spacing=1.2, scenario_size=9)


def slide_ai(s):
    slide_header(s, 'AI-powered tag refinement',
        'Claude Haiku adds intelligence where keyword rules stop short — at trivial cost.')

    # Left: what AI fixes
    add_text(s, 'What it fixes', Inches(0.6), Inches(1.85), Inches(6), Inches(0.45),
             size=14, bold=True, color=GOLD)
    add_bullets(s, [
        ('444 of 460 KVMR events tagged "Nevada County" → infers actual community',
         '"KVMR Storytelling Night" gets "Nevada City" instead of vague "Nevada County".'),
        ('Empty location field on most KVMR events → extracts venue name',
         '"Center for the Arts" surfaces as the venue from a description-only event.'),
        ('"Center for the Arts" → Grass Valley; "Miners Foundry" → Nevada City',
         'Visitor filtering by Grass Valley gets concerts without manual tagging.'),
        ('Cluttered descriptions → clean one-line summaries',
         'Long press-release blob shrinks to a clean teaser the visitor will actually read.'),
        ('Truckee / Sierra-side events flagged "low quality" → auto-hidden',
         'Tahoe events tagged "low quality" auto-hide on the public site, no manual cleanup.'),
        ('Future scrapes auto-categorize new events with the same logic',
         'Tuesday\'s new event gets correct area + venue + tags without human touch.'),
    ], Inches(0.6), Inches(2.3), Inches(6), Inches(4.2),
       size=10, line_spacing=1.15, scenario_size=8)

    # Right: cost table
    add_text(s, 'Cost', Inches(7.2), Inches(1.85), Inches(5.5), Inches(0.45),
             size=14, bold=True, color=GOLD)
    two_col_table(s, ['Run pattern', 'Monthly'], [
        ('First-time bulk (460 events)',    '~$0.30 once'),
        ('Daily scrape + categorize',       '$0.30 – $0.60'),
        ('Weekly scrape + categorize',      '$0.16 – $0.52'),
        ('Realistic chamber operation',     '~$0.50 – $1.00'),
    ], Inches(2.3), left_w=3.0, right_w=2.4, body_size=10, row_height=0.45)

    # Footer note
    add_rect(s, Inches(0.6), Inches(6.5), Inches(12.1), Inches(0.5),
             RGBColor(0xFB, 0xF7, 0xEE), GOLD)
    add_text(s,
        'Hard $5/month spending cap settable in Anthropic console — cannot be exceeded.',
        Inches(0.7), Inches(6.55), Inches(11.9), Inches(0.4),
        size=11, italic=True, color=BROWN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def slide_cost(s):
    slide_header(s, 'What it costs',
        'Three operating scenarios for the first year of operation.')

    # 4 stat cards: Lean, Typical, Premium, Comparison
    add_stat_card(s, Inches(0.6),  Inches(1.85), Inches(2.85), Inches(1.7),
                  '$0–$50',  'LEAN\nFree hosting + AI off')
    add_stat_card(s, Inches(3.65), Inches(1.85), Inches(2.85), Inches(1.7),
                  '$80–$150', 'TYPICAL\n$5/mo VPS + weekly AI')
    add_stat_card(s, Inches(6.7),  Inches(1.85), Inches(2.85), Inches(1.7),
                  '$300–$500', 'PREMIUM\nManaged + daily AI')
    add_stat_card(s, Inches(9.75), Inches(1.85), Inches(2.85), Inches(1.7),
                  '$5K–$30K',  'COMMERCIAL ALT.\nCrowdRiff / Simpleview')

    # Bullet list of what's NOT a cost
    add_text(s, 'What\'s NOT a cost',
             Inches(0.6), Inches(3.85), Inches(6), Inches(0.45),
             size=14, bold=True, color=GOLD)
    add_bullets(s, [
        'Per-listing fees — every chamber member free',
        'Per-event fees — scrapers cost zero',
        'Per-visitor fees — traffic 10× has no impact',
        'Vendor termination fees — owned outright',
        'Privacy compliance overhead — nothing collected to comply about',
        'License fees — fully open-source stack',
    ], Inches(0.6), Inches(4.3), Inches(12.1), Inches(2.6),
       size=12, line_spacing=1.4)


def slide_next_steps(s):
    """
    Retitled per chat-Claude feedback: "What the chamber needs to do next"
    sounded like assigning homework. New framing is collaborative.
    """
    slide_header(s, 'Where the group can take this',
        'Findings from the build — collaborative work that would unlock the next version.')

    # Three columns of action items grouped by category
    col_y = Inches(1.85); col_h = Inches(4.6)

    # ── Column 1: Data partnerships ──
    add_text(s, 'DATA PARTNERSHIPS',
             Inches(0.6), col_y, Inches(4.0), Inches(0.4),
             size=12, bold=True, color=GOLD)
    add_bullets(s, [
        'Ask NCAC for read access to their Trumba '
        'master — its 540-event, 16-month window is '
        'the most comprehensive feed in the county',
        'Reach out to GoNevadaCounty (gonevadacounty.com) '
        'for a public events feed — Cloudflare blocks '
        'scrapers and we lose the 13 anchor festivals',
        'Coordinate with The Union for a public events '
        'feed — articles are paywalled and the RSS often '
        'returns nothing scrape-able',
        'Confirm whether the County itself runs a Trumba '
        'master calendar — if so, federate from it instead '
        'of NCAC alone',
    ], Inches(0.6), col_y + Inches(0.4), Inches(4.0), col_h - Inches(0.4),
       size=9, line_spacing=1.35)

    # ── Column 2: Member outreach ──
    add_text(s, 'MEMBER OUTREACH',
             Inches(4.7), col_y, Inches(4.0), Inches(0.4),
             size=12, bold=True, color=GOLD)
    add_bullets(s, [
        'Encourage venues to publish events on a '
        'platform with a public feed — Trumba, Tribe '
        'Events (WordPress), Eventbrite — not just '
        'static HTML pages',
        'Push schema.org/Event JSON-LD adoption — one '
        'snippet on each event page makes scraping '
        'reliable without custom code per site',
        'Solicit "missing venue" submissions — a simple '
        'web form for member venues to flag events that '
        'didn\'t get auto-discovered',
        'Identify the 5-10 venues responsible for the bulk '
        'of visitor traffic and prioritize their data '
        'reliability over long-tail coverage',
    ], Inches(4.7), col_y + Inches(0.4), Inches(4.0), col_h - Inches(0.4),
       size=9, line_spacing=1.35)

    # ── Column 3: Operations ──
    add_text(s, 'OPERATIONS',
             Inches(8.8), col_y, Inches(4.0), Inches(0.4),
             size=12, bold=True, color=GOLD)
    add_bullets(s, [
        'Designate a queue curator — someone clears the '
        'pending-events queue 1-2x per week (Approve / '
        'Dismiss takes ~5 minutes per session)',
        'Run AI Categorize after each scrape — fixes '
        'venue, area, tags on long-tail events ($0.50/mo)',
        'Validate "no event" alerts — when a scraper '
        'returns 0 events, the source has either gone '
        'down or restructured (NCAC was a false negative '
        'for months before we caught it)',
        'Quarterly review of disabled scrapers — vendors '
        'change platforms (e.g. NCAC moved to Trumba) and '
        'previously-blocked sources become reachable',
    ], Inches(8.8), col_y + Inches(0.4), Inches(4.0), col_h - Inches(0.4),
       size=9, line_spacing=1.35)

    # Bottom callout: what we already learned
    add_rect(s, Inches(0.6), Inches(6.5), Inches(12.1), Inches(0.5),
             RGBColor(0xFB, 0xF7, 0xEE), GOLD)
    add_text(s,
        'Concrete win from this work:  NCAC\'s calendar went from "0 events" '
        '(blocked by an iframe) to 540 events — by hitting Trumba\'s JSON feed directly.',
        Inches(0.7), Inches(6.55), Inches(11.9), Inches(0.4),
        size=10, italic=True, color=BROWN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def slide_migration(s):
    """
    Note from chat-Claude: "9-phase migration plan for a prototype conversation
    feels premature." Kept as a regular slide near the end, but consider this
    a candidate for an appendix / skip-unless-asked depending on the room.
    """
    slide_header(s, 'Migration to a county server',
        'One focused half-day for someone comfortable with Linux; two days for a learner.')

    steps = [
        ('Phase 0',  'Decisions: hosting (DigitalOcean $6/mo recommended), domain, OS, server account ownership'),
        ('Phase 1',  'Pre-flight: domain registered, DNS access, SSH keys ready, Anthropic API key generated'),
        ('Phase 2',  'Provision: $6/mo Ubuntu droplet, lockdown SSH, install Python + nginx + chromium'),
        ('Phase 3',  'Deploy: git clone, Python venv, install deps, drop API keys in scraper/config.py'),
        ('Phase 4',  'systemd service for auto-restart on crash, auto-start on reboot'),
        ('Phase 5',  'nginx reverse proxy + Let\'s Encrypt HTTPS (auto-renew via certbot)'),
        ('Phase 6',  'Cron job: nightly scrape at 3 AM + AI categorize at 3:30 AM'),
        ('Phase 7',  'Backups: provider snapshots ($1/mo) + daily JSON tar to off-site'),
        ('Phase 8',  'Test checklist: site loads, vibes work, events populate, AI button works, scraper runs'),
        ('Phase 9',  'Hand-off to chamber: admin URL, billing alerts, cheat sheet, emergency contact'),
    ]
    two_col_table(s, ['Phase', 'What happens'], steps,
                  Inches(1.85), left_w=1.6, right_w=10.5,
                  body_size=10, row_height=0.4)


def slide_thank_you(s):
    # Brown band on left
    add_rect(s, 0, 0, Inches(4.5), SLIDE_H, BROWN)
    add_rect(s, Inches(4.5), 0, Inches(0.08), SLIDE_H, GOLD)

    add_text(s, 'Thank you',
             Inches(0.6), Inches(2.4), Inches(3.7), Inches(1.0),
             size=44, bold=True, color=GOLD_LIGHT, font='Calibri')
    add_text(s, 'Questions?',
             Inches(0.6), Inches(3.4), Inches(3.7), Inches(0.7),
             size=22, color=WHITE, italic=True, font='Calibri')

    add_text(s, 'The leave-behind one-liner',
             Inches(4.9), Inches(2.4), Inches(7.8), Inches(0.5),
             size=14, bold=True, color=GOLD)
    add_gold_rule(s, Inches(4.9), Inches(2.85), Inches(7.5))
    add_text(s,
        '"This isn\'t a website — it\'s a planning workspace for visitors and a '
        'living directory for the chamber, with AI-assisted curation built in. '
        'Privacy-respecting by default, owned by the county outright, '
        'maintained in minutes per week."',
        Inches(4.9), Inches(3.05), Inches(7.8), Inches(2.5),
        size=14, italic=True, color=BROWN)

    # Footer info
    add_text(s,
        'Live demo:  liammlrb-eng.github.io/nevada-county-experiences\n'
        'Repo:       github.com/liammlrb-eng/nevada-county-experiences\n'
        'Pitch deck: demo_pitch.pdf  ·  Operator guide: operator_guide.pdf',
        Inches(4.9), Inches(5.6), Inches(7.8), Inches(1.5),
        size=11, color=SLATE, font='Consolas')


# ═══════════════════════════ DECK NARRATIVE ═══════════════════════════════
# Five-act structure based on chat-Claude's reorder feedback (May 2026):
#
#   Act 1 — Why we're here     (title + strategic insight)
#   Act 2 — What I built       (what this is + discovery + itinerary + demo)
#   Act 3 — Why this works     (personas + UX + privacy)
#   Act 4 — How it runs        (admin + AI + cost)
#   Act 5 — What's next        (group next steps + migration appendix + close)
#
# Each entry: (function, show_page_footer)
SLIDE_ORDER = [
    # ── Act 1 ─────────────────────────────────────────────────────────────
    (slide_title,              False),
    (slide_strategic_insight,  True),   # Lead with the lodging-revenue framing
    # ── Act 2 ─────────────────────────────────────────────────────────────
    (slide_what_this_is,       True),   # Numbers as evidence for Act 1's argument
    (slide_discovery,          True),
    (slide_itinerary,          True),
    (slide_demo_flow,          True),   # Live demo — the emotional peak
    # ── Act 3 ─────────────────────────────────────────────────────────────
    (slide_personas,           True),   # After demo, personas feel like real people
    (slide_ux_decisions,       True),
    (slide_privacy,            True),
    # ── Act 4 ─────────────────────────────────────────────────────────────
    (slide_admin,              True),
    (slide_ai,                 True),
    (slide_cost,               True),   # Second big moment — $6/mo vs $5K–$30K
    # ── Act 5 ─────────────────────────────────────────────────────────────
    (slide_next_steps,         True),   # "Where the group can take this"
    (slide_migration,          True),   # Optional / appendix-feeling — skip if no IT in room
    (slide_thank_you,          False),
]

TOTAL = len(SLIDE_ORDER)


# ═══════════════════════════ BUILD THE DECK ═══════════════════════════════
for i, (build_fn, show_footer) in enumerate(SLIDE_ORDER, 1):
    s = prs.slides.add_slide(BLANK)
    build_fn(s)
    if show_footer:
        page_footer(s, i, TOTAL)


# ─── Save ───────────────────────────────────────────────────────────────
import shutil
project_root = Path(__file__).resolve().parent
out = project_root / 'demo_pitch.pptx'
prs.save(str(out))
print(f'Wrote: {out}')
print(f'Slides: {TOTAL}')
print(f'Size: {out.stat().st_size:,} bytes ({out.stat().st_size/1024:.1f} KB)')

# Mirror to pitch_resources/ so the chat-upload bundle stays in sync
mirror_dir = project_root / 'pitch_resources'
if mirror_dir.is_dir():
    mirror = mirror_dir / 'demo_pitch.pptx'
    shutil.copy2(out, mirror)
    print(f'Mirrored: {mirror}')

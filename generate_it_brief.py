"""
Generate it_migration_brief.pdf — technical reference for county IT staff
evaluating adoption of the Nevada County Experience platform.

Audience: county IT director, sysadmin, security/policy reviewer.
Tone: detailed but concise, no marketing framing.

Run:   python generate_it_brief.py
Out:   it_migration_brief.pdf  (in project root + pitch_resources/)
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Preformatted, KeepTogether,
)
from pathlib import Path

# ── Palette (matches operator_guide.pdf for cross-doc consistency) ──────────
BROWN   = colors.HexColor('#5C3A1F')
GOLD    = colors.HexColor('#C9A84C')
SLATE   = colors.HexColor('#4A5568')
FOG     = colors.HexColor('#F5EFE2')
DARK    = colors.HexColor('#1E1508')
RULE    = colors.HexColor('#D4C9B0')
GREEN_OK   = colors.HexColor('#2F7D32')   # works as-is
AMBER_WARN = colors.HexColor('#B8860B')   # partial / fallback
RED_BLOCK  = colors.HexColor('#8B0000')   # feature disabled

# ── Styles ─────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()
H_TITLE = ParagraphStyle('Title', parent=styles['Title'],
    fontName='Helvetica-Bold', fontSize=24, leading=28,
    textColor=BROWN, alignment=TA_LEFT, spaceAfter=4)
H_SUB = ParagraphStyle('Subtitle', parent=styles['Normal'],
    fontName='Helvetica', fontSize=11, leading=15,
    textColor=SLATE, spaceAfter=18)
H1 = ParagraphStyle('H1', parent=styles['Heading1'],
    fontName='Helvetica-Bold', fontSize=16, leading=20,
    textColor=BROWN, spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle('H2', parent=styles['Heading2'],
    fontName='Helvetica-Bold', fontSize=12, leading=16,
    textColor=BROWN, spaceBefore=8, spaceAfter=3)
H3 = ParagraphStyle('H3', parent=styles['Heading3'],
    fontName='Helvetica-Bold', fontSize=10.5, leading=14,
    textColor=GOLD, spaceBefore=6, spaceAfter=2)
BODY = ParagraphStyle('Body', parent=styles['BodyText'],
    fontName='Helvetica', fontSize=10, leading=13.5, textColor=DARK, spaceAfter=4)
BULLET = ParagraphStyle('Bullet', parent=BODY,
    fontSize=10, leading=13.5, leftIndent=14, spaceAfter=2)
SMALL = ParagraphStyle('Small', parent=BODY,
    fontSize=8.5, leading=11.5, textColor=SLATE, spaceAfter=2)
CODE = ParagraphStyle('Code', parent=styles['Code'],
    fontName='Courier', fontSize=8, leading=11,
    textColor=DARK, backColor=colors.HexColor('#FBF7EE'),
    borderColor=RULE, borderWidth=0.5, borderPadding=6,
    leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8)


def section_rule(color=GOLD, width=6.5*inch, thickness=2):
    t = Table([['']], colWidths=[width], rowHeights=[thickness])
    t.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), thickness, color),
        ('LEFTPADDING',(0,0),(-1,-1),0), ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0), ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    return t


def build_table(rows, col_widths, header=True, zebra=True, body_size=9):
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('FONT',         (0,0), (-1,-1), 'Helvetica', body_size),
        ('TEXTCOLOR',    (0,0), (-1,-1), DARK),
        ('LEFTPADDING',  (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]
    if header:
        style += [
            ('BACKGROUND',(0,0),(-1,0), BROWN),
            ('TEXTCOLOR', (0,0),(-1,0), colors.white),
            ('FONT',      (0,0),(-1,0), 'Helvetica-Bold', body_size + 0.5),
            ('BOTTOMPADDING',(0,0),(-1,0), 6),
            ('TOPPADDING',(0,0),(-1,0), 6),
        ]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == (1 if header else 0):
                style.append(('BACKGROUND',(0,i),(-1,i), FOG))
    style += [
        ('LINEBELOW',(0,-1),(-1,-1), 0.5, RULE),
        ('LINEBELOW',(0, 0),(-1, 0), 0.8, GOLD),
    ]
    t.setStyle(TableStyle(style))
    return t


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT BUILD
# ═══════════════════════════════════════════════════════════════════════════
project_root = Path(__file__).resolve().parent
out_path = project_root / 'it_migration_brief.pdf'

doc = SimpleDocTemplate(str(out_path), pagesize=LETTER,
    leftMargin=0.7*inch, rightMargin=0.7*inch,
    topMargin=0.7*inch, bottomMargin=0.7*inch,
    title='Nevada County Experience — IT Migration & Dependencies Brief',
    author='Nevada County Experience project',
)
flow = []

# ─────────────────────────────────────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('IT Migration &amp; Dependencies Brief', H_TITLE))
flow.append(Paragraph('Nevada County Experience — technical reference for county IT staff', H_SUB))
flow.append(section_rule())
flow.append(Spacer(1, 8))

flow.append(Paragraph(
    'This document supports the technical evaluation of moving the Nevada '
    'County Experience platform onto county-owned infrastructure. It '
    'enumerates every external service the platform touches, the data flow '
    'in both directions, four hosting scenarios with cost and policy '
    'implications, a step-by-step migration plan, ongoing administrative '
    'responsibilities, and a policy-block impact matrix.',
    BODY))
flow.append(Paragraph(
    '<b>Key facts up front:</b>',
    BODY))
key_facts = [
    'Platform is a static HTML/JS site plus a small Python (Flask) admin server.',
    'No database — all data lives in JSON files inside the project directory.',
    'No visitor accounts, no PII collected; itinerary save is opt-in localStorage.',
    'Outbound network calls only — no inbound listening except HTTPS/443.',
    'AI categorization is optional; site is fully functional without it.',
    'Total monthly cost on a $6/mo VPS: ~$7-8 including AI use at chamber scale.',
]
for f in key_facts:
    flow.append(Paragraph(f'•  {f}', BULLET))

flow.append(Spacer(1, 10))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: EXTERNAL SERVICES INVENTORY
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('1. External Services Inventory', H1))
flow.append(Paragraph(
    'Every external dependency the platform touches, with vendor, purpose, '
    'data flow direction, monthly cost, what fails if the service is blocked '
    'or down, and replacement options. <b>Outbound</b> = our server initiates; '
    '<b>Inbound</b> = visitor reaches us. There are no inbound vendor connections.',
    BODY))

inv_rows = [
    ['Service', 'Purpose', 'Direction', 'Cost', 'Required?'],
    ['Anthropic Claude API',
     'AI categorize button — refines tags, venue, area, quality flags on scraped events',
     'Outbound HTTPS to api.anthropic.com',
     '$0.30–$1/mo',
     'Optional'],
    ['Plausible Analytics',
     'Privacy-respecting aggregate metrics (page views, itinerary build count). No cookies, no PII',
     'Outbound HTTPS to plausible.io',
     '$0 (self-host) or $9/mo cloud',
     'Optional, opt-in'],
    ['GitHub Pages',
     'Static-site hosting (current public deploy). Replaceable by any web server',
     'Outbound HTTPS to github.com on deploy only',
     '$0',
     'Replaceable'],
    ['Google Fonts CDN',
     'Playfair Display + Josefin Sans typefaces. Hotlinked from the index.html head section',
     'Outbound HTTPS from visitor browser to fonts.googleapis.com',
     '$0',
     'Replaceable (self-host)'],
    ['Leaflet (Cloudflare CDN)',
     'Map library for the "View on Map" feature. Hotlinked from cdnjs.cloudflare.com',
     'Outbound HTTPS from visitor browser',
     '$0',
     'Replaceable (self-host)'],
    ['Unsplash CDN',
     'Stock photography for theme cards. ~30 hotlinked images',
     'Outbound HTTPS from visitor browser to images.unsplash.com',
     '$0',
     'Replaceable (self-host)'],
    ['KVMR website (scrape target)',
     'Community-radio events calendar — major source of weekly events',
     'Outbound HTTPS from server (kvmr.org)',
     '$0',
     'Optional source'],
    ['Trumba JSON feed (NCAC)',
     'Nevada County Arts Council calendar — 540 events, 16-month window. JSON, no auth',
     'Outbound HTTPS to trumba.com',
     '$0',
     'Optional source'],
    ['Eventbrite, NC Chamber, GV Chamber, The Union',
     'Additional event scrape sources. Public HTML pages, no auth',
     'Outbound HTTPS from server',
     '$0',
     'Optional sources'],
    ['Let\'s Encrypt',
     'Free TLS certificates via certbot. Required for HTTPS',
     'Outbound HTTPS to acme-v02.api.letsencrypt.org during cert renewal',
     '$0',
     'Required for HTTPS'],
    ['Gmail SMTP (optional alerting)',
     'Currently used by trade-related projects; not used by this platform',
     'N/A here',
     'N/A',
     'Not used'],
]
flow.append(build_table(inv_rows,
    col_widths=[1.4*inch, 2.3*inch, 1.6*inch, 0.7*inch, 0.7*inch],
    body_size=8.5))

flow.append(Paragraph(
    '<b>What we do not use:</b> no third-party tracking / advertising / '
    'identity / payment / CDN-for-data services. No social-login providers. '
    'No vendor SDK or proprietary library — the entire site is plain '
    'HTML/JS that opens in any modern browser.',
    BODY))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: ARCHITECTURE & DATA FLOW
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('2. Architecture &amp; Data Flow', H1))

flow.append(Paragraph('2a. Components', H2))
arch_rows = [
    ['Component', 'Tech', 'Disk path', 'Network'],
    ['Public static site',  'HTML + JS (single file)', 'index.html',
     'Served on :443 to visitors'],
    ['Admin server',        'Python 3.12 + Flask',    'server.py',
     'Listens on :5000 behind nginx'],
    ['Event scraper',       'Python 3 + Selenium (Chromium headless)', 'scraper/event_scraper.py',
     'Outbound HTTPS to source sites'],
    ['AI categorizer',      'Python 3 + Anthropic SDK', 'scraper/ai_categorize.py',
     'Outbound HTTPS to api.anthropic.com'],
    ['Events queue file',   'JSON',                    'scraper_output/events.json',
     'Local only'],
    ['Suggestions file',    'JSON',                    'scraper_output/suggestions.json',
     'Local only'],
    ['Scraper sources file','JSON',                    'scraper/sources.json',
     'Local only'],
    ['Itinerary state',     'localStorage in visitor\'s browser',  'n/a (client-side)',
     'Never leaves the visitor\'s device'],
]
flow.append(build_table(arch_rows,
    col_widths=[1.5*inch, 1.7*inch, 1.8*inch, 1.8*inch],
    body_size=8.5))
flow.append(Spacer(1, 6))

flow.append(Paragraph('2b. Data flow', H2))
flow.append(Paragraph(
    '<b>Visitor path:</b> browser → CDN (Google Fonts, Leaflet, Unsplash, '
    'optional Plausible) and HTTPS to our server :443 → nginx reverse-'
    'proxies to Flask on :5000 → returns index.html and JSON event data. '
    'No cookies set; no server-side session.',
    BODY))
flow.append(Paragraph(
    '<b>Admin path:</b> chamber staff browser → HTTPS to /admin (gated by '
    'either localhost-only access or ?admin=1 query parameter on a '
    'whitelisted hostname) → Flask serves the admin endpoints (events queue, '
    'suggestions, scraper trigger, AI categorize trigger).',
    BODY))
flow.append(Paragraph(
    '<b>Scheduled job path:</b> cron / systemd timer / Windows Task '
    'Scheduler → invokes Python scraper → scraper fetches HTML/JSON from '
    'each enabled source → writes new entries to events.json → optionally '
    'invokes AI categorizer which posts to Anthropic API and writes '
    'enriched fields back to events.json.',
    BODY))
flow.append(Paragraph(
    '<b>What flows OUT of the county:</b> only the scrape requests '
    '(public-page fetches), AI categorize prompts (event titles + '
    'descriptions, no PII), and Let\'s Encrypt cert renewal calls. No '
    'visitor data is ever transmitted to a third party.',
    BODY))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: HOSTING SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('3. Hosting Scenarios', H1))
flow.append(Paragraph(
    'Four realistic options for where the platform runs. Pick by whatever '
    'best matches county policy on cloud vs. on-prem and OS preference. '
    'Migration effort is similar across A, B, and C (Linux). Scenario D '
    '(Windows Server) is the heaviest lift because the scraper expects a '
    'POSIX environment.',
    BODY))

flow.append(Paragraph('3a. Scenario A — Linux VPS (DigitalOcean, Vultr, Linode)', H2))
flow.append(Paragraph(
    '<b>Profile:</b> $6–12/month managed VPS. Ubuntu 24.04 LTS. We provision, '
    'county pays the bill directly. County retains root SSH access; vendor '
    'handles hypervisor and provider backups.',
    BODY))
flow.append(Paragraph(
    '<b>Effort:</b> half-day for a Linux-comfortable admin; two days for a '
    'learner. <b>Monthly:</b> $6 (droplet) + $1 (provider backups) + ~$1 '
    '(AI) = $8/mo. <b>Best for:</b> chambers that prefer "we know one '
    'person who can SSH in and fix things" over an in-house ops team.',
    BODY))

flow.append(Paragraph('3b. Scenario B — AWS / Azure / GCP IaaS', H2))
flow.append(Paragraph(
    '<b>Profile:</b> AWS EC2 t4g.small or Azure Standard_B1ms, Ubuntu image. '
    'Roughly $15–25/month for the smallest instance the platform needs. '
    'County may already have an enterprise account, security baselines, and '
    'an existing landing-zone configuration to drop into.',
    BODY))
flow.append(Paragraph(
    '<b>Effort:</b> half-day if the county has paved-road provisioning; '
    'one day otherwise. <b>Monthly:</b> $15–25 (instance) + $5 (EBS storage '
    '&amp; snapshots) + ~$1 (AI) = $21–31/mo. <b>Best for:</b> counties '
    'standardized on a public-cloud vendor with existing tooling.',
    BODY))

flow.append(Paragraph('3c. Scenario C — County on-prem VMware / Hyper-V (Linux VM)', H2))
flow.append(Paragraph(
    '<b>Profile:</b> Ubuntu 24.04 LTS as a guest on county-managed '
    'hypervisor. 2 vCPU, 4 GB RAM, 30 GB disk is plenty. County handles '
    'host-level backups, patching cadence, and network access; we install '
    'the application stack inside the VM.',
    BODY))
flow.append(Paragraph(
    '<b>Effort:</b> half-day to a day depending on how long VM provisioning '
    'takes through the county\'s request process. <b>Monthly:</b> '
    'incremental (counted as part of existing virtualization licensing). '
    'AI use still ~$1/mo if outbound is permitted. <b>Best for:</b> '
    'counties with existing private-cloud capacity and policy preference '
    'for on-prem.',
    BODY))

flow.append(Paragraph('3d. Scenario D — Windows Server (IIS or Python service)', H2))
flow.append(Paragraph(
    '<b>Profile:</b> Windows Server 2022, IIS reverse-proxies to the Flask '
    'admin server, scraper runs as a Windows Service via NSSM or as a '
    'scheduled task via Task Scheduler. Chromium must be installed for '
    'Selenium; HTTPS via win-acme (alternative to certbot).',
    BODY))
flow.append(Paragraph(
    '<b>Effort:</b> one to two days. The scraper depends on Selenium with '
    'headless Chromium — works on Windows but is less battle-tested than '
    'Linux. Chocolatey or winget for installs.',
    BODY))
flow.append(Paragraph(
    '<b>Monthly:</b> incremental (existing Windows Server licensing) + AI '
    '~$1. <b>Best for:</b> counties whose IT shop is exclusively Windows '
    'and has no Linux administration capacity.',
    BODY))

flow.append(Paragraph('Sizing summary (all scenarios):', H3))
sizing_rows = [
    ['Resource', 'Minimum', 'Recommended', 'Why'],
    ['CPU', '1 vCPU', '2 vCPU', 'Headless Chromium during scrape; 1-2 minute peak'],
    ['RAM', '2 GB', '4 GB', 'Chromium memory footprint; Flask itself is tiny'],
    ['Disk', '10 GB', '30 GB', 'Code under 100 MB; JSON files grow slowly; backups optional'],
    ['Bandwidth', '5 GB/mo egress', '20 GB/mo', 'Static site; map/font CDN traffic served by 3rd parties'],
    ['Inbound ports', '443 only', '443 + 22 (SSH limited)', '80→443 redirect; SSH locked to admin IPs'],
]
flow.append(build_table(sizing_rows,
    col_widths=[1.3*inch, 1.1*inch, 1.5*inch, 3*inch],
    body_size=8.5))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: MIGRATION PLAN (DETAILED)
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('4. Migration Plan', H1))
flow.append(Paragraph(
    'Ten phases, each independently verifiable. The walkthrough assumes '
    'Linux (scenarios A/B/C); Windows differences are called out where '
    'relevant. A Linux-comfortable admin completes phases 0–9 in a focused '
    'half-day.',
    BODY))

mig_rows = [
    ['Phase', 'What happens', 'Owner', 'Verifiable when'],
    ['0. Decisions',
     'Pick hosting scenario, domain name, DNS provider, who owns the bill. Generate Anthropic API key (optional).',
     'County IT + chamber',
     'Hosting account + domain registered'],
    ['1. Pre-flight',
     'Domain DNS access confirmed, SSH key pair created and saved, Anthropic key stored in password manager.',
     'County IT',
     'All credentials in a shared password vault'],
    ['2. Provision',
     'VM/droplet created, Ubuntu 24.04 LTS installed, security baseline applied (firewall, fail2ban, automatic updates), Python 3.12 / nginx / chromium installed.',
     'County IT',
     '`ssh ncexp@server` connects; `nginx -v` and `python3 --version` succeed'],
    ['3. Deploy',
     'Repository cloned to /opt/ncexp, Python venv created, requirements.txt installed, config.py populated with API key.',
     'County IT or contractor',
     '`python server.py` starts cleanly on port 5000'],
    ['4. systemd service',
     'ncexp.service unit file installed under /etc/systemd/system, enabled to auto-start on boot, auto-restart on crash.',
     'County IT',
     '`systemctl status ncexp` reports active (running)'],
    ['5. nginx + TLS',
     'nginx vhost reverse-proxies localhost:5000 to public 443. Certbot issues Let\'s Encrypt certificate; auto-renew cron installed.',
     'County IT',
     '`curl https://ncexperience.county.gov` returns the site; SSL Labs grade A'],
    ['6. Schedule scrapes',
     'cron entries (Linux) or Task Scheduler entries (Windows) added: nightly source refresh at 3 AM, AI categorize at 3:30 AM, daily backup at 4 AM.',
     'County IT',
     '`/var/log/ncexp-scrape.log` shows a successful 3 AM run'],
    ['7. Backups',
     'Provider snapshots enabled (DO/AWS) OR county VM backup policy applied (C). Daily JSON tarball mirrored to off-site (S3, county SAN, or scp).',
     'County IT',
     'Restore test: pull yesterday\'s tarball, verify events.json round-trips'],
    ['8. Test checklist',
     'Public site loads in all major browsers; admin Events Queue accepts approve/dismiss; AI Categorize button completes a small batch (skip if AI disabled); /feed.rss returns valid XML.',
     'Chamber + IT',
     'All seven items in the test sheet pass'],
    ['9. Hand-off',
     'Document handed to chamber: admin URL, log paths, common troubleshooting, escalation contact. County IT retains root.',
     'County IT + chamber',
     'Chamber operator runs through the operator_guide.pdf flow unassisted'],
]
flow.append(build_table(mig_rows,
    col_widths=[1.0*inch, 3.0*inch, 1.2*inch, 1.8*inch],
    body_size=8))

flow.append(Spacer(1, 6))

flow.append(Paragraph('Phase 6 — schedule example (Linux cron)', H3))
flow.append(Preformatted("""# Edit the ncexp user's crontab
sudo -u ncexp crontab -e

# Add three lines (UTC times — adjust for PT if server isn't on PT):
0  3 * * * cd /opt/ncexp && .venv/bin/python scraper/event_scraper.py >> /var/log/ncexp-scrape.log 2>&1
30 3 * * * cd /opt/ncexp && .venv/bin/python scraper/ai_categorize.py  >> /var/log/ncexp-ai.log     2>&1
0  4 * * * tar czf /var/backups/ncexp-$(date +\\%Y\\%m\\%d).tgz /opt/ncexp/scraper_output""", CODE))

flow.append(Paragraph('Phase 6 — schedule example (Windows Task Scheduler)', H3))
flow.append(Preformatted("""schtasks /Create /TN "NCExp-Scrape" /TR "C:\\ncexp\\.venv\\Scripts\\python.exe C:\\ncexp\\scraper\\event_scraper.py" /SC DAILY /ST 03:00 /RU ncexp
schtasks /Create /TN "NCExp-AI"     /TR "C:\\ncexp\\.venv\\Scripts\\python.exe C:\\ncexp\\scraper\\ai_categorize.py"  /SC DAILY /ST 03:30 /RU ncexp""", CODE))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: ADMINISTRATION RESPONSIBILITIES & FREQUENCIES
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('5. Administration Responsibilities &amp; Frequencies', H1))
flow.append(Paragraph(
    'Two roles maintain the platform: <b>chamber operator</b> (content '
    'curation, queue review) and <b>county IT</b> (server health, security '
    'patches, backups). Time estimates assume the platform is running '
    'normally; incidents are separate.',
    BODY))

flow.append(Paragraph('5a. Chamber operator tasks', H2))
op_rows = [
    ['Task', 'Frequency', 'Time', 'Tool'],
    ['Review the pending Events Queue, approve / dismiss',
     '2–3× per week',  '5–10 min',  'Admin → Events Queue tab'],
    ['Run AI Categorize after a scrape',
     'After each scrape',  '~30 sec (click + wait)',  'Admin → AI Categorize button'],
    ['Click 🧹 Prune Past between scrapes if queue grows',
     'Ad-hoc',  '30 sec',  'Admin → Events Queue → 🧹 Prune Past'],
    ['Review the Suggestions tab (visitor-submitted ideas)',
     'Weekly',  '10–15 min',  'Admin → Suggestions tab'],
    ['Spot-check that scrapers are not returning 0 events',
     'Weekly',  '2 min',  'Admin → Events Queue status bar'],
    ['Publish a Suggested Experience (curated itinerary)',
     'As inspiration strikes',  '15–30 min',  'My Itinerary → ✨ Publish'],
    ['Edit / delete a published Suggested Experience',
     'Ad-hoc',  '5 min',  'Suggested Experiences tab → ✎ Edit'],
    ['Add a new venue / experience',
     'When a member opens',  '5 min',  'Admin → Experiences tab → + Add row'],
    ['Update an experience\'s hours, photo, or notes',
     'Ad-hoc',  '2 min',  'Admin → Experiences tab → inline edit'],
    ['Add a new event-source URL',
     'When discovered',  '10 min',  'Admin → Event Sources tab'],
    ['Quarterly review of disabled scraper sources',
     'Quarterly',  '30 min',  'Admin → Event Sources, re-test blocked'],
    ['Annual full-catalog walk-through (verify URLs, hours)',
     'Annual',  '4–6 hours',  'Admin → Experiences, row by row'],
]
flow.append(build_table(op_rows,
    col_widths=[2.6*inch, 1.2*inch, 1.0*inch, 2.2*inch],
    body_size=8.5))

flow.append(Paragraph(
    '<b>Estimated steady-state chamber operator time:</b> ~30 minutes per '
    'week during normal operation, plus a 4–6 hour annual review.',
    BODY))

flow.append(Spacer(1, 4))
flow.append(Paragraph('5b. County IT tasks', H2))
it_rows = [
    ['Task', 'Frequency', 'Time', 'Tool / location'],
    ['OS security updates',
     'Weekly (auto, monitored)',  '5 min review',  '`unattended-upgrades` log'],
    ['Application updates (git pull from upstream)',
     'Monthly or as needed',  '15 min',  '`git pull && systemctl restart ncexp`'],
    ['Backup verification — pull last tarball and dry-run restore',
     'Monthly',  '15 min',  '`tar tzf ncexp-YYYYMMDD.tgz`'],
    ['TLS certificate expiry check (certbot auto-renews; verify)',
     'Quarterly',  '5 min',  '`certbot certificates`'],
    ['Log rotation health',
     'Quarterly',  '5 min',  '`ls -la /var/log/ncexp-*.log`'],
    ['Disk usage review',
     'Quarterly',  '5 min',  '`df -h` / `du -sh /opt/ncexp/scraper_output`'],
    ['User access review — SSH keys, admin URLs',
     'Semi-annual',  '15 min',  '`~/.ssh/authorized_keys`; admin host whitelist'],
    ['DR / restore drill — full server rebuild from backup',
     'Annual',  '2–4 hours',  'Snapshot → fresh VM → restore JSON'],
    ['Anthropic API key rotation',
     'Annual or on staff change',  '10 min',  'Anthropic console + `config.py`'],
    ['Vendor / external-service review (still permitted? alternatives?)',
     'Annual',  '30 min',  'This document, section 1'],
]
flow.append(build_table(it_rows,
    col_widths=[2.6*inch, 1.4*inch, 1.0*inch, 2.0*inch],
    body_size=8.5))

flow.append(Paragraph(
    '<b>Estimated steady-state county IT time:</b> ~30 minutes per month '
    'during normal operation, plus an annual DR drill.',
    BODY))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: SECURITY POSTURE
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('6. Security &amp; Compliance Posture', H1))

sec_rows = [
    ['Control', 'How it\'s handled'],
    ['Inbound network exposure',
     'HTTPS only (port 443). SSH (22) restricted to admin IPs via firewall. No other listening ports.'],
    ['TLS / certificates',
     'Let\'s Encrypt via certbot; auto-renew cron. Strong cipher suite per Mozilla "intermediate" profile.'],
    ['Secrets storage',
     'API keys and credentials in `config.py` (file mode 0600, owned by service user). Not in git. Optional: load from environment variables.'],
    ['Authentication',
     'Visitor: none required. Admin URL: localhost-only by default OR `?admin=1` query parameter on a whitelisted hostname. For public admin, add HTTP Basic auth at the nginx layer (5-minute config).'],
    ['Authorization',
     'Single chamber operator role; no fine-grained RBAC. Add nginx Basic auth users for multiple operators if required.'],
    ['Personal data (PII)',
     'None collected. Itinerary save is opt-in localStorage on the visitor device — never leaves their browser. Suggestion form collects only the optional email the visitor types.'],
    ['GDPR / CCPA scope',
     'Effectively out of scope: no cookies, no PII storage. Suggestion-form emails (if entered) fall under standard records-retention policy.'],
    ['ADA / WCAG',
     'WCAG 2.1 AA on the demo. High-contrast text, keyboard-navigable, semantic HTML. Re-audit recommended after each major UI change.'],
    ['Logging',
     '`/var/log/ncexp-scrape.log`, `/var/log/ncexp-ai.log`, `journalctl -u ncexp` for the web server. No visitor-IP retention by default.'],
    ['Patch cadence',
     'OS: `unattended-upgrades` for security patches. Application: monthly `git pull` review. Python deps: quarterly `pip list --outdated`.'],
    ['Incident response',
     'Site is stateless apart from the JSON files; full restore from backup is < 30 minutes. Provider snapshot rollback covers OS-level compromises.'],
    ['Supply chain',
     'All Python deps pinned in requirements.txt. Frontend deps via CDN (Leaflet, fonts) — self-host option documented in section 7 if CDN use is restricted.'],
]
flow.append(build_table(sec_rows,
    col_widths=[1.8*inch, 5.0*inch],
    body_size=8.5))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: FLASK SERVER — SECURITY REVIEW
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('7. Flask Server — Security Review', H1))
flow.append(Paragraph(
    'The public site is plain HTML/JS and can be deployed to any web server '
    'with no special review. The <b>Flask admin server</b> is the only '
    'component that warrants security scrutiny — it executes Python, '
    'spawns subprocesses (headless Chromium for scrapes), holds API '
    'credentials, and writes to the local filesystem. This section '
    'enumerates the concerns and the mitigations available out of the box.',
    BODY))

flow.append(Paragraph('7a. What Flask does (in one paragraph)', H2))
flow.append(Paragraph(
    'A ~280-line Python script (<font face="Courier">server.py</font>) '
    'using Flask. Listens on '
    '<font face="Courier">localhost:5000</font> behind an nginx reverse '
    'proxy. Serves the static <font face="Courier">index.html</font>; '
    'exposes a small JSON API used by the in-page admin tabs '
    '(Events Queue, AI Categorize trigger, Suggestions review, Scraper '
    'Sources). Stateless across restarts — every request reads/writes '
    'JSON files on disk; no database, no in-memory sessions.',
    BODY))

flow.append(Paragraph('7b. Concerns IT will raise (and pre-built mitigations)', H2))
sec_concerns = [
    ['Concern', 'Default state', 'Mitigation', 'Effort'],
    ['Admin endpoints have no login wall',
     'Gated by network only — listens on localhost; admin UI shown when host = 127.0.0.1 or URL contains ?admin=1 on a whitelisted hostname.',
     'Add HTTP Basic auth at the nginx layer in front of /admin* paths. Optionally upgrade to SAML/OIDC via oauth2-proxy if the county has SSO.',
     '5–30 min'],
    ['Endpoints execute subprocesses (Python scraper, Chromium)',
     '/api/scrape and /api/ai/categorize spawn child processes in a background thread on admin click.',
     'Run Flask as an unprivileged user (ncexp) with a restricted shell; subprocesses inherit the same low-privilege identity. The only callable scripts are inside /opt/ncexp/scraper/, not arbitrary code.',
     '15 min'],
    ['Long-running Python process owns credentials and writes files',
     'Anthropic API key in config.py (mode 0600). Writes to scraper_output/*.json.',
     'systemd hardening: NoNewPrivileges=true, ProtectSystem=strict, ProtectHome=true, PrivateTmp=true, ReadWritePaths=/opt/ncexp/scraper_output, CapabilityBoundingSet=. Confines the process to its data directory.',
     '30 min'],
    ['Containerization / process isolation',
     'Bare-metal Python process under systemd.',
     'Optional: run in Docker/Podman with --read-only root, --cap-drop=ALL, volume-mount only scraper_output. Standard county-IT practice on many sites.',
     '1–2 hours'],
    ['Public suggestion form open to abuse',
     'POST /api/suggestions accepts visitor input (name/email/description). Input length is capped server-side but no rate limit.',
     'Add nginx limit_req zone — 30 req/min/IP on /api/suggestions. Optional: Cloudflare Turnstile (free, no cookies) on the form.',
     '30 min'],
    ['Python / Flask / Selenium / Chromium supply chain',
     'Pip packages pinned in requirements.txt. Chromium installed via apt.',
     'Schedule pip-audit weekly (or use Dependabot if mirrored to county GitHub). unattended-upgrades for OS + Chromium CVEs. Quarterly pip-outdated review.',
     '15 min setup'],
    ['No audit trail of admin actions',
     'Admin clicks (approve/dismiss) are appended to events.json but not separately logged with operator identity.',
     'Add nginx access log retention; if Basic auth is enabled, the username is logged per request. Optional: emit per-action audit entries to /var/log/ncexp-admin.log.',
     '15 min'],
    ['What if Flask itself is compromised?',
     'Worst-case: attacker has read/write on scraper_output/ + can call the Anthropic API.',
     'Provider snapshots provide hour-level rollback. Anthropic key has a $5/month hard spending cap. No PII to exfiltrate. systemd hardening limits filesystem damage to the data directory.',
     'baseline + monitoring'],
]
flow.append(build_table(sec_concerns,
    col_widths=[1.5*inch, 1.8*inch, 2.7*inch, 0.8*inch],
    body_size=8))

flow.append(Paragraph('7c. The "split deployment" option for strictest policies', H2))
flow.append(Paragraph(
    'If county policy treats the dynamic Flask layer as too sensitive to '
    'host on its own server, the site can be split:',
    BODY))
split_rows = [
    ['Public site', 'Static HTML/JS', 'Hosted on a CDN or county static-web bucket. Zero attack surface. No Python, no inbound port management, no patch cadence.'],
    ['Admin layer', 'Flask + scraper', 'Hosted on a small internal VM the chamber operator reaches via VPN or county intranet only. Public internet never sees the Flask process.'],
    ['Data hand-off', 'Generated artifact', 'Admin layer publishes its scraper_output/events.json to the public bucket on a cron (rsync, aws s3 cp, or equivalent). Visitors fetch it from the CDN.'],
]
flow.append(build_table(split_rows,
    col_widths=[1.2*inch, 1.5*inch, 4.1*inch],
    body_size=8.5))
flow.append(Paragraph(
    '<b>Trade-off:</b> the "Suggest a venue" public form needs SOME live '
    'endpoint — either keep a tiny suggestions-only Flask on a hardened '
    'sub-host, replace it with a static form-to-email service (Formspree, '
    'Tally, Microsoft Forms), or remove the public form entirely. '
    'Everything else works in the split model.',
    BODY))

flow.append(Paragraph('7d. What runs entirely without Flask', H2))
flow.append(Paragraph(
    'The visitor experience is HTML/JS only. With Flask off and only the '
    'static <font face="Courier">index.html</font> + a periodically-updated '
    '<font face="Courier">scraper_output/events.json</font> available, '
    'visitors get: theme browsing, vibe-pill filtering, day-by-day '
    'itinerary builder, opt-in localStorage save, share-link generation, '
    'map view, print, and Suggested Experiences browse. The only things '
    'that require Flask are the chamber-side admin tools and the public '
    'Suggest-a-venue submission form.',
    BODY))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: POLICY-BLOCK IMPACT MATRIX
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('8. Policy-Block Impact Matrix', H1))
flow.append(Paragraph(
    'For each external service, what breaks if county policy disallows it '
    'and what the workaround is. Sites continues to function in nearly all '
    'cases; severity scales with how visitor-facing the lost feature is.',
    BODY))

impact_rows = [
    ['If this is blocked…', 'Impact', 'Workaround'],
    ['Outbound HTTPS to api.anthropic.com',
     'AI Categorize button stops working. Newly-scraped events keep their raw scraper-assigned tags — area/venue/quality refinement disabled. Operators must hand-tag events with bad metadata.',
     'Hide the AI Categorize button in admin; rely on operator review. Lose ~20–30% of automated tagging accuracy. No site-visitor impact.'],
    ['Outbound HTTPS to plausible.io',
     'Aggregate metrics (visitor counts, itinerary build rate) unavailable. Site continues to work; chamber loses operational visibility into usage.',
     'Self-host Plausible on the same VPS (Docker image, ~$0 incremental). Or use the file-based access-log analytics built into nginx. Or disable analytics entirely.'],
    ['Outbound HTTPS to fonts.googleapis.com (visitor browsers)',
     'Custom fonts fall back to system serif/sans-serif. Site readable, slightly less branded look.',
     'Self-host the Playfair Display + Josefin Sans WOFF2 files from /static/fonts and update the @font-face rules in index.html. ~20 KB extra payload per visitor.'],
    ['Outbound HTTPS to cdnjs.cloudflare.com (Leaflet)',
     'Map view button fails. Itinerary still works; visitors lose the "View on Map" feature.',
     'Self-host Leaflet (one JS + one CSS file, ~150 KB total) from /static/leaflet/.'],
    ['Outbound HTTPS to images.unsplash.com',
     '~30 theme-card photos fail to load. Theme cards render with their gradient backgrounds; site still usable.',
     'Download Unsplash photos once, commit to /static/photos/, update the THEMES[] array. ~3 MB one-time addition to the repo.'],
    ['Outbound HTTPS to scraper source sites (KVMR, Trumba, etc.)',
     'No new events arrive. Existing events keep showing until they expire; the catalog goes stale within ~2 weeks.',
     'Operate in static-catalog mode: chamber adds events manually via the admin UI or the Suggestions form. Loss of ~95% of event volume.'],
    ['Outbound HTTPS to acme-v02.api.letsencrypt.org (cert renewal)',
     'TLS certificate eventually expires (90-day life). Site becomes inaccessible after expiry.',
     'Use a county-internal CA, or a paid cert from a vendor the county already uses (DigiCert, Sectigo). Renewal becomes a manual quarterly task.'],
    ['Inbound HTTPS (443) from public internet',
     'Site is internal-only. Visitors outside the county network can\'t reach it.',
     'Re-purpose as a kiosk / intranet tool. Defeats the public-facing visitor-planning value; not recommended unless that is the intent.'],
    ['Cron / Task Scheduler permitted to run as a service account',
     'Scrapes never run automatically. Queue stays empty. Auto-prune of past events never fires.',
     'Operator manually clicks "Update Now" in the admin UI 1–3 times per week. Adds ~5 min/week to operator load.'],
    ['Outbound SMTP (any provider)',
     'No effect on this platform — we don\'t send email. Reserved for future alerting only.',
     'N/A — feature not yet built.'],
]
flow.append(build_table(impact_rows,
    col_widths=[1.8*inch, 2.5*inch, 2.5*inch],
    body_size=8))

flow.append(Paragraph(
    '<b>The "everything off but the lights" scenario:</b> with every '
    'optional outbound service blocked (no Anthropic, no Plausible, no '
    'CDNs, no scrape, no Let\'s Encrypt), the platform still functions '
    'as a manually-curated static catalog hosted on the county server '
    'with a county-internal certificate. Operator time roughly doubles '
    '(~1 hour/week instead of 30 min) because manual tagging and manual '
    'event entry replace the automated paths. No visitor-facing feature '
    'is broken; only the data-freshness rate drops.',
    BODY))

flow.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9: APPENDICES
# ─────────────────────────────────────────────────────────────────────────────
flow.append(Paragraph('9. Appendices', H1))

flow.append(Paragraph('A. systemd unit file', H2))
flow.append(Preformatted("""[Unit]
Description=Nevada County Experience admin server
After=network.target

[Service]
Type=simple
User=ncexp
WorkingDirectory=/opt/ncexp
Environment="ANTHROPIC_API_KEY=sk-ant-..."
ExecStart=/opt/ncexp/.venv/bin/python server.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target""", CODE))

flow.append(Paragraph('B. nginx vhost (HTTPS, with redirect from HTTP)', H2))
flow.append(Preformatted("""server {
    listen 80;
    server_name ncexperience.county.gov;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ncexperience.county.gov;

    ssl_certificate     /etc/letsencrypt/live/ncexperience.county.gov/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ncexperience.county.gov/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;

    # Strong default headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options    "nosniff"  always;
    add_header X-Frame-Options           "SAMEORIGIN" always;

    location / {
        proxy_pass       http://127.0.0.1:5000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}""", CODE))

flow.append(Paragraph('C. Daily JSON backup script', H2))
flow.append(Preformatted("""#!/bin/bash
# /opt/ncexp/bin/backup-daily.sh — run by root cron at 04:00
set -euo pipefail
STAMP=$(date +%Y%m%d)
DEST=/var/backups/ncexp
mkdir -p "$DEST"
tar czf "$DEST/ncexp-$STAMP.tgz" /opt/ncexp/scraper_output /opt/ncexp/config.py
# Retain 14 days
find "$DEST" -name 'ncexp-*.tgz' -mtime +14 -delete
# Optional: mirror to county SAN / S3
# rsync -a "$DEST/" backupserver:/backups/ncexp/""", CODE))

flow.append(Paragraph('D. Reference URLs', H2))
ref_rows = [
    ['Document / artifact', 'Where'],
    ['Live demo (currently on GitHub Pages)', 'https://liammlrb-eng.github.io/nevada-county-experiences/'],
    ['Source repository',                    'https://github.com/liammlrb-eng/nevada-county-experiences'],
    ['Operator day-to-day guide',            'operator_guide.pdf (in this bundle)'],
    ['Long-form pitch &amp; UX rationale',   'demo_pitch.pdf (in this bundle)'],
    ['Slide deck',                           'demo_pitch.pptx (in this bundle)'],
]
flow.append(build_table(ref_rows,
    col_widths=[2.8*inch, 4.0*inch],
    body_size=8.5))

flow.append(Spacer(1, 8))
flow.append(section_rule())
flow.append(Spacer(1, 6))
flow.append(Paragraph(
    'Document version: generated automatically from <font face="Courier">'
    'generate_it_brief.py</font>. Regenerate after any change to dependency '
    'list, hosting scenarios, or migration plan.',
    SMALL))

# ─────────────────────────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────────────────────────
doc.build(flow)
print(f'Wrote: {out_path}')

# Mirror to pitch_resources/ for the chat-share bundle
import shutil
mirror = project_root / 'pitch_resources' / 'it_migration_brief.pdf'
if mirror.parent.exists():
    shutil.copy2(out_path, mirror)
    print(f'Mirrored: {mirror}')

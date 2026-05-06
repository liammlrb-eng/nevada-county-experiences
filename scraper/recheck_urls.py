#!/usr/bin/env python3
"""
Re-checks only the pending URL issues in updates.json with a longer timeout.
Run this instead of the full scraper when you just want to verify flagged links.
"""

import os, sys, json, time, requests
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)
UPDATES_F  = os.path.join(ROOT_DIR, 'scraper_output', 'updates.json')

TIMEOUT    = 25   # seconds per request
HEADERS    = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def check_url(url):
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True, headers=HEADERS)
        return r.status_code < 400, str(r.status_code)
    except Exception:
        pass
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True, headers=HEADERS, stream=True)
        r.close()
        return r.status_code < 400, str(r.status_code)
    except Exception as e:
        return False, str(e)[:80]

def main():
    with open(UPDATES_F, 'r', encoding='utf-8') as f:
        items = json.load(f)

    pending = [i for i in items if i.get('status') == 'pending']
    print(f"Re-checking {len(pending)} pending URLs (timeout={TIMEOUT}s)...\n")

    changed = 0
    for idx, item in enumerate(pending, 1):
        url  = item['old_value']
        name = item['name']
        alive, status = check_url(url)
        tag = 'OK  ' if alive else 'DEAD'
        print(f"  [{idx:2d}/{len(pending)}] {tag} [{status:>5}]  {name}")

        if alive:
            # Site is actually up — mark dismissed (scraper was too impatient)
            for i in items:
                if i['id'] == item['id'] and i['field'] == item['field']:
                    i['status']     = 'dismissed'
                    i['http_status'] = status
                    i['checked']    = datetime.now().strftime('%Y-%m-%d')
            changed += 1

        time.sleep(0.5)

    with open(UPDATES_F, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    still_pending = sum(1 for i in items if i.get('status') == 'pending')
    print(f"\nDone. {changed} items cleared (were just slow).")
    print(f"{still_pending} genuinely dead links remain.")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
customize.py — flag-driven demo edit of the captured My Learning tabs.

  --name NAME            display name everywhere (greeting, avatars, profile menu)
  --course KEYWORD ...    which specialization(s) to show, all marked Complete
                          (repeatable; keyword or full slug). Default: devops fintech

Only specializations present in the capture can be shown:
  devops | fintech | financial-services | defi | content-creation | anatomy

Run after build_site.py + localize_assets.py  (rebuild.sh forwards flags here).
"""
import argparse
import os
import re
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
TABDIR = os.path.join(HERE, 'site', 'tabs')
TABS = ['IN_PROGRESS', 'COMPLETED', 'SAVED', 'CERTIFICATES']
BLUE = "#0056D2"
IBM_LOGO = "/_res/5130a1da15a2db91.png"
CERT_POOL = ['/_res/d440b7510002359a.bin', '/_res/45a0d3d1d4b3d388.bin']  # devops cert, cloud cert

SPEC_NAME = {
    'devops-and-software-engineering': 'IBM DevOps and Software Engineering',
    'fintech': 'FinTech: Finance Industry Transformation and Regulation',
    'digital-transformation-financial-services': 'Digital Transformation in Financial Services',
    'decentralized-finance-duke': 'Decentralized Finance (DeFi): The Future of Finance',
    'content-creation-tiktok-youtube-instagram-facebook': 'Content Creation for TikTok, YouTube, Instagram, Facebook',
    'anatomy': 'Anatomy',
    'innovation-and-entrepreneurship': 'Innovation and entrepreneurship',
}

# Synthesized spec (not in the capture) — built from the reference screenshots.
ENT_SLUG = 'innovation-and-entrepreneurship'
ENT_COURSES = ['Entrepreneurial Mindset', 'Organizational innovation and creativity',
               'Design and innovation of business model', 'Corporate Entrepreneurship']
ENT_LEARN = ['entrepreneurial-mindset', 'organizational-innovation-creativity',
             'business-model-innovation', 'corporate-entrepreneurship']
COURSE_KEYWORDS = {
    'devops': 'devops-and-software-engineering', 'software-engineering': 'devops-and-software-engineering',
    'ibm-devops': 'devops-and-software-engineering', 'ibm': 'devops-and-software-engineering',
    'fintech': 'fintech',
    'finance': 'digital-transformation-financial-services',
    'financial-services': 'digital-transformation-financial-services',
    'digital-transformation': 'digital-transformation-financial-services',
    'defi': 'decentralized-finance-duke', 'decentralized-finance': 'decentralized-finance-duke',
    'content-creation': 'content-creation-tiktok-youtube-instagram-facebook',
    'content': 'content-creation-tiktok-youtube-instagram-facebook',
    'tiktok': 'content-creation-tiktok-youtube-instagram-facebook',
    'anatomy': 'anatomy',
    'entrepreneurship': 'innovation-and-entrepreneurship',
    'innovation': 'innovation-and-entrepreneurship',
    'innovation-and-entrepreneurship': 'innovation-and-entrepreneurship',
}

CTA_HTML = (
    '<div style="display:flex;align-items:center;justify-content:flex-end;gap:16px;height:100%">'
    f'<a role="button" tabindex="0" style="background:{BLUE};color:#fff;padding:9px 16px;'
    'border-radius:4px;font-weight:600;font-size:14px;line-height:1;text-decoration:none;'
    'white-space:nowrap;cursor:pointer"><span class="cds-button-label">Add to LinkedIn</span></a>'
    f'<a role="button" tabindex="0" href="#" style="color:{BLUE};font-weight:600;font-size:14px;'
    'text-decoration:none;white-space:nowrap;cursor:pointer">'
    '<span class="cds-button-label">View certificate</span></a></div>'
)
THUMB = ("display:block;opacity:1;visibility:visible;width:48px;height:48px;object-fit:cover;"
         "object-position:left top;background:#fff;border:1px solid #e5e7eb;border-radius:8px;position:static")
STATS = [("24", "daily goals completed"), ("312", "items completed"), ("3,480", "minutes learned")]


# ---------------------------------------------------------------- helpers
def slug_of(mod):
    a = mod.select_one('a[href*="/specializations/"]')
    return a['href'].split('/specializations/')[-1].split('?')[0].strip('/') if a else ''


def cert_for(slug, idx):
    return {'devops-and-software-engineering': CERT_POOL[0],
            'fintech': CERT_POOL[1]}.get(slug, CERT_POOL[idx % len(CERT_POOL)])


def synth_entrepreneurship(soup):
    """Build the 'Innovation and entrepreneurship' spec by cloning a real 4-course
    block and relabeling it (the capture doesn't contain this spec)."""
    tmpl = next((m for m in soup.select('div.rc-PathwayCardModule')
                 if slug_of(m) == 'fintech' and len(m.select('a[href*="/learn/"]')) == 4), None)
    if tmpl is None:
        tmpl = next((m for m in soup.select('div.rc-PathwayCardModule')
                     if len(m.select('a[href*="/learn/"]')) == 4), None)
    if tmpl is None:
        return False
    tslug = slug_of(tmpl)
    tcourses = [a.get_text(strip=True) for a in tmpl.select('a[data-click-key*="course_card_link"]')]
    tlearn = []
    for s in re.findall(r'/learn/([a-z0-9-]+)/', str(tmpl)):
        if s not in tlearn:
            tlearn.append(s)

    html = str(tmpl)
    html = html.replace('/specializations/' + tslug, '/specializations/' + ENT_SLUG)
    tname = SPEC_NAME.get(tslug, '')
    if tname:
        html = html.replace(tname, SPEC_NAME[ENT_SLUG])
    for old, new in zip(tcourses[:4], ENT_COURSES):
        html = html.replace(old, new)
    for old, new in zip(tlearn[:4], ENT_LEARN):   # trailing slash avoids prefix clashes
        html = html.replace('/learn/' + old + '/', '/learn/' + new + '/')

    block = BeautifulSoup(html, 'html.parser').find('div', class_='rc-PathwayCardModule')
    tmpl.insert_after(block)
    return True


def resolve_courses(args):
    out = []
    for c in args:
        key = c.strip().lower()
        slug = COURSE_KEYWORDS.get(key) or (key if key in SPEC_NAME else None)
        if not slug:
            slug = next((s for s in SPEC_NAME if key in s), None)
        if slug and slug not in out:
            out.append(slug)
        elif not slug:
            print(f"[!] unknown course '{c}' — available: "
                  f"{', '.join(sorted(set(COURSE_KEYWORDS)))}")
    return out or ['devops-and-software-engineering', 'fintech']


# ---------------------------------------------------------------- row completion
def check_div(soup):
    d = soup.new_tag("div"); d["class"] = ["css-hetlg"]
    d.append(BeautifulSoup(
        '<svg aria-hidden="true" class="css-fa3pa9" fill="none" focusable="false" height="20"'
        ' viewBox="0 0 20 20" width="20"><path d="M8.104 12.313l6.23-6.23a.73.73 0 011.063 0 .73'
        '.73 0 01.007 1.058l-6.758 6.776a.73.73 0 01-1.063 0l-2.979-2.98a.73.73 0 010-1.062.733'
        '.733 0 011.063 0l2.437 2.438z" fill="currentColor"></path></svg>', 'html.parser'))
    return d


def make_complete(row, soup):
    meta_wrap = row.select_one('.rc-PathwayCourseMetadata')
    if meta_wrap and not meta_wrap.select_one('.css-hetlg'):
        meta_wrap.insert(0, check_div(soup))
    meta = row.select_one('.css-a7rx60')
    if meta:
        meta['style'] = 'display:flex;flex-wrap:wrap;gap:4px;align-items:center'
        if not re.search(r'·\s*Complete\b', meta.get_text(' ', strip=True)):
            for p in meta.find_all('p', recursive=False)[2:]:
                p.decompose()
            done = soup.new_tag('p'); done['class'] = ['css-vac8rf']; done.string = 'Complete'
            meta.append(done)
    pb = row.find(attrs={'data-testid': 'progress-bar'})
    if pb:
        (pb.parent or pb).decompose()
    for sec in row.find_all('section'):
        sec.decompose()
    slot = row.select_one('.css-1tijkpe')
    if slot is not None:
        slot.clear()
        slot.append(BeautifulSoup(CTA_HTML, 'html.parser'))


def keep_specs_complete(soup, keep):
    kept = []
    for m in soup.select('div.rc-PathwayCardModule'):
        if slug_of(m) in keep:
            kept.append(m)
            for row in m.select('[class*="PathwayCardCourseItemModule"]'):
                make_complete(row, soup)
        else:
            t = m
            while t.parent and t.parent.get_text(strip=True) == m.get_text(strip=True):
                t = t.parent
            t.decompose()
    for c in soup.select('div.rc-CourseCardModule'):
        t = c
        while t.parent and t.parent.get_text(strip=True) == c.get_text(strip=True):
            t = t.parent
        t.decompose()
    for e in sorted([e for e in soup.find_all(['div', 'nav', 'section'])
                     if e.get_text(strip=True).startswith('Results per page')
                     and len(e.get_text(strip=True)) < 160], key=lambda e: len(str(e)), reverse=True)[:1]:
        e.decompose()
    # order kept to match the requested order
    kept.sort(key=lambda m: keep.index(slug_of(m)) if slug_of(m) in keep else 99)
    return kept


# ---------------------------------------------------------------- sidebar / stats
def fix_recent_certs(soup, keep):
    hdr = soup.find(string=re.compile('Recent Certificates'))
    if not hdr:
        return
    widget = hdr
    for _ in range(3):
        widget = widget.parent
    items = widget.select('.css-3nqq3r')
    if not items:
        return
    template = items[0]
    parent = template.parent
    for it in items:
        it.extract()
    for i, slug in enumerate(keep[:3]):
        node = BeautifulSoup(str(template), 'html.parser')
        title = node.select_one('.css-puj6la')
        if title:
            title.string = SPEC_NAME.get(slug, slug)
        img = node.find('img')
        if img:
            img['src'] = cert_for(slug, i)
            img['alt'] = SPEC_NAME.get(slug, slug) + ' certificate'
            img['style'] = THUMB
        parent.append(node)


def update_stats(soup):
    hdr = soup.find(string=re.compile(r'Last 4 weeks'))
    if not hdr:
        return
    w = hdr
    for _ in range(3):
        w = w.parent
    nums = w.select('.css-49l1ij')
    for i, (val, _l) in enumerate(STATS):
        if i < len(nums):
            nums[i].string = val
    for val, label in STATS:
        for node in soup.find_all(string=re.compile(r'^\s*[0-9,]+\s+' + re.escape(label) + r'\s*$')):
            node.replace_with(f'{val} {label}')


# ---------------------------------------------------------------- completed tab
def banner_html(mod, idx):
    slug = slug_of(mod)
    name = SPEC_NAME.get(slug, mod.select_one('a[href*="/specializations/"]').get_text(strip=True))
    logo = mod.find('img')
    logo_src = logo['src'] if logo and logo.get('src') else IBM_LOGO
    return f'''<div style="background:#eaf1fb;border-radius:12px;padding:28px 32px;display:flex;
align-items:center;gap:28px;margin:16px 0;justify-content:space-between">
  <div style="flex:1;min-width:0">
    <img src="{logo_src}" alt="" style="height:34px;margin-bottom:14px">
    <h2 style="font-size:23px;line-height:1.3;font-weight:700;color:#1f1f1f;margin:0 0 18px">
      Congratulations on earning your {name} Professional Certificate!</h2>
    <div style="display:flex;gap:12px">
      <a role="button" tabindex="0" style="background:{BLUE};color:#fff;padding:11px 20px;border-radius:4px;
         font-weight:600;font-size:15px;text-decoration:none;cursor:pointer">
        <span class="cds-button-label">Add to LinkedIn</span></a>
      <a role="button" tabindex="0" href="#" style="color:{BLUE};background:#fff;border:1px solid {BLUE};
         padding:10px 20px;border-radius:4px;font-weight:600;font-size:15px;text-decoration:none;cursor:pointer">
        <span class="cds-button-label">View career certificate</span></a>
    </div>
  </div>
  <img src="{cert_for(slug, idx)}" alt="{name} certificate"
       style="width:240px;max-width:40%;border:1px solid #d7dee8;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.08)">
</div>'''


def build_completed(kept):
    path = os.path.join(TABDIR, 'COMPLETED.html')
    comp = BeautifulSoup(open(path, encoding='utf-8', errors='replace').read(), 'lxml')
    ccm = comp.select('div.rc-CourseCardModule')
    if not ccm:
        return
    container = ccm[0]
    while container.parent and len(container.parent.select('div.rc-CourseCardModule')) == len(ccm):
        container = container.parent
    container.clear()
    for i, m in enumerate(kept):
        block = BeautifulSoup(str(m), 'html.parser')
        host = block.select_one('.pathway-card-container') or block
        host.insert_before(BeautifulSoup(banner_html(m, i), 'html.parser'))
        container.append(block)
    open(path, 'w', encoding='utf-8').write(str(comp))


# ---------------------------------------------------------------- certificates tab
def build_certificates(kept):
    path = os.path.join(TABDIR, 'CERTIFICATES.html')
    soup = BeautifulSoup(open(path, encoding='utf-8', errors='replace').read(), 'lxml')
    cards = soup.select('div[data-testid="certificate-card"]')
    if not cards:
        return
    template = cards[0]
    grid = template.parent
    for c in cards:
        c.extract()
    for i, m in enumerate(kept):
        slug = slug_of(m)
        name = SPEC_NAME.get(slug, slug)
        node = BeautifulSoup(str(template), 'html.parser')
        t = node.select_one('.css-1rbd4p0')
        if t:
            t.string = name
        img = node.find('img')
        if img:
            img['src'] = cert_for(slug, i)
            img['alt'] = name + ' certificate'
        grid.append(node)
    # heading "Course" -> "Specialization" (these are professional certs now)
    for h in soup.find_all('h2'):
        if h.get_text(strip=True) == 'Course':
            h.string = 'Specialization'
            break
    open(path, 'w', encoding='utf-8').write(str(soup))


# ---------------------------------------------------------------- name
def apply_name(path, name):
    soup = BeautifulSoup(open(path, encoding='utf-8', errors='replace').read(), 'lxml')
    for sp in soup.select('span.cds-Avatar-initialText'):
        sp.string = name[0].upper()
    for el in soup.find_all(attrs={'aria-label': re.compile('atharva', re.I)}):
        el['aria-label'] = re.sub('atharva bobde', name, el['aria-label'], flags=re.I)
    html = str(soup)
    html = re.sub(r'Atharva Bobde', lambda m: name, html)
    html = re.sub(r'atharva', lambda m: name, html, flags=re.I)
    open(path, 'w', encoding='utf-8').write(html)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='atharva')
    ap.add_argument('--course', action='append', default=None)
    a = ap.parse_args()
    keep = resolve_courses(a.course or ['devops', 'fintech'])
    print(f"[*] name='{a.name}'  courses={keep}")

    ip_path = os.path.join(TABDIR, 'IN_PROGRESS.html')
    ip = BeautifulSoup(open(ip_path, encoding='utf-8', errors='replace').read(), 'lxml')
    if ENT_SLUG in keep:
        if synth_entrepreneurship(ip):
            print("[+] synthesized 'Innovation and entrepreneurship' spec")
    kept = keep_specs_complete(ip, keep)
    fix_recent_certs(ip, [slug_of(m) for m in kept])
    update_stats(ip)
    open(ip_path, 'w', encoding='utf-8').write(str(ip))
    print(f"[+] IN_PROGRESS: {len(kept)} specs complete")

    build_completed(kept)
    build_certificates(kept)
    print(f"[+] COMPLETED + CERTIFICATES rebuilt for {len(kept)} specs")

    for tab in TABS:
        apply_name(os.path.join(TABDIR, f'{tab}.html'), a.name)
    print(f"[+] name applied to all tabs: {a.name}")


if __name__ == '__main__':
    main()

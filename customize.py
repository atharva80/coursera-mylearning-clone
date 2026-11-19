#!/usr/bin/env python3
"""
customize.py — flag-driven demo edit of the captured My Learning tabs, wired to
the real certificate assets produced by build_certs.py (site/_res/certs.json).

  --name NAME             display name everywhere (greeting, avatars, profile menu)
  --course KEYWORD ...     which specialization(s) to show, all marked Complete
                          (repeatable; keyword or full slug). Default: devops fintech

Per course it wires the real certificate:
  * each course row gets  Add to LinkedIn  +  View certificate (opens the real PDF)
  * Completed-tab banners + Recent Certificates use the real specialization cert
  * Certificates & Badges lists every real course cert + the specialization certs

Run after build_site.py + localize_assets.py + build_certs.py.
"""
import argparse
import json
import os
import re
import urllib.parse
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
TABDIR = os.path.join(HERE, 'site', 'tabs')
RES = os.path.join(HERE, 'site', '_res')
TABS = ['IN_PROGRESS', 'COMPLETED', 'SAVED', 'CERTIFICATES']
BLUE = "#0056D2"
IBM_LOGO = "/_res/5130a1da15a2db91.png"
CERT_POOL = ['/_res/d440b7510002359a.bin', '/_res/45a0d3d1d4b3d388.bin']  # fallback only

MONTHS = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
          'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}

# real certificate manifest (built by build_certs.py)
try:
    MANIFEST = json.load(open(os.path.join(RES, 'certs.json'), encoding='utf-8'))['specs']
except (OSError, ValueError):
    MANIFEST = {}

SPEC_NAME = {
    'devops-and-software-engineering': 'IBM DevOps and Software Engineering',
    'fintech': 'Financial Technology (Fintech) Innovations',
    'digital-transformation-financial-services': 'Digital Transformation in Financial Services',
    'decentralized-finance-duke': 'Decentralized Finance (DeFi): The Future of Finance',
    'content-creation-tiktok-youtube-instagram-facebook': 'Content Creation for TikTok, YouTube, Instagram, Facebook',
    'anatomy': 'Anatomy',
    'innovation-and-entrepreneurship': 'Innovation and entrepreneurship',
}

# Relabel the captured HKUST "fintech" block into the real U-Michigan path.
RELABEL = {
    'fintech': {
        'old_name': 'FinTech: Finance Industry Transformation and Regulation',
        'old_logo': '/_res/2443029dd1339873.png',
        'old_courses': ['FinTech Foundations and Overview',
                        'FinTech Security and Regulation (RegTech)',
                        'FinTech Risk Management',
                        'FinTech Disruptive Innovation: Implications for Society'],
    },
}

# Synthesized spec (not in the capture) — kept for flag compatibility.
ENT_SLUG = 'innovation-and-entrepreneurship'
ENT_COURSES = ['Entrepreneurial Mindset', 'Organizational innovation and creativity',
               'Design and innovation of business model', 'Corporate Entrepreneurship']
ENT_LEARN = ['entrepreneurial-mindset', 'organizational-innovation-creativity',
             'business-model-innovation', 'corporate-entrepreneurship']

COURSE_KEYWORDS = {
    'devops': 'devops-and-software-engineering', 'software-engineering': 'devops-and-software-engineering',
    'ibm-devops': 'devops-and-software-engineering', 'ibm': 'devops-and-software-engineering',
    'fintech': 'fintech', 'financial-technology': 'fintech', 'michigan': 'fintech',
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

THUMB = ("display:block;opacity:1;visibility:visible;width:48px;height:48px;object-fit:cover;"
         "object-position:center top;background:#fff;border:1px solid #e5e7eb;border-radius:6px;position:static")
STATS = [("26", "daily goals completed"), ("19", "items completed"), ("3,840", "minutes learned")]


# ---------------------------------------------------------------- manifest helpers
def spec_entry(slug):
    return MANIFEST.get(slug)


def spec_img(slug):
    e = spec_entry(slug)
    return e['spec']['img'] if e else CERT_POOL[0]


def spec_thumb(slug):
    e = spec_entry(slug)
    return e['spec']['thumb'] if e else CERT_POOL[0]


def spec_pdf(slug):
    e = spec_entry(slug)
    return e['spec']['pdf'] if e else '#'


def course_cert(slug, idx):
    e = spec_entry(slug)
    if e and 0 <= idx < len(e['courses']):
        return e['courses'][idx]
    return None


def display_name(slug):
    e = spec_entry(slug)
    return e['name'] if e else SPEC_NAME.get(slug, slug)


def partner_of(slug):
    e = spec_entry(slug)
    return e['partner'] if e else 'IBM'


def logo_of(slug):
    e = spec_entry(slug)
    return e['logo'] if e else IBM_LOGO


def linkedin_url(name, org, date):
    parts = (date or '').split()
    mon = MONTHS.get(parts[0], 11) if parts else 11
    yr = parts[1] if len(parts) > 1 else '2026'
    return ('https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME'
            '&name=' + urllib.parse.quote(name or 'Coursera Certificate')
            + '&organizationName=' + urllib.parse.quote(org or 'Coursera')
            + '&issueMonth=' + str(mon) + '&issueYear=' + str(yr))


# ---------------------------------------------------------------- helpers
def slug_of(mod):
    a = mod.select_one('a[href*="/specializations/"]')
    return a['href'].split('/specializations/')[-1].split('?')[0].strip('/') if a else ''


def relabel_block(mod, slug):
    """Rewrite the captured block's spec title, course titles and partner logo."""
    cfg = RELABEL.get(slug)
    e = spec_entry(slug)
    if not cfg or not e:
        return mod
    html = str(mod)
    html = html.replace(cfg['old_name'], e['name'])
    for old, new in zip(cfg['old_courses'], [c['title'] for c in e['courses']]):
        html = html.replace(old, new)
    html = html.replace(cfg['old_logo'], e['logo'])
    node = BeautifulSoup(html, 'html.parser').find('div', class_='rc-PathwayCardModule')
    mod.replace_with(node)
    return node


def synth_entrepreneurship(soup):
    """Clone a real 4-course block into the 'Innovation and entrepreneurship' spec."""
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
    for old, new in zip(tlearn[:4], ENT_LEARN):
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
            print(f"[!] unknown course '{c}' — available: {', '.join(sorted(set(COURSE_KEYWORDS)))}")
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


def course_cta_html(li_name, org, pdf, date):
    view = pdf or '#'
    tgt = ' target="_blank" rel="noopener"' if pdf and pdf != '#' else ''
    return (
        '<div style="display:flex;align-items:center;justify-content:flex-end;gap:18px;height:100%">'
        f'<a role="button" tabindex="0" href="{linkedin_url(li_name, org, date)}" target="_blank" rel="noopener" '
        f'style="background:{BLUE};color:#fff;padding:9px 16px;border-radius:4px;font-weight:600;'
        'font-size:14px;line-height:1;text-decoration:none;white-space:nowrap;cursor:pointer">'
        '<span class="cds-button-label">Add to LinkedIn</span></a>'
        f'<a role="button" tabindex="0" href="{view}"{tgt} style="color:{BLUE};font-weight:600;'
        'font-size:14px;text-decoration:none;white-space:nowrap;cursor:pointer">'
        '<span class="cds-button-label">View certificate</span></a></div>'
    )


def make_complete(row, soup, slug, idx):
    cc = course_cert(slug, idx)
    li_name = cc['title'] if cc else display_name(slug)
    pdf = cc['pdf'] if cc else spec_pdf(slug)
    date = cc['date'] if cc else (spec_entry(slug) or {}).get('spec', {}).get('date', 'November 2026')

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
    slot = row.select_one('.rc-CompletedCourseCTAs') or row.select_one('.css-1tijkpe')
    if slot is not None:
        slot.clear()
        slot.append(BeautifulSoup(course_cta_html(li_name, partner_of(slug), pdf, date), 'html.parser'))


def keep_specs_complete(soup, keep):
    kept = []
    for m in soup.select('div.rc-PathwayCardModule'):
        if slug_of(m) in keep:
            if slug_of(m) in RELABEL:
                m = relabel_block(m, slug_of(m))
            kept.append(m)
            for i, row in enumerate(m.select('[class*="PathwayCardCourseItemModule"]')):
                make_complete(row, soup, slug_of(m), i)
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
    kept.sort(key=lambda m: keep.index(slug_of(m)) if slug_of(m) in keep else 99)
    return kept


# ---------------------------------------------------------------- sidebar / stats
def fix_recent_certs(soup, keep):
    # the Recent Certificates list repeats one `.css-uvcl0b` row per credential
    rows = soup.select('.css-uvcl0b')
    if not rows:
        return
    template = rows[0]
    parent = template.parent
    for r in rows:
        r.extract()
    for slug in keep[:4]:                       # final specialization certs only
        node = BeautifulSoup(str(template), 'html.parser').find(True)
        title = node.select_one('.css-puj6la')
        if title:
            title.string = display_name(slug)
        img = node.find('img')
        if img:
            img['src'] = spec_thumb(slug)
            img['alt'] = display_name(slug) + ' certificate'
            img['style'] = THUMB
        for a in node.find_all('a'):
            txt = a.get_text(strip=True).lower()
            if 'view' in txt:
                a['href'] = spec_pdf(slug)
            elif 'linkedin' in txt:
                a['href'] = linkedin_url(display_name(slug), partner_of(slug), 'November 2026')
            a['target'] = '_blank'; a['rel'] = 'noopener'
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
def banner_html(slug):
    name = display_name(slug)
    return f'''<div style="background:#eaf1fb;border-radius:12px;padding:28px 32px;display:flex;
align-items:center;gap:28px;margin:16px 0;justify-content:space-between">
  <div style="flex:1;min-width:0">
    <img src="{logo_of(slug)}" alt="{partner_of(slug)}" style="height:30px;margin-bottom:14px">
    <h2 style="font-size:23px;line-height:1.3;font-weight:700;color:#1f1f1f;margin:0 0 18px">
      Congratulations on earning your {name} Professional Certificate!</h2>
    <div style="display:flex;gap:12px">
      <a role="button" tabindex="0" href="{linkedin_url(name, partner_of(slug), 'November 2026')}"
         target="_blank" rel="noopener" style="background:{BLUE};color:#fff;padding:11px 20px;border-radius:4px;
         font-weight:600;font-size:15px;text-decoration:none;cursor:pointer">
        <span class="cds-button-label">Add to LinkedIn</span></a>
      <a role="button" tabindex="0" href="{spec_pdf(slug)}" target="_blank" rel="noopener"
         style="color:{BLUE};background:#fff;border:1px solid {BLUE};
         padding:10px 20px;border-radius:4px;font-weight:600;font-size:15px;text-decoration:none;cursor:pointer">
        <span class="cds-button-label">View career certificate</span></a>
    </div>
  </div>
  <a href="{spec_pdf(slug)}" target="_blank" rel="noopener" style="flex-shrink:0">
    <img src="{spec_img(slug)}" alt="{name} certificate"
       style="width:240px;max-width:40%;border:1px solid #d7dee8;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.08)"></a>
</div>'''


def build_completed(kept):
    path = os.path.join(TABDIR, 'COMPLETED.html')
    comp = BeautifulSoup(open(path, encoding='utf-8', errors='replace').read(), 'lxml')
    ccm = comp.select('div.rc-CourseCardModule')
    if not ccm:
        return
    # the shared row that holds every captured course-card wrapper
    def contains_all(a):
        return all(a in list(x.parents) for x in ccm)
    row = ccm[0].parent
    while row and not contains_all(row):
        row = row.parent
    anchor = ccm[0]
    while anchor.parent is not row and anchor.parent is not None:
        anchor = anchor.parent
    # insert the completed spec blocks (banner + block) where the cards were
    for m in kept:
        slug = slug_of(m)
        block = BeautifulSoup(str(m), 'html.parser')
        host = block.select_one('.pathway-card-container') or block
        host.insert_before(BeautifulSoup(banner_html(slug), 'html.parser'))
        anchor.insert_before(block)
    # drop every original standalone course card (with its wrapper)
    for c in ccm:
        node = c
        while node.parent is not row and node.parent is not None:
            node = node.parent
        node.decompose()
    _remove_pagers(comp)
    open(path, 'w', encoding='utf-8').write(str(comp))


# ---------------------------------------------------------------- certificates tab
def fill_cert_card(node, title, thumb, pdf, partner, date):
    t = node.select_one('.css-1rbd4p0')
    if t:
        t.string = title
    img = node.find('img')
    if img:
        img['src'] = thumb
        img['alt'] = title + ' certificate'
        img['style'] = ('width:100%;height:auto;display:block;border:1px solid #e5e7eb;'
                        'border-radius:4px;aspect-ratio:auto')
    for a in node.find_all('a'):
        txt = a.get_text(strip=True).lower()
        if 'linkedin' in txt:
            a['href'] = linkedin_url(title, partner, date); a['target'] = '_blank'; a['rel'] = 'noopener'
        elif 'view' in txt:
            a['href'] = pdf; a['target'] = '_blank'; a['rel'] = 'noopener'
    for s in node.find_all(string=True):
        st = s.strip()
        if st == 'IBM':
            s.replace_with(partner)
        elif st.startswith('Completed'):
            s.replace_with('Completed ' + date)
    return node


def _clean_spec_title(name):
    return re.sub(r'\s+(Specialization|Professional Certificate)\s*$', '', name).strip()


def _remove_pagers(soup):
    # the frozen page can't paginate — drop every inert "Results per page" control
    for p in soup.select('div.css-5p2hcg'):
        wrap = p
        while wrap.parent and len(wrap.parent.get_text(' ', strip=True)) < 120:
            wrap = wrap.parent
        wrap.decompose()
    for node in list(soup.find_all(string=re.compile(r'Results per page'))):
        target = None
        anc = node.parent
        for _ in range(8):
            if anc and anc.name and len(anc.get_text(' ', strip=True)) < 120:
                target = anc
            anc = anc.parent if anc else None
        if target is not None:
            target.decompose()


def build_certificates(kept):
    path = os.path.join(TABDIR, 'CERTIFICATES.html')
    soup = BeautifulSoup(open(path, encoding='utf-8', errors='replace').read(), 'lxml')
    cards = soup.select('div[data-testid="certificate-card"]')
    if not cards:
        return
    template_li = cards[0].parent          # <li class="cds-grid-item ..."> — the grid cell
    row = template_li.parent               # <ul> — the responsive grid row
    section = row.parent                    # <section> wrapping the row
    for li in row.find_all('li', recursive=False):
        li.extract()
    _remove_pagers(soup)

    def make_li(title, thumb, pdf, partner, date):
        li = BeautifulSoup(str(template_li), 'html.parser').find('li')
        card = li.select_one('div[data-testid="certificate-card"]')
        fill_cert_card(card, title, thumb, pdf, partner, date)
        return li

    spec_slugs = [slug_of(m) for m in kept if spec_entry(slug_of(m))]
    course_hdr = next((h for h in soup.find_all('h2') if h.get_text(strip=True) == 'Course'), None)

    # --- Specialization section (cloned section+row), before the Course heading ---
    if course_hdr is not None and spec_slugs:
        spec_hdr = BeautifulSoup(str(course_hdr), 'html.parser').find('h2')
        spec_hdr.string = 'Specialization'
        spec_section = BeautifulSoup(str(section), 'html.parser').find(True)
        spec_row = spec_section.find('ul')
        for li in spec_row.find_all('li', recursive=False):
            li.extract()
        for slug in spec_slugs:
            spec_row.append(make_li(_clean_spec_title(display_name(slug)), spec_thumb(slug), spec_pdf(slug),
                                    partner_of(slug), (spec_entry(slug) or {}).get('spec', {}).get('date', 'November 2026')))
        course_hdr.insert_before(spec_hdr)
        course_hdr.insert_before(spec_section)

    # --- Course section (every course cert) into the original row ---
    for m in kept:
        slug = slug_of(m)
        e = spec_entry(slug)
        if not e:
            continue
        for c in e['courses']:
            row.append(make_li(c['title'], c['thumb'], c['pdf'], e['partner'], c['date']))
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
    if not MANIFEST:
        print("[!] certs.json missing — run build_certs.py first (cert previews will fall back)")

    ip_path = os.path.join(TABDIR, 'IN_PROGRESS.html')
    ip = BeautifulSoup(open(ip_path, encoding='utf-8', errors='replace').read(), 'lxml')
    if ENT_SLUG in keep and synth_entrepreneurship(ip):
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

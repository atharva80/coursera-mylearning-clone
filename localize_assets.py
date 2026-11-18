#!/usr/bin/env python3
"""
localize_assets.py — pull any still-external <img> assets into site/_res and
rewrite the refs, so nothing loads over http (mixed-content) or off-site.
Run after build_site.py. Public assets only; no auth.
"""
import hashlib, os, re, mimetypes
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
RES = os.path.join(SITE, "_res")
TABS = ["IN_PROGRESS", "COMPLETED", "SAVED", "CERTIFICATES"]

EXT = {"image/png":".png","image/jpeg":".jpg","image/gif":".gif","image/svg+xml":".svg",
       "image/webp":".webp","image/x-icon":".ico"}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(), r.headers.get("Content-Type","")

def ext_for(ct, url):
    ct=(ct or "").split(";")[0].strip().lower()
    return EXT.get(ct) or mimetypes.guess_extension(ct) or os.path.splitext(url.split("?")[0])[1] or ".png"

def main():
    # collect external img src across all tabs
    htmls = {t: open(os.path.join(SITE,"tabs",f"{t}.html"),encoding="utf-8",errors="replace").read() for t in TABS}
    urls = set()
    for h in htmls.values():
        for m in re.finditer(r'<img\b[^>]*\bsrc=(["\'])(https?://[^"\']+)\1', h, re.I):
            urls.add(m.group(2))
    print(f"[*] {len(urls)} external img url(s)")
    mapping = {}
    for u in sorted(urls):
        https = u.replace("http://","https://",1)
        got = None
        for cand in (https, u):
            try:
                data, ct = fetch(cand); got=(data,ct); break
            except Exception as e:
                last=e
        if not got:
            print(f"    [skip] {u[:70]} ({last})"); continue
        data, ct = got
        fn = hashlib.sha1(u.encode()).hexdigest()[:16] + ext_for(ct, u)
        open(os.path.join(RES, fn),"wb").write(data)
        mapping[u] = "/_res/"+fn
        print(f"    [ok] {u.split('/')[-1][:48]} -> {fn} ({len(data)//1024}KB)")
    # rewrite (also upgrade any we couldn't fetch to https so they at least try securely)
    for t in TABS:
        h = htmls[t]
        for u,local in mapping.items():
            h = h.replace(u, local)
        h = re.sub(r'(<img\b[^>]*\bsrc=["\'])http://', r'\1https://', h, flags=re.I)
        htmls[t] = h
    print(f"[done] localized {len(mapping)} asset(s)")

    # --- cert-preview linking: make every "<name> certificate preview" img use
    #     the real cert image that the Certificates tab already loaded ---
    cert_map = {}   # name-keyword -> /_res/<file>
    for m in re.finditer(r'<img\b[^>]*>', htmls["CERTIFICATES"]):
        tag=m.group(0)
        alt=re.search(r'alt="([^"]*certificate preview[^"]*)"',tag,re.I)
        src=re.search(r'src="(/_res/[^"]+)"',tag)
        if alt and src:
            key=re.sub(r'\s+certificate preview.*','',alt.group(1),flags=re.I).strip().lower()
            cert_map[key]=src.group(1)
    print(f"[*] cert previews: {len(cert_map)} -> {list(cert_map)}")

    def relink(tag):
        alt=re.search(r'alt="([^"]*certificate preview[^"]*)"',tag,re.I)
        if not alt: return tag
        key=re.sub(r'\s+certificate preview.*','',alt.group(1),flags=re.I).strip().lower()
        if key in cert_map:
            tag=re.sub(r'(src=")[^"]*(")', r'\1'+cert_map[key]+r'\2', tag, count=1)
            # ONLY the tiny sidebar thumbnails (class css-13kuv6l) get forced sizing;
            # the big cert cards (css-1y73cpw) keep their native layout.
            if 'css-13kuv6l' in tag:
                style='opacity:1;visibility:visible;width:48px;height:48px;object-fit:cover;background:#fff;border:1px solid #e5e7eb;border-radius:8px;position:static'
                if re.search(r'style="', tag):
                    tag=re.sub(r'style="([^"]*)"', r'style="\1;'+style+'"', tag, count=1)
                else:
                    tag=tag[:-1]+f' style="{style}">'
            return tag
        return tag

    fixed=0
    for t in TABS:
        new=re.sub(r'<img\b[^>]*>', lambda m: relink(m.group(0)), htmls[t])
        fixed += new.count('certificate preview') if t!="CERTIFICATES" else 0
        open(os.path.join(SITE,"tabs",f"{t}.html"),"w",encoding="utf-8").write(new)
    print(f"[done] relinked cert previews across tabs")

if __name__ == "__main__":
    main()

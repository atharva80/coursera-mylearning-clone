#!/usr/bin/env python3
"""
build_site.py — assemble capture/tabs/*.mhtml into one navigable static site.

  site/_res/<hash><ext>     shared asset pool (deduped across tabs by URL hash)
  site/tabs/<TAB>.html      each tab, scripts stripped, /_res/ absolute paths,
                            + a tiny injected nav shim so tabs click through

server.py routes ?myLearningTab=<TAB> -> site/tabs/<TAB>.html and /_res/* here.
"""
import email, hashlib, mimetypes, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
TABSRC = os.path.join(HERE, "capture", "tabs")
SITE = os.path.join(HERE, "site")
RES = os.path.join(SITE, "_res")
TABS = ["IN_PROGRESS", "COMPLETED", "SAVED", "CERTIFICATES"]

EXT = {"text/css":".css","image/png":".png","image/jpeg":".jpg","image/gif":".gif",
       "image/svg+xml":".svg","image/webp":".webp","font/woff2":".woff2","font/woff":".woff",
       "application/font-woff2":".woff2","application/font-woff":".woff","font/ttf":".ttf",
       "image/x-icon":".ico","image/vnd.microsoft.icon":".ico"}

NAV_SHIM = """
<script>
(function(){
  var MAP={'In Progress':'IN_PROGRESS','Completed':'COMPLETED','Saved':'SAVED','Certificates & Badges':'CERTIFICATES'};
  function go(t){location.href='/organizations/viot/my-learning?myLearningTab='+t;}
  var SKIP=/^(Add to LinkedIn|View certificate|View career certificate|Resume|Get started|Credit|Course|IBM)$/i;
  function clean(s){return (s||'').replace(/\\s+/g,' ').trim();}
  function nearestTitle(el){
    var sels=['a[href*="/learn/"]','a[data-click-key*="card_link"]','h1,h2,h3,h4','[class*="itle"]'];
    for(var n=el,i=0;i<9 && n;i++,n=n.parentElement){
      if(!n.querySelectorAll) continue;
      for(var s=0;s<sels.length;s++){
        var nodes=n.querySelectorAll(sels[s]);
        for(var k=0;k<nodes.length;k++){
          var t=clean(nodes[k].textContent);
          if(t && t.length>3 && !SKIP.test(t)) return t;
        }
      }
    }
    return '';
  }
  function linkedin(name){
    window.open('https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME'
      +'&name='+encodeURIComponent(name||'Coursera Certificate')
      +'&organizationName='+encodeURIComponent('Coursera')+'&issueYear=2026&issueMonth=11','_blank','noopener');
  }
  function realHref(el){
    var a=el.closest&&el.closest('a[href]');
    var h=a&&a.getAttribute('href');
    return (h && h!=='#' && h.indexOf('javascript:')!==0) ? h : null;
  }
  // fallback only — real cert links carry their own href (wired by customize.py)
  function viewCert(){ window.open('/_res/cert_devops_spec.pdf','_blank','noopener'); }

  document.addEventListener('click',function(e){
    var el=e.target;
    for(var i=0;i<6 && el;i++,el=el.parentElement){
      var txt=clean(el.textContent);
      if(MAP[txt]!==undefined){e.preventDefault();e.stopPropagation();go(MAP[txt]);return;}
      if(/^Add to LinkedIn$/i.test(txt)){
        if(realHref(el)) return;                 // real LinkedIn add link, let it open
        e.preventDefault();e.stopPropagation();linkedin(nearestTitle(el));return;}
      if(/^View (career )?certificate$/i.test(txt)){
        if(realHref(el)) return;                 // real cert PDF link, let it open
        e.preventDefault();e.stopPropagation();viewCert();return;}
    }
  },true);

  /* ---------- time-based greeting ---------- */
  function greet(){
    var h=new Date().getHours();
    var g=h<12?'Good morning':(h<17?'Good afternoon':'Good evening');
    var el=document.querySelector('h1.css-1xoj1ft')||document.querySelector('h1');
    if(el && /good (morning|afternoon|evening)/i.test(el.textContent)){
      el.textContent=el.textContent.replace(/good (morning|afternoon|evening)/i,g);
    }
  }

  /* ---------- live calendar: highlight today's date ---------- */
  function calToday(){
    var now=new Date(); if(now.getFullYear()!==2026||now.getMonth()!==10) return; // Nov 2026 only
    var d=now.getDate();
    // clear the captured today-circle
    document.querySelectorAll('span.css-xfcwga').forEach(function(s){
      s.className='css-vac8rf'; var w=s.parentElement; if(w) w.className='css-qp23nx';
    });
    // find today's cell and apply the circle
    document.querySelectorAll('div.css-o1szhl span').forEach(function(s){
      if(clean(s.textContent)===String(d)){
        s.className='css-xfcwga'; var w=s.parentElement; if(w) w.className='css-qqnvx4';
      }
    });
  }

  /* ---------- profile dropdown menu ---------- */
  function displayName(){
    var h1=document.querySelector('h1.css-1xoj1ft')||document.querySelector('h1');
    var m=h1&&h1.textContent.match(/,\\s*(.+?)\\s*$/);
    return m?m[1].trim():'there';
  }
  function profileMenu(){
    var btn=document.querySelector('button[aria-label^="User dropdown menu"]')
         || document.querySelector('header button:last-of-type');
    if(!btn) return;
    var nm=displayName(), initial=(nm[0]||'A').toUpperCase();
    var menu=document.createElement('div');
    menu.id='viot-profile-menu';
    menu.style.cssText='position:fixed;top:56px;right:16px;width:240px;background:#fff;'
      +'border:1px solid #e5e7eb;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.18);'
      +'z-index:99999;display:none;font-family:inherit;overflow:hidden;padding:8px 0';
    menu.innerHTML=
      '<div style="display:flex;flex-direction:column;align-items:center;padding:16px 12px 12px">'
      +'<div style="width:40px;height:40px;border-radius:50%;background:#0a1744;color:#fff;'
      +'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px">'+initial+'</div>'
      +'<div style="margin-top:8px;font-weight:700;font-size:16px;color:#1f1f1f">Hi, '+nm+'</div></div>'
      +'<div style="height:1px;background:#eee;margin:4px 0"></div>'
      +['My Learning','My Purchases','Settings','Updates','Help Center','Language: English','Log Out']
        .map(function(x){return '<a href="#" class="viot-mi" style="display:block;padding:11px 20px;'
          +'color:#1f1f1f;text-decoration:none;font-size:15px">'+x+'</a>';}).join('');
    document.body.appendChild(menu);
    menu.querySelectorAll('.viot-mi').forEach(function(a){
      a.addEventListener('mouseenter',function(){a.style.background='#f3f4f6';});
      a.addEventListener('mouseleave',function(){a.style.background='';});
      a.addEventListener('click',function(e){e.preventDefault();
        if(a.textContent==='My Learning') go('IN_PROGRESS'); else menu.style.display='none';});
    });
    btn.addEventListener('click',function(e){
      e.preventDefault();e.stopPropagation();
      menu.style.display=menu.style.display==='none'?'block':'none';
    },true);
    document.addEventListener('click',function(e){
      if(menu.style.display==='block' && !menu.contains(e.target) && !btn.contains(e.target))
        menu.style.display='none';
    });
  }

  function init(){ greet(); calToday(); profileMenu(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
})();
</script>
"""


def strip_junk(html):
    # drop invisible tracker iframes (their cid: src triggers xdg-open) and
    # neutralise any leftover cid: references from the mhtml capture
    html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", html, flags=re.I | re.S)
    html = re.sub(r"<iframe\b[^>]*/?>", "", html, flags=re.I)
    html = re.sub(r'(src|href)=(["\'])cid:[^"\']*\2', r'\1=\2about:blank\2', html, flags=re.I)
    # remove CDS loading skeletons — frozen page, they never resolve and cover content
    html = re.sub(r'<span\b[^>]*cds-Skeleton[^>]*>.*?</span>', '', html, flags=re.I | re.S)
    return html


def ext_for(ct, url):
    ct = (ct or "").split(";")[0].strip().lower()
    if ct in EXT: return EXT[ct]
    return mimetypes.guess_extension(ct or "") or os.path.splitext(url.split("?")[0])[1] or ".bin"


def rewrite(text, mapping):
    for url in sorted(mapping, key=len, reverse=True):
        if url in text:
            text = text.replace(url, mapping[url])
    return text


def unpack_one(tab, url_to_local, css_jobs):
    path = os.path.join(TABSRC, f"{tab}.mhtml")
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f)
    parts = [p for p in msg.walk() if not p.is_multipart()]
    root = next((p for p in parts if p.get_content_type() == "text/html"), parts[0])
    for p in parts:
        if p is root:
            continue
        loc = p.get("Content-Location")
        if not loc:
            continue
        ct = p.get_content_type()
        h = hashlib.sha1(loc.encode()).hexdigest()[:16]
        fname = h + ext_for(ct, loc)
        fpath = os.path.join(RES, fname)
        if not os.path.exists(fpath):            # dedupe shared assets
            with open(fpath, "wb") as out:
                out.write(p.get_payload(decode=True) or b"")
            if ct == "text/css":
                css_jobs.append(fpath)
        url_to_local[loc] = "/_res/" + fname     # absolute
    html = (root.get_payload(decode=True) or b"").decode("utf-8", "replace")
    return html


def main():
    os.makedirs(RES, exist_ok=True)
    os.makedirs(os.path.join(SITE, "tabs"), exist_ok=True)
    url_to_local, css_jobs, roots = {}, [], {}

    for tab in TABS:
        roots[tab] = unpack_one(tab, url_to_local, css_jobs)

    # rewrite all CSS once (shared pool)
    for fpath in css_jobs:
        txt = open(fpath, encoding="utf-8", errors="replace").read()
        open(fpath, "w", encoding="utf-8").write(rewrite(txt, url_to_local))

    out = {}
    for tab, html in roots.items():
        html = rewrite(html, url_to_local)
        html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
        html = re.sub(r"<script\b[^>]*/>", "", html, flags=re.I)
        html = strip_junk(html)
        html = html.replace("<noscript>", "").replace("</noscript>", "")
        out[tab] = html

    # union of every tab's stylesheet links, so markup copied between tabs
    # (e.g. spec blocks moved onto the Completed tab) always has its CSS.
    css_link = re.compile(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', re.I)
    href_re = re.compile(r'href=["\'](/_res/[^"\']+\.css)["\']', re.I)
    all_links = []  # (href, tag) in first-seen order
    seen = set()
    for tab in TABS:
        for tag in css_link.findall(out[tab]):
            h = href_re.search(tag)
            if h and h.group(1) not in seen:
                seen.add(h.group(1)); all_links.append((h.group(1), tag))

    for tab in TABS:
        html = out[tab]
        have = {m.group(1) for m in href_re.finditer(html)}
        missing = "".join(tag for href, tag in all_links if href not in have)
        if missing:
            html = html.replace("</head>", missing + "</head>", 1) if "</head>" in html else missing + html
        html = html.replace("</body>", NAV_SHIM + "</body>") if "</body>" in html else html + NAV_SHIM
        open(os.path.join(SITE, "tabs", f"{tab}.html"), "w", encoding="utf-8").write(html)
        print(f"[+] site/tabs/{tab}.html  ({len(html)//1024} KB)")

    print(f"[+] {len(os.listdir(RES))} shared assets in site/_res/")
    print("[done] run: sudo python3 server.py")


if __name__ == "__main__":
    main()

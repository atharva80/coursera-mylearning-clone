#!/usr/bin/env python3
"""
unpack.py — turn capture/my_learning.mhtml into a self-contained static site that
renders identically with NO backend, then it can be served under coursera.org.

What it does:
  - parses the MHTML multipart (root DOM + every CSS/font/image the browser loaded)
  - writes each resource under site/_res/<hash><ext>
  - rewrites every absolute URL in the HTML + CSS to the local resource path
  - strips <script> tags from the root HTML so the React bundle can't re-hydrate
    and wipe the captured DOM (we want the frozen, already-rendered page)
  - writes site/index.html

Then:  sudo python3 server.py   (point translate_path at ./site/index.html)
"""

import email
import hashlib
import mimetypes
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MHTML = os.path.join(HERE, "capture", "my_learning.mhtml")
SITE = os.path.join(HERE, "site")
RES = os.path.join(SITE, "_res")

EXT = {
    "text/css": ".css", "image/png": ".png", "image/jpeg": ".jpg",
    "image/gif": ".gif", "image/svg+xml": ".svg", "image/webp": ".webp",
    "font/woff2": ".woff2", "font/woff": ".woff", "application/font-woff2": ".woff2",
    "application/font-woff": ".woff", "font/ttf": ".ttf", "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
}


def ext_for(ctype, url):
    ct = (ctype or "").split(";")[0].strip().lower()
    if ct in EXT:
        return EXT[ct]
    guessed = mimetypes.guess_extension(ct or "") or os.path.splitext(url.split("?")[0])[1]
    return guessed or ".bin"


def main():
    if not os.path.exists(MHTML):
        sys.exit(f"no {MHTML} — run grab.py first")
    os.makedirs(RES, exist_ok=True)

    with open(MHTML, "rb") as f:
        msg = email.message_from_binary_file(f)

    parts = [p for p in msg.walk() if not p.is_multipart()]
    if not parts:
        sys.exit("mhtml had no parts")

    # first text/html part is the root document
    root = next((p for p in parts if (p.get_content_type() == "text/html")), parts[0])

    url_to_local = {}
    css_parts = []
    for p in parts:
        if p is root:
            continue
        loc = p.get("Content-Location")
        if not loc:
            continue
        ctype = p.get_content_type()
        payload = p.get_payload(decode=True) or b""
        h = hashlib.sha1(loc.encode()).hexdigest()[:16]
        fname = h + ext_for(ctype, loc)
        with open(os.path.join(RES, fname), "wb") as out:
            out.write(payload)
        local = "_res/" + fname
        url_to_local[loc] = local
        if ctype == "text/css":
            css_parts.append((os.path.join(RES, fname), payload, loc))

    # rewrite url() refs inside each CSS file
    for path, payload, _loc in css_parts:
        text = payload.decode("utf-8", "replace")
        text = rewrite(text, url_to_local)
        with open(path, "w", encoding="utf-8") as out:
            out.write(text)

    # root HTML
    html = (root.get_payload(decode=True) or b"").decode("utf-8", "replace")
    html = rewrite(html, url_to_local)
    # kill scripts so the SPA can't rehydrate over our frozen DOM
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    html = re.sub(r"<script\b[^>]*/>", "", html, flags=re.I)
    # neutralise noscript wrappers (show their content)
    html = html.replace("<noscript>", "").replace("</noscript>", "")

    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as out:
        out.write(html)

    print(f"[+] {len(url_to_local)} resources -> {RES}")
    print(f"[+] {os.path.join(SITE, 'index.html')}")
    print("[next] point server.py at ./site and serve under coursera.org")


def rewrite(text, mapping):
    # longest URLs first so a prefix match never clobbers a longer one
    for url in sorted(mapping, key=len, reverse=True):
        if url in text:
            text = text.replace(url, mapping[url])
    return text


if __name__ == "__main__":
    main()

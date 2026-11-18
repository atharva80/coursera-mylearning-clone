#!/usr/bin/env python3
"""
grab.py — drive a headless Chrome over CDP with the user's Coursera auth cookie,
render the real /my-learning page, and capture a pixel-perfect snapshot.

Outputs (into ./capture/):
  my_learning.mhtml   — single-file bundle of the rendered DOM + ALL resources
                        (CSS, fonts, images) exactly as the browser painted them
  my_learning.html    — the post-React outerHTML (for inspection / unpacking)
  my_learning.png     — full-page screenshot (reference for pixel diffing)
  cookies_used.txt    — which cookies were injected

Cookie intake (first that exists wins):
  - env  CAUTH=...            (single value)
  - file ./.cookie           ("CAUTH=..." or bare value, or many name=value lines)

Usage:
  python3 grab.py                                   # default my-learning URL
  python3 grab.py "https://www.coursera.org/..."    # any logged-in URL
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import base64
from urllib.request import urlopen

try:
    from websocket import create_connection  # websocket-client
except ImportError:
    sys.exit("need websocket-client:  pip install websocket-client")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "capture")
URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://www.coursera.org/organizations/viot/my-learning?myLearningTab=IN_PROGRESS"
DEBUG_PORT = 9333
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")

BROWSER = shutil.which("google-chrome") or shutil.which("google-chrome-stable") \
    or shutil.which("chromium") or shutil.which("microsoft-edge")


# ---------------------------------------------------------------- cookies
def load_cookies():
    """Return list of {name,value} to inject for .coursera.org."""
    jar = []
    env = os.environ.get("CAUTH")
    if env:
        jar.append(("CAUTH", env.strip()))
    cfile = os.path.join(HERE, ".cookie")
    if os.path.exists(cfile):
        raw = open(cfile, encoding="utf-8", errors="replace").read().strip()
        for line in raw.splitlines():
            line = line.strip().rstrip(";")
            if not line:
                continue
            if "=" in line:
                name, _, val = line.partition("=")
                jar.append((name.strip(), val.strip()))
            else:
                jar.append(("CAUTH", line))  # bare value
    # dedupe by name, last wins
    seen = {}
    for n, v in jar:
        seen[n] = v
    return [{"name": n, "value": v} for n, v in seen.items()]


# ---------------------------------------------------------------- CDP client
class CDP:
    def __init__(self, ws_url):
        self.ws = create_connection(ws_url, max_size=None, timeout=120)
        self._id = 0

    def call(self, method, params=None, timeout=120):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        self.ws.settimeout(timeout)
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            # ignore events

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def wait_port(port, secs=15):
    for _ in range(secs * 10):
        try:
            with socket.create_connection(("127.0.0.1", port), 0.2):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main():
    if not BROWSER:
        sys.exit("no chrome/chromium/edge found")
    cookies = load_cookies()
    if not cookies:
        sys.exit("no cookie. put the CAUTH value in ./.cookie  (or export CAUTH=...)")
    os.makedirs(OUT, exist_ok=True)

    profile = os.path.join(OUT, "_profile")
    shutil.rmtree(profile, ignore_errors=True)
    os.makedirs(profile, exist_ok=True)

    args = [
        BROWSER,
        "--headless=new",
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile}",
        "--no-first-run", "--no-default-browser-check",
        "--disable-gpu", "--hide-scrollbars",
        "--window-size=1440,2400",
        f"--user-agent={UA}",
        "about:blank",
    ]
    print(f"[*] launching {os.path.basename(BROWSER)} headless on :{DEBUG_PORT} ...")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_port(DEBUG_PORT):
            sys.exit("CDP port never opened")
        time.sleep(0.5)
        # discover the page target
        targets = json.loads(urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json").read())
        page = next(t for t in targets if t["type"] == "page")
        cdp = CDP(page["webSocketDebuggerUrl"])

        cdp.call("Network.enable")
        cdp.call("Page.enable")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": 1440, "height": 2200, "deviceScaleFactor": 2,
            "mobile": False,
        })

        # inject auth cookies for both apex + www
        for c in cookies:
            for dom in (".coursera.org", "www.coursera.org"):
                cdp.call("Network.setCookie", {
                    "name": c["name"], "value": c["value"],
                    "domain": dom, "path": "/",
                    "secure": True, "httpOnly": True,
                    "sameSite": "Lax",
                })
        print(f"[*] injected cookies: {', '.join(c['name'] for c in cookies)}")

        print(f"[*] navigating: {URL}")
        cdp.call("Page.navigate", {"url": URL}, timeout=60)

        # settle: wait for the SPA to finish painting the learning list
        print("[*] waiting for React render ...")
        deadline = time.time() + 40
        ready = False
        while time.time() < deadline:
            time.sleep(1.2)
            r = cdp.call("Runtime.evaluate", {
                "returnByValue": True,
                "expression": (
                    "(function(){var t=document.body?document.body.innerText:'';"
                    "return {len:(document.body?document.body.innerHTML.length:0),"
                    "learn:/My Learning|In Progress|Completed|Certificates/i.test(t),"
                    "login:/log\\s?in|sign\\s?in|password/i.test(t) && t.length<4000};})()"
                ),
            })["result"]["value"]
            if r.get("login"):
                print("[!] page looks like a LOGIN wall — cookie not accepted. "
                      "re-copy a fresh CAUTH (and add CAUTHU/csrf if present).")
            if r.get("learn") and r.get("len", 0) > 20000:
                ready = True
                break
        print(f"[*] render {'OK' if ready else 'TIMEOUT (capturing anyway)'}")
        time.sleep(2)  # let fonts/images finish

        # 1) MHTML — the pixel-perfect single-file bundle
        snap = cdp.call("Page.captureSnapshot", {"format": "mhtml"}, timeout=120)
        mhtml_path = os.path.join(OUT, "my_learning.mhtml")
        open(mhtml_path, "w", encoding="utf-8").write(snap["data"])
        print(f"[+] {mhtml_path}  ({len(snap['data'])//1024} KB)")

        # 2) rendered outerHTML
        html = cdp.call("Runtime.evaluate", {
            "returnByValue": True,
            "expression": "document.documentElement.outerHTML",
        })["result"]["value"]
        html_path = os.path.join(OUT, "my_learning.html")
        open(html_path, "w", encoding="utf-8").write(html)
        print(f"[+] {html_path}  ({len(html)//1024} KB)")

        # 3) full-page screenshot
        shot = cdp.call("Page.captureScreenshot", {
            "format": "png", "captureBeyondViewport": True,
        }, timeout=120)
        png_path = os.path.join(OUT, "my_learning.png")
        open(png_path, "wb").write(base64.b64decode(shot["data"]))
        print(f"[+] {png_path}")

        open(os.path.join(OUT, "cookies_used.txt"), "w").write(
            "\n".join(c["name"] for c in cookies))
        cdp.close()
        print("\n[done] capture/ has the mhtml bundle, html, and screenshot.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
capture_tabs.py — one authed headless Chrome session, capture all four My Learning
tabs as full MHTML snapshots (+ screenshots). Reuses ./.cookie (CAUTH).

Writes capture/tabs/<TAB>.mhtml and capture/tabs/<TAB>.png
"""
import base64, json, os, shutil, socket, subprocess, sys, time
from urllib.request import urlopen
from websocket import create_connection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "capture", "tabs")
PORT = 9335
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")
BROWSER = shutil.which("google-chrome") or shutil.which("chromium")
BASE = "https://www.coursera.org/organizations/viot/my-learning?myLearningTab="
TABS = ["IN_PROGRESS", "COMPLETED", "SAVED", "CERTIFICATES"]


def cauth():
    f = os.path.join(HERE, ".cookie")
    raw = open(f).read().strip()
    return raw.split("=", 1)[1] if raw.startswith("CAUTH=") else raw


class CDP:
    def __init__(self, ws):
        self.ws = create_connection(ws, max_size=None, timeout=120); self._id = 0
    def call(self, m, p=None, timeout=120):
        self._id += 1; i = self._id
        self.ws.send(json.dumps({"id": i, "method": m, "params": p or {}}))
        self.ws.settimeout(timeout)
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == i:
                if "error" in r: raise RuntimeError(f"{m}: {r['error']}")
                return r.get("result", {})


def wait_port(p, s=20):
    for _ in range(s*10):
        try:
            with socket.create_connection(("127.0.0.1", p), 0.2): return True
        except OSError: time.sleep(0.1)
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    prof = os.path.join(HERE, "capture", "_profile2"); shutil.rmtree(prof, ignore_errors=True)
    args = [BROWSER, "--headless=new", f"--remote-debugging-port={PORT}",
            f"--user-data-dir={prof}", "--no-first-run", "--disable-gpu",
            "--hide-scrollbars", "--window-size=1440,2600", f"--user-agent={UA}", "about:blank"]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_port(PORT): sys.exit("no cdp port")
        time.sleep(0.5)
        tgt = next(t for t in json.loads(urlopen(f"http://127.0.0.1:{PORT}/json").read()) if t["type"]=="page")
        cdp = CDP(tgt["webSocketDebuggerUrl"])
        cdp.call("Network.enable"); cdp.call("Page.enable")
        cdp.call("Emulation.setDeviceMetricsOverride",
                 {"width":1440,"height":2400,"deviceScaleFactor":2,"mobile":False})
        val = cauth()
        for dom in (".coursera.org","www.coursera.org"):
            cdp.call("Network.setCookie", {"name":"CAUTH","value":val,"domain":dom,
                     "path":"/","secure":True,"httpOnly":True,"sameSite":"Lax"})
        for tab in TABS:
            url = BASE + tab
            print(f"[*] {tab} ...")
            cdp.call("Page.navigate", {"url": url}, timeout=60)
            # settle
            dl = time.time()+30; ok=False
            while time.time() < dl:
                time.sleep(1.1)
                r = cdp.call("Runtime.evaluate", {"returnByValue":True,"expression":
                    "(function(){var t=document.body?document.body.innerText:'';"
                    "return {len:document.body?document.body.innerHTML.length:0,"
                    "tabs:/In Progress|Completed|Certificates/i.test(t)};})()"})["result"]["value"]
                if r.get("tabs") and r.get("len",0)>15000: ok=True; break
            time.sleep(2.2)
            snap = cdp.call("Page.captureSnapshot", {"format":"mhtml"}, timeout=120)
            open(os.path.join(OUT, f"{tab}.mhtml"),"w",encoding="utf-8").write(snap["data"])
            shot = cdp.call("Page.captureScreenshot", {"format":"png","captureBeyondViewport":True}, timeout=120)
            open(os.path.join(OUT, f"{tab}.png"),"wb").write(base64.b64decode(shot["data"]))
            print(f"    {'OK' if ok else 'timeout'}  mhtml {len(snap['data'])//1024}KB")
        print("[done] capture/tabs/")
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()


if __name__ == "__main__":
    main()

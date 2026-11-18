# Coursera "My Learning" — Local Demo Clone

A pixel-perfect, **offline** reproduction of the Coursera *My Learning* page
(`/organizations/viot/my-learning`), served from your own machine so the browser's
address bar reads **`https://www.coursera.org/...`** with a valid padlock.

It is built from a one-time snapshot of a real logged-in page (the rendered DOM +
every stylesheet, font and image), frozen into static HTML. No Coursera backend,
no network calls, no login — everything is local. Think of it as a high-fidelity
screenshot you can click through.

> **Scope / honesty:** this is a local demo for your own use. It runs entirely on
> `127.0.0.1`, serves *your own* captured data, and changes nothing on Coursera.
> The name on the baked certificate *images* is whatever was captured; see
> [Limitations](#limitations).

---

## How it works

Three moving parts:

1. **DNS override** — a line in your OS `hosts` file points `coursera.org` and
   `www.coursera.org` at `127.0.0.1`.
2. **Trusted TLS cert** — a self-signed cert for `coursera.org` is added to your
   browser's trust store, so HTTPS shows a valid padlock instead of a warning.
3. **Static server** — `server.py` serves the frozen tabs on ports 80/443 and
   maps `?myLearningTab=` to the right captured tab.

The only OS-specific parts are **where the hosts file lives** and **how certs are
trusted** — the included Python scripts handle both automatically.

---

## Repo layout

```
coursera_clone/
├── README.md                 ← you are here
├── requirements.txt          ← pip dependencies
│
├── build.py                  ← rebuild the static site (cross-platform)   ── run these
├── gen_cert.py               ← make the self-signed cert (cross-platform)
├── setup.py                  ← trust cert + DNS override (Win/mac/Linux)
├── teardown.py               ← undo setup.py
├── server.py                 ← the local HTTPS/HTTP server
│
├── build_site.py             ← stage 1: unpack snapshots → site/tabs/*.html   ── pipeline
├── localize_assets.py        ← stage 2: pull external images local
├── customize.py              ← stage 3: apply --name / --course, complete specs
│
├── grab.py / capture_tabs.py ← (optional) re-capture fresh data with a CAUTH cookie
│
├── capture/tabs/*.mhtml      ← the source snapshots the build reads
├── site/                     ← generated static site (git-ignored)
├── rebuild.sh                ← Linux/macOS shortcut for build.py
│
└── setup.sh / teardown.sh    ← Linux-only bash equivalents of setup.py/teardown.py
```

---

## Prerequisites (all platforms)

- **Python 3.8+** — check with `python --version` (or `python3 --version`).
- Install the Python dependencies:

  ```bash
  pip install -r requirements.txt
  ```

- A Chromium browser (**Microsoft Edge** or **Google Chrome**). They share the
  OS trust store on Windows/macOS and the NSS store on Linux.

Platform-specific extra:

| OS | Extra requirement |
|----|-------------------|
| **Windows** | Nothing to install. You must run `setup.py` / `server.py` from an **Administrator** terminal (editing the hosts file and binding port 443 need it). |
| **macOS** | Nothing to install. Run `setup.py` / `server.py` with `sudo`. |
| **Linux** | Install NSS tools so Edge/Chrome cert trust works: `sudo apt install libnss3-tools` (Debian/Ubuntu) · `sudo dnf install nss-tools` (Fedora) · `sudo pacman -S nss` (Arch). Run `setup.py` / `server.py` with `sudo`. |

---

## Quick start

> Run every command from inside the `coursera_clone/` folder.

### Windows (Administrator PowerShell)

```powershell
pip install -r requirements.txt
python build.py                 # build the static site
python setup.py                 # generate+trust cert, add hosts entries  (needs Admin)
python server.py                # serve on :80 and :443                   (needs Admin)
# then fully close & reopen Edge/Chrome, and open:
#   https://www.coursera.org/organizations/viot/my-learning
```

### macOS

```bash
pip3 install -r requirements.txt
python3 build.py
sudo python3 setup.py
sudo python3 server.py
# close & reopen Edge/Chrome, then open the URL above
```

### Linux

```bash
sudo apt install libnss3-tools          # one-time (or dnf/pacman equivalent)
pip3 install -r requirements.txt
python3 build.py
sudo python3 setup.py
sudo python3 server.py
# pkill -x msedge  (or pkill chrome), reopen it, then open the URL above
```

Open **https://www.coursera.org/organizations/viot/my-learning** — valid padlock,
real-looking page, clickable tabs.

When you're done: **`python teardown.py`** (Windows: Admin; macOS/Linux: `sudo`) —
restores DNS and removes the trusted cert. Restart the browser afterwards.

---

## Certificate trust — per OS (the important bit)

Browsers don't all use the same trust store, which is why `setup.py` branches:

| OS | Where the cert goes | Command used | Who uses it |
|----|--------------------|--------------|-------------|
| **Windows** | `CurrentUser\Root` store | `certutil -addstore -user Root cert.pem` | Edge & Chrome read the **Windows** cert store |
| **macOS** | login keychain, `trustRoot` | `security add-trusted-cert -r trustRoot -k login.keychain-db cert.pem` | Edge & Chrome read the **system/login keychain** |
| **Linux** | `~/.pki/nssdb` | `certutil -d sql:~/.pki/nssdb -A -t "C,," ...` | Edge & Chrome read the **NSS** db (needs `libnss3-tools`) |

`setup.py` detects the OS and does the right one automatically — you don't pick.
`gen_cert.py` builds the cert with Python's `cryptography` library, so **no
OpenSSL binary is required** on any platform.

> **Why a self-signed cert is OK here:** it's trusted only in *your* browser, only
> for `coursera.org` pointed at *your* `127.0.0.1`. `teardown.py` removes it.

---

## Feature flags

Rebuild with a different name and/or set of completed specializations:

```bash
python build.py --name Vivake --course devops --course fintech
python build.py --name Priya  --course finance --course anatomy
python build.py --name vWake                       # name only, default courses
```

(Linux/macOS shortcut: `./rebuild.sh --name ... --course ...`.)

- **`--name NAME`** — sets the name in the greeting ("Good morning, NAME"), both
  avatar circles (→ first initial), the profile dropdown ("Hi, NAME"), and the
  aria-labels. Applied to **all four tabs**.
- **`--course KEYWORD`** (repeatable) — which specialization(s) to show; every
  course in them is marked **Complete**, and it updates In Progress, Completed
  (with the "Congratulations … Professional Certificate" banner), Certificates &
  Badges, and the Recent Certificates sidebar.

**Available courses** (only what's in the capture):

| keyword | specialization |
|---------|----------------|
| `devops` | IBM DevOps and Software Engineering |
| `fintech` | FinTech: Finance Industry Transformation and Regulation |
| `financial-services` (`finance`) | Digital Transformation in Financial Services |
| `defi` | Decentralized Finance (DeFi): The Future of Finance |
| `content-creation` (`tiktok`) | Content Creation for TikTok, YouTube, Instagram, Facebook |
| `anatomy` | Anatomy |
| `entrepreneurship` (`innovation`) | Innovation and entrepreneurship — *synthesized* from the reference screenshots (not in the original capture), rendered with the same markup so it's pixel-identical |

Example — DevOps + Entrepreneurship, named "vwake":

```bash
python build.py --name vwake --course devops --course entrepreneurship
```

After rebuilding, just **hard-refresh** the page (`Ctrl+Shift+R`) — the running
server reads files live.

---

## (Optional) Re-capture fresh data

The repo ships with snapshots in `capture/tabs/*.mhtml`. To capture a *different*
logged-in account:

1. In the browser, open DevTools (**F12**) → **Application** → **Cookies** →
   `https://www.coursera.org` → copy the **`CAUTH`** value.
2. Put it in a file named `.cookie` next to the scripts (just the value).
3. `python capture_tabs.py` — drives a headless Chrome with that cookie and writes
   fresh `capture/tabs/*.mhtml`.
4. `python build.py` to regenerate the site, then **delete `.cookie`** (it's a live
   session token; it's git-ignored for safety).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Port 443 already in use** | Something else holds it (e.g. another server, or on Linux a Tailscale bind). Stop it, or edit `server.py` to bind only `127.0.0.1`. |
| **Cert warning / "Not secure"** | The cert isn't trusted yet, or the browser was open during `setup.py`. Close the browser **completely**, re-run `setup.py`, reopen. |
| **Page still loads the real Coursera** | hosts edit didn't take or DNS is cached. Re-run `setup.py` (elevated), flush DNS: Windows `ipconfig /flushdns`, macOS `sudo dscacheutil -flushcache`, Linux usually none. Fully restart the browser. |
| **Linux: `certutil: command not found`** | Install `libnss3-tools` (see Prerequisites), then re-run `setup.py`. |
| **Windows: "Access is denied" editing hosts** | You're not elevated. Run the terminal **as Administrator**. |
| **Tabs don't switch / buttons dead** | Expected for some controls — it's a frozen snapshot. Tabs, profile menu, Add-to-LinkedIn and View-certificate are wired; search, Resume and the calendar arrows are inert. |
| **Changed files but page looks old** | Hard-refresh `Ctrl+Shift+R` (busts the browser's cached HTML). |

---

## Limitations

- **Frozen snapshot**, not a live app. Tab navigation, the profile dropdown,
  Add-to-LinkedIn and View-certificate work; search box, Resume buttons, "⋯"
  menus and calendar arrows are inert (that logic lived in Coursera's stripped JS).
- **Certificate *images*** (`capture/_res/*.bin`) have the original name and course
  baked into the pixels. `--name` / `--course` update every title, label and avatar,
  but the small cert *picture* still shows the captured text.
- Shows the **six captured specializations** plus **Innovation and
  entrepreneurship**, which is *synthesized* from the reference screenshots
  (cloned from a real 4-course block and relabeled, so it renders identically).
  Any other specialization would need a fresh capture from an account that has it.
- The cert is **self-signed** and trusted only on this machine for this purpose.
  Always run `teardown.py` when finished to restore normal `coursera.org` access.

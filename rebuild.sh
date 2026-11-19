#!/usr/bin/env bash
# rebuild.sh — regenerate the static clone from the captured MHTML snapshots.
# Pipeline: unpack tabs -> localize external assets -> apply demo edits.
#
# Feature flags (forwarded to customize.py):
#   ./rebuild.sh --name vwake  --course devops --course entrepreneurship
#   ./rebuild.sh --name Vivake --course devops --course fintech
#   ./rebuild.sh --name Priya  --course defi --course anatomy
# Courses: devops | fintech | financial-services | defi | content-creation | anatomy | entrepreneurship
# (Re-capturing from the live site needs a fresh CAUTH; see grab.py / capture_tabs.py.)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
rm -rf site
python3 build_site.py          # mhtml -> site/tabs/*.html + shared /_res pool
python3 localize_assets.py     # pull external imgs local, wire cert previews
python3 build_certs.py         # render real certificate PDFs -> jpg/thumb/pdf + manifest
python3 customize.py "$@"      # apply --name / --course flags, complete the specs
echo
echo "[done] clone rebuilt. If server.py is already running, just hard-refresh"
echo "       the page (Ctrl+Shift+R). Otherwise: sudo python3 server.py"

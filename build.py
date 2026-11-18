#!/usr/bin/env python3
"""
build.py — regenerate the static clone from the captured snapshots, OS-independently.

  python build.py                                  # default: name 'atharva', devops+fintech
  python build.py --name Vivake --course devops --course fintech
  python build.py --name Priya  --course finance --course anatomy

Pipeline:  build_site.py -> localize_assets.py -> customize.py (flags passed through).
Equivalent to rebuild.sh, but works on Windows/macOS/Linux with plain Python.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, extra=()):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *extra])
    if r.returncode != 0:
        sys.exit(f'[X] {script} failed')


def main():
    run('build_site.py')
    run('localize_assets.py')
    run('customize.py', sys.argv[1:])   # forward --name / --course
    print('\n[done] clone rebuilt in ./site')
    print('       If the server is already running, hard-refresh (Ctrl+Shift+R).')
    print('       Otherwise:  python server.py   (elevated: Admin on Windows, sudo on *nix)')


if __name__ == '__main__':
    main()

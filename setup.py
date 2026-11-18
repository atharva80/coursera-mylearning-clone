#!/usr/bin/env python3
"""
setup.py — point coursera.org at this local clone and trust its TLS cert,
on Windows, macOS or Linux.

  Windows : run from an **Administrator** PowerShell/cmd:   python setup.py
  macOS   :   sudo python3 setup.py
  Linux   :   sudo python3 setup.py     (needs libnss3-tools for certutil)

What it does, per-OS:
  * cert trust
      Windows -> certutil -addstore -user Root      (Edge/Chrome use the Windows store)
      macOS   -> security add-trusted-cert (login keychain, trustRoot)
      Linux   -> certutil into the NSS db ~/.pki/nssdb (Edge/Chrome use NSS)
  * DNS override: adds 127.0.0.1 coursera.org / www.coursera.org to the hosts file
      Windows -> C:\\Windows\\System32\\drivers\\etc\\hosts
      *nix    -> /etc/hosts

Undo everything with:  python teardown.py
"""
import ctypes
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(HERE, 'cert.pem')
KEY = os.path.join(HERE, 'key.pem')
DOMAINS = ['coursera.org', 'www.coursera.org']
MARK = '# coursera-clone'
CERT_NAME = 'coursera-clone'
OSN = platform.system()  # 'Windows' | 'Darwin' | 'Linux'


# ---------------------------------------------------------------- elevation
def is_admin():
    if OSN == 'Windows':
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


def require_admin():
    if not is_admin():
        if OSN == 'Windows':
            sys.exit("[X] Run this from an **Administrator** terminal "
                     "(right-click > Run as administrator), then: python setup.py")
        sys.exit("[X] Needs root for the hosts file. Run:  sudo python3 setup.py")


def sudo_user_home():
    """When invoked via sudo on *nix, the real user's home (for NSS/keychain)."""
    su = os.environ.get('SUDO_USER')
    if su and OSN != 'Windows':
        import pwd
        return su, pwd.getpwnam(su).pw_dir
    return None, os.path.expanduser('~')


def run_as_user(cmd, home):
    """Run a command as the invoking (non-root) user when under sudo."""
    su = os.environ.get('SUDO_USER')
    if su and OSN != 'Windows' and os.geteuid() == 0:
        cmd = ['sudo', '-u', su, 'env', f'HOME={home}'] + cmd
    return subprocess.run(cmd)


# ---------------------------------------------------------------- hosts
def hosts_path():
    if OSN == 'Windows':
        return os.path.join(os.environ.get('SystemRoot', r'C:\Windows'),
                            'System32', 'drivers', 'etc', 'hosts')
    return '/etc/hosts'


def edit_hosts():
    p = hosts_path()
    with open(p, 'r', encoding='utf-8', errors='replace') as f:
        lines = [l for l in f.read().splitlines() if MARK not in l]
    for d in DOMAINS:
        lines.append(f'127.0.0.1 {d} {MARK}')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'[+] hosts updated: {", ".join(DOMAINS)} -> 127.0.0.1   ({p})')


# ---------------------------------------------------------------- trust
def trust_windows():
    subprocess.run(['certutil', '-addstore', '-f', '-user', 'Root', CERT], check=True)
    print('[+] cert trusted in Windows CurrentUser\\Root store')


def trust_macos():
    _su, home = sudo_user_home()
    kc = os.path.join(home, 'Library', 'Keychains', 'login.keychain-db')
    if not os.path.exists(kc):
        kc = os.path.join(home, 'Library', 'Keychains', 'login.keychain')
    run_as_user(['security', 'add-trusted-cert', '-r', 'trustRoot', '-k', kc, CERT], home)
    print(f'[+] cert trusted in macOS login keychain ({kc})')


def trust_linux():
    if not shutil.which('certutil'):
        print('[!] certutil not found. Install NSS tools, then re-run:')
        print('      Debian/Ubuntu:  sudo apt install libnss3-tools')
        print('      Fedora:         sudo dnf install nss-tools')
        print('      Arch:           sudo pacman -S nss')
        return
    _su, home = sudo_user_home()
    nssdir = os.path.join(home, '.pki', 'nssdb')
    os.makedirs(nssdir, exist_ok=True)
    nss = f'sql:{nssdir}'
    run_as_user(['certutil', '-d', nss, '-D', '-n', CERT_NAME], home)  # drop old (ignore err)
    r = run_as_user(['certutil', '-d', nss, '-A', '-t', 'C,,', '-n', CERT_NAME, '-i', CERT], home)
    if r.returncode == 0:
        print(f'[+] cert trusted in NSS db ({nssdir}) for Edge/Chrome')
    else:
        print('[!] NSS trust failed — is the browser closed? Try again with Edge/Chrome shut.')


def ensure_cert():
    if os.path.exists(CERT) and os.path.exists(KEY):
        return
    print('[*] generating self-signed cert ...')
    subprocess.run([sys.executable, os.path.join(HERE, 'gen_cert.py')], check=True)


def main():
    require_admin()
    ensure_cert()
    if OSN == 'Windows':
        trust_windows()
    elif OSN == 'Darwin':
        trust_macos()
    else:
        trust_linux()
    edit_hosts()
    print('\nNext:')
    if OSN == 'Windows':
        print('  1) (same Admin terminal)  python server.py')
        print('  2) fully close & reopen Edge/Chrome')
    else:
        print('  1) sudo python3 server.py')
        print('  2) fully close & reopen Edge/Chrome '
              '(Linux: pkill -x msedge / pkill chrome)')
    print('  3) open  https://www.coursera.org/organizations/viot/my-learning')
    print('Undo:  python teardown.py   (Windows: as Admin; *nix: sudo)')


if __name__ == '__main__':
    main()

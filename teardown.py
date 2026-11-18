#!/usr/bin/env python3
"""
teardown.py — undo setup.py: restore DNS and remove the trusted cert.

  Windows : (Administrator)   python teardown.py
  macOS   : sudo python3 teardown.py
  Linux   : sudo python3 teardown.py
"""
import ctypes
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOMAINS = ['coursera.org', 'www.coursera.org']
MARK = '# coursera-clone'
CERT_NAME = 'coursera-clone'
CN = 'coursera.org'
OSN = platform.system()


def is_admin():
    if OSN == 'Windows':
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


def sudo_user_home():
    su = os.environ.get('SUDO_USER')
    if su and OSN != 'Windows':
        import pwd
        return su, pwd.getpwnam(su).pw_dir
    return None, os.path.expanduser('~')


def run_as_user(cmd, home):
    su = os.environ.get('SUDO_USER')
    if su and OSN != 'Windows' and os.geteuid() == 0:
        cmd = ['sudo', '-u', su, 'env', f'HOME={home}'] + cmd
    return subprocess.run(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


def hosts_path():
    if OSN == 'Windows':
        return os.path.join(os.environ.get('SystemRoot', r'C:\Windows'),
                            'System32', 'drivers', 'etc', 'hosts')
    return '/etc/hosts'


def main():
    if not is_admin():
        sys.exit("[X] Run elevated: Windows=Administrator terminal, *nix=sudo python3 teardown.py")

    # hosts
    p = hosts_path()
    try:
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            lines = [l for l in f.read().splitlines() if MARK not in l]
        with open(p, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f'[+] hosts restored ({p})')
    except Exception as e:
        print(f'[!] hosts restore failed: {e}')

    # cert untrust
    if OSN == 'Windows':
        subprocess.run(['certutil', '-delstore', '-user', 'Root', CN],
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        print('[+] cert removed from Windows CurrentUser\\Root')
    elif OSN == 'Darwin':
        _su, home = sudo_user_home()
        run_as_user(['security', 'delete-certificate', '-c', CN], home)
        print('[+] cert removed from macOS keychain')
    else:
        if shutil.which('certutil'):
            _su, home = sudo_user_home()
            nss = f'sql:{os.path.join(home, ".pki", "nssdb")}'
            run_as_user(['certutil', '-d', nss, '-D', '-n', CERT_NAME], home)
            print('[+] cert removed from NSS db')

    print('\n[done] coursera.org resolves normally again. Restart the browser.')


if __name__ == '__main__':
    main()

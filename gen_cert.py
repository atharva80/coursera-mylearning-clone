#!/usr/bin/env python3
"""
gen_cert.py — create a self-signed TLS cert for coursera.org, OS-independently.

Uses the `cryptography` library (no openssl binary required), so it works the
same on Windows, macOS and Linux. Writes cert.pem + key.pem next to this file.
Idempotent: pass --force to regenerate.
"""
import argparse
import datetime
import ipaddress
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(HERE, 'cert.pem')
KEY = os.path.join(HERE, 'key.pem')
DOMAINS = ['coursera.org', 'www.coursera.org']


def generate():
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, DOMAINS[0])])
    san = x509.SubjectAlternativeName(
        [x509.DNSName(d) for d in DOMAINS] + [x509.IPAddress(ipaddress.IPv4Address('127.0.0.1'))])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=825))
            .add_extension(san, critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))

    with open(KEY, 'wb') as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
    with open(CERT, 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='regenerate even if it exists')
    a = ap.parse_args()
    if os.path.exists(CERT) and os.path.exists(KEY) and not a.force:
        print(f'[=] cert already exists: {CERT} (use --force to regenerate)')
        return
    try:
        generate()
    except ImportError:
        sys.exit("need the 'cryptography' package:  pip install -r requirements.txt")
    print(f'[+] wrote {CERT}')
    print(f'[+] wrote {KEY}')
    print('    CN=coursera.org  SAN=coursera.org,www.coursera.org,127.0.0.1')


if __name__ == '__main__':
    main()

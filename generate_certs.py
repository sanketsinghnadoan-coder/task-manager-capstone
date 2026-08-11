"""
Generate a free self-signed TLS certificate for local HTTPS development.

Uses only the Python standard library (ssl + cryptography is NOT required).
Produces:
  certs/localhost.pem  — certificate + private key (PEM, combined)
  certs/cert.pem       — certificate only
  certs/key.pem        — private key only

These are for LOCAL DEVELOPMENT only — browsers will show a warning that you
can safely accept for 127.0.0.1 / localhost.
"""

from __future__ import annotations

import datetime
import ipaddress
import os
import sys

CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs")
CERT_FILE = os.path.join(CERT_DIR, "cert.pem")
KEY_FILE = os.path.join(CERT_DIR, "key.pem")
COMBINED_FILE = os.path.join(CERT_DIR, "localhost.pem")


def generate_self_signed_cert(
    common_name: str = "localhost",
    days_valid: int = 365,
) -> tuple[str, str]:
    """
    Create a self-signed certificate using the cryptography package if available,
    otherwise fall back to a minimal openssl-compatible approach via ssl module helpers.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        return _generate_with_openssl_fallback(common_name, days_valid)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TaskFlow Pro Dev"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    alt_names = [
        x509.DNSName("localhost"),
        x509.DNSName("127.0.0.1"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv6Address("::1")),
    ]

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=days_valid))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return cert_pem, key_pem


def _generate_with_openssl_fallback(common_name: str, days_valid: int) -> tuple[str, str]:
    """Fallback: shell out to openssl if cryptography is not installed."""
    import subprocess
    import tempfile

    os.makedirs(CERT_DIR, exist_ok=True)
    conf = f"""
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = {common_name}
O = TaskFlow Pro Dev
C = US

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = ::1
"""
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as conf_file:
        conf_file.write(conf)
        conf_path = conf_file.name

    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                KEY_FILE,
                "-out",
                CERT_FILE,
                "-days",
                str(days_valid),
                "-config",
                conf_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with open(CERT_FILE, "r", encoding="utf-8") as f:
            cert_pem = f.read()
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            key_pem = f.read()
        return cert_pem, key_pem
    except FileNotFoundError:
        print(
            "ERROR: Neither the 'cryptography' package nor the 'openssl' CLI is available.\n"
            "Install cryptography (free/open-source):\n"
            "  pip install cryptography\n"
            "Then re-run: python generate_certs.py",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"openssl failed: {exc.stderr}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            os.unlink(conf_path)
        except OSError:
            pass


def main() -> None:
    os.makedirs(CERT_DIR, exist_ok=True)

    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print(f"Certificates already exist in {CERT_DIR}/")
        print(f"  cert: {CERT_FILE}")
        print(f"  key:  {KEY_FILE}")
        print("Delete them and re-run this script to regenerate.")
        return

    print("Generating self-signed TLS certificate for localhost...")
    cert_pem, key_pem = generate_self_signed_cert()

    with open(CERT_FILE, "w", encoding="utf-8") as f:
        f.write(cert_pem)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key_pem)
    with open(COMBINED_FILE, "w", encoding="utf-8") as f:
        f.write(cert_pem)
        f.write(key_pem)

    # Restrict key permissions on Unix; no-op-ish on Windows
    try:
        os.chmod(KEY_FILE, 0o600)
        os.chmod(COMBINED_FILE, 0o600)
    except OSError:
        pass

    print("Done. Files written:")
    print(f"  {CERT_FILE}")
    print(f"  {KEY_FILE}")
    print(f"  {COMBINED_FILE}")
    print()
    print("Start HTTPS server with:")
    print("  python run_https.py")
    print("  # or")
    print(
        "  python -m uvicorn main:app --host 127.0.0.1 --port 8443 "
        f'--ssl-keyfile "{KEY_FILE}" --ssl-certfile "{CERT_FILE}"'
    )


if __name__ == "__main__":
    main()

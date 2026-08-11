"""
Launch TaskFlow Pro over HTTPS with a free self-signed local certificate.

Usage:
  python generate_certs.py   # once
  python run_https.py

Then open: https://127.0.0.1:8443/
(Accept the browser warning for the self-signed cert.)
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(ROOT, "certs")
CERT_FILE = os.path.join(CERT_DIR, "cert.pem")
KEY_FILE = os.path.join(CERT_DIR, "key.pem")
HOST = "127.0.0.1"
PORT = 8443


def ensure_certs() -> None:
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    print("TLS certificates not found — generating self-signed certs...")
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "generate_certs.py")],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
        print("Certificate generation failed.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ensure_certs()
    print(f"Starting TaskFlow Pro over HTTPS at https://{HOST}:{PORT}/")
    print("(Self-signed cert — accept the browser security warning for local dev.)")
    print()

    # Prefer uvicorn programmatically so reload works on Windows
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required. Install with: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
        ssl_keyfile=KEY_FILE,
        ssl_certfile=CERT_FILE,
        log_level="info",
    )


if __name__ == "__main__":
    main()

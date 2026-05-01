"""
Deploy the NYC Listings web app to the asmit.space portfolio.

What this script does, in order:
  1. Re-runs build_data.py + build_transit.py so the published bundle is fresh.
  2. Reads the password from .env.local (gitignored on the brain side).
     The plaintext password never travels to the portfolio repo.
  3. Encrypts web/data/listings.json with AES-GCM. Key derived from the
     password via PBKDF2-HMAC-SHA256 (250k iterations, fresh 16-byte salt
     and 12-byte IV per build).
  4. Copies the entire web/ folder to <portfolio>/nyclistings/ — except for
     the plaintext listings.json, which is replaced with listings.enc.json.

Run from the brain folder root:

    python scripts/deploy_portfolio.py

Set NYC_LISTINGS_PASSWORD in .env.local (one line:  NYC_LISTINGS_PASSWORD=...)
or pass it inline:

    NYC_LISTINGS_PASSWORD=shiroshiro python scripts/deploy_portfolio.py
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
PORTFOLIO_ROOT = Path(r"C:\Users\asmit\OneDrive\Documents\GitHub\asmit-space")
PORTFOLIO_TARGET = PORTFOLIO_ROOT / "nyclistings"
ENV_FILE = ROOT / ".env.local"

PBKDF2_ITERATIONS = 250_000  # must match gate.js default


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def read_password() -> str:
    pwd = os.environ.get("NYC_LISTINGS_PASSWORD")
    if pwd:
        return pwd
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "NYC_LISTINGS_PASSWORD":
                return v.strip().strip('"').strip("'")
    print(
        "ERROR: password not found.\n"
        f"  Add it to {ENV_FILE} as:  NYC_LISTINGS_PASSWORD=shiroshiro\n"
        "  (or export NYC_LISTINGS_PASSWORD=...)\n"
        f"  And ensure {ENV_FILE.name} is in .gitignore.",
        file=sys.stderr,
    )
    sys.exit(2)


def encrypt_listings(password: str) -> dict:
    plaintext = (WEB_DIR / "data" / "listings.json").read_bytes()
    salt = os.urandom(16)
    iv = os.urandom(12)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plaintext, None)  # ciphertext || 16-byte tag

    return {
        "v": 1,
        "kdf": {
            "name": "PBKDF2",
            "iterations": PBKDF2_ITERATIONS,
            "hash": "SHA-256",
            "salt": b64(salt),
        },
        "iv": b64(iv),
        "ct": b64(ct),
        "_note": "Decrypt with the password using PBKDF2-derived AES-GCM. See gate.js.",
    }


def rebuild_bundles():
    py = sys.executable
    print("[1/4] rebuilding listings.json from markdown ...")
    subprocess.run([py, "scripts/build_data.py"], cwd=ROOT, check=True)
    print("[2/4] (skipping transit rebuild — run scripts/build_transit.py manually if MTA data is stale)")


SKIP_NAMES = {
    "listings.json",        # plaintext data — must never be published
    "__pycache__",
    ".DS_Store",
    "Thumbs.db",
    "README.md",            # README stays brain-side only
}


def _ignore(_dir: str, names: list[str]) -> list[str]:
    """Custom ignore: drop the names above, plus raw transit downloads
    (subway-lines.geojson etc.) while keeping the slimmed *.min.geojson
    files used at runtime."""
    out: list[str] = []
    for name in names:
        if name in SKIP_NAMES:
            out.append(name); continue
        # Drop raw MTA geojson; keep *.min.geojson.
        if name.endswith(".geojson") and not name.endswith(".min.geojson"):
            out.append(name); continue
    return out


def copy_web_to_portfolio():
    if not PORTFOLIO_ROOT.exists():
        print(f"ERROR: portfolio path not found: {PORTFOLIO_ROOT}", file=sys.stderr)
        sys.exit(2)

    print(f"[3/4] copying web/ -> {PORTFOLIO_TARGET}")
    if PORTFOLIO_TARGET.exists():
        shutil.rmtree(PORTFOLIO_TARGET)
    shutil.copytree(WEB_DIR, PORTFOLIO_TARGET, ignore=_ignore)

    # Defensive: if anything slipped through, scrub it.
    leaked = PORTFOLIO_TARGET / "data" / "listings.json"
    if leaked.exists():
        leaked.unlink()


def write_encrypted(blob: dict):
    out = PORTFOLIO_TARGET / "data" / "listings.enc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, separators=(",", ":")), encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"[4/4] wrote {out.relative_to(PORTFOLIO_ROOT)}  ({size_kb:,.1f} KB)")


def round_trip_check(blob: dict, password: str):
    """Sanity-check: decrypt the just-written blob and confirm it parses."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as KDF
    salt = base64.b64decode(blob["kdf"]["salt"])
    iv = base64.b64decode(blob["iv"])
    ct = base64.b64decode(blob["ct"])
    kdf = KDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=blob["kdf"]["iterations"],
    )
    key = kdf.derive(password.encode("utf-8"))
    plaintext = AESGCM(key).decrypt(iv, ct, None)
    parsed = json.loads(plaintext)
    if "listings" not in parsed:
        raise RuntimeError("decrypted blob missing 'listings' key")
    print(f"        round-trip OK ({len(parsed['listings'])} listings)")


def main():
    password = read_password()
    rebuild_bundles()
    copy_web_to_portfolio()
    blob = encrypt_listings(password)
    write_encrypted(blob)
    round_trip_check(blob, password)
    print()
    print("Done. Commit and push the portfolio repo to publish.")
    print(f"  cd {PORTFOLIO_ROOT}")
    print('  git add nyclistings && git commit -m "deploy: nyclistings update"')
    print("  git push")


if __name__ == "__main__":
    main()

"""Re-download official ISED source material into references/ (git-ignored).

Source binaries are NOT committed (constitution §2/§3 — don't redistribute);
this script makes re-fetching reproducible. English-only (QUESTIONS #12).

Usage:
    python -m app.db.fetch_sources

Notes:
- The Basic bank lives at the lowercase `.pdf` data-file URL (PHASE0 correction).
- The dated `documents/...` URLs from PHASE0 currently 404; the ZIP / RIC docs
  below are best-effort and may need their URLs refreshed. Failures are reported,
  not fatal — the bank PDF is the only Phase-1 hard requirement.
"""
from __future__ import annotations

import ssl
import urllib.request

from app import config

# label -> (url, filename). Bank PDF is required; the rest are best-effort.
SOURCES = {
    "Basic question bank (REQUIRED)": (
        "https://apc-cap.ic.gc.ca/datafiles/amateur_basic_questions_en.pdf",
        "amateur_basic_questions_en.pdf",
    ),
    # Best-effort — verify/refresh URLs if they fail (see LOG / BACKLOG).
    # "Reference Material ZIP (formula/diagram sheets)": (..., "..."),
    # "RIC-3" / "RBR-4" / "RIC-1": (..., "..."),
}


def _download(url: str, dest) -> int:
    # Some Windows TLS stacks fail CRL revocation checks against gc.ca hosts;
    # disable revocation checking (data integrity is still TLS-protected).
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    req = urllib.request.Request(url, headers={"User-Agent": "HamStudy-ingest/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main() -> None:
    config.REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    for label, (url, fname) in SOURCES.items():
        dest = config.REFERENCES_DIR / fname
        try:
            n = _download(url, dest)
            head = dest.read_bytes()[:4]
            ok = head == b"%PDF" if fname.endswith(".pdf") else True
            print(f"[{'ok' if ok else 'WARN'}] {label}: {n} bytes -> {dest}"
                  + ("" if ok else "  (not a PDF — check URL)"))
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"[FAIL] {label}: {e}\n       url: {url}")


if __name__ == "__main__":
    main()

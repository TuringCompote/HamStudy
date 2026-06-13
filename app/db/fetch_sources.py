"""Re-download official ISED source material into references/ (git-ignored).

Source material is NOT committed (constitution §2/§3 — don't redistribute);
this script makes re-fetching reproducible. English-only (QUESTIONS #12).

Usage:
    python -m app.db.fetch_sources

All URLs verified live 2026-06-13. The bank PDF is the only Phase-1 hard
requirement; the rest feed Phase 4 (formula trainer) and Phase 5 (AI reference
layer). Failures are reported, not fatal.
"""
from __future__ import annotations

import ssl
import urllib.request
import zipfile

from app import config

_ISED = "https://ised-isde.canada.ca/site"
_ARO = f"{_ISED}/amateur-radio-operator-certificate-services"
_SMT = f"{_ISED}/spectrum-management-telecommunications/en/licences-and-certificates"

# label -> (url, filename, kind). kind: "pdf" | "zip" | "html".
SOURCES = {
    # REQUIRED — the question bank (machine-friendly data file; lowercase .pdf).
    # NB: this apc-cap copy is an ISED re-issue dated 2025-08-26 on its title page;
    # ingest derives bank_version from the PDF, so the date self-corrects.
    "Basic question bank (REQUIRED)": (
        "https://apc-cap.ic.gc.ca/datafiles/amateur_basic_questions_en.pdf",
        "amateur_basic_questions_en.pdf", "pdf",
    ),
    # Formula/block-diagram sheets: labelled (study) + unlabelled (exam-legal).
    # Real path is sites/default/files/documents/ (note the trailing space in name).
    "Reference Material ZIP (formula sheets)": (
        f"{_ARO}/sites/default/files/documents/"
        "Reference%20Material%20for%20Amateur%20Radio%20Basic%20EN%202025%20.zip",
        "Reference_Material_Basic_EN_2025.zip", "zip",
    ),
    # Regulatory references for the AI explanation layer (Phase 5).
    "RBR-4 (Standards for Operation)": (
        f"{_ISED}/spectrum-management-telecommunications/sites/default/files/"
        "attachments/2022/RBR-4-i3-2022-07EN.pdf",
        "RBR-4-i3-2022-07EN.pdf", "pdf",
    ),
    # RIC-3 and RIC-1 are HTML-only (no PDF); save the faithful server-rendered
    # page. Clean text extraction happens in Phase 5 when the AI layer uses them.
    "RIC-3 (Information on the Amateur Radio Service)": (
        f"{_SMT}/radiocom-information-circulars-ric/"
        "ric-3-information-amateur-radio-service",
        "RIC-3.html", "html",
    ),
    "RIC-1 (Guide for Examiners)": (
        f"{_SMT}/radiocom-information-circulars-ric/"
        "ric-1-guide-examiners-accredited-conduct-examinations-amateur-radio-operator-certificates",
        "RIC-1.html", "html",
    ),
}


def _ctx() -> ssl.SSLContext:
    # Some Windows TLS stacks fail CRL revocation checks against gc.ca hosts;
    # relax strict X509 flags (transport is still TLS-encrypted/authenticated).
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


def _download(url: str, dest) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "HamStudy-ingest/1.0"})
    with urllib.request.urlopen(req, context=_ctx(), timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def _verify(kind: str, dest) -> bool:
    head = dest.read_bytes()[:4]
    if kind == "pdf":
        return head == b"%PDF"
    if kind == "zip":
        return head[:2] == b"PK"
    return dest.stat().st_size > 0      # html


def main() -> None:
    config.REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    for label, (url, fname, kind) in SOURCES.items():
        dest = config.REFERENCES_DIR / fname
        try:
            n = _download(url, dest)
            ok = _verify(kind, dest)
            print(f"[{'ok' if ok else 'WARN'}] {label}: {n} bytes -> {dest.name}"
                  + ("" if ok else f"  (unexpected content for {kind}; check URL)"))
            if kind == "zip" and ok:
                out = config.REFERENCES_DIR / "_extracted"
                with zipfile.ZipFile(dest) as z:
                    z.extractall(out)
                print(f"       extracted {len(z.namelist())} file(s) -> {out.name}/")
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"[FAIL] {label}: {e}\n       url: {url}")


if __name__ == "__main__":
    main()

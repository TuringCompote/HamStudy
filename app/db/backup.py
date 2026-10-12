"""Online SQLite backup to a NAS-backed path (constitution §6 — never lose history).

Uses SQLite's online backup API, which is safe while the app is running (WAL mode)
— no need to stop the container. Writes a timestamped copy and prunes old ones.

Usage (e.g. from cron on the LXC):
    python -m app.db.backup --dest /mnt/nas/elmer-backups --keep 30

Stamp via --dest only; the timestamp is taken at run time (this is a maintenance
script, not part of the deterministic engine).
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from app import quals


def backup(dest_dir: Path, keep: int = 30, qual: quals.Qual = quals.BASIC) -> Path:
    """Snapshot one qualification's store: hamstudy-<stamp>.db (Basic) or
    hamstudy_advanced-<stamp>.db (Advanced)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = qual.db_path.stem
    out = dest_dir / f"{stem}-{stamp}.db"

    src = sqlite3.connect(qual.db_path)
    try:
        dst = sqlite3.connect(out)
        try:
            src.backup(dst)          # consistent online snapshot (WAL-safe)
        finally:
            dst.close()
    finally:
        src.close()

    # prune oldest, keeping the most recent `keep`
    backups = sorted(dest_dir.glob(f"{stem}-*.db"))
    for old in backups[:-keep] if keep > 0 else []:
        old.unlink()
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Online SQLite backup for Elmer.")
    ap.add_argument("--dest", required=True, type=Path, help="backup directory (NAS path)")
    ap.add_argument("--keep", type=int, default=30, help="how many backups to retain")
    args = ap.parse_args()
    # every qualification store that exists (Basic always; Advanced once built)
    for q in quals.QUALS.values():
        if not q.db_path.exists():
            print(f"skip {q.label}: {q.db_path} not present")
            continue
        path = backup(args.dest, args.keep, q)
        print(f"backed up {q.db_path} -> {path}")

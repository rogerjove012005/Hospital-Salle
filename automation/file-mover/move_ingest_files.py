#!/usr/bin/env python3
"""
Organiza ficheros CSV del worker de ingesta (inbox → processed | failed).

Uso típico (mismas rutas que docker-compose csv-ingest-worker):
  python automation/file-mover/move_ingest_files.py --inbox ./infra/docker/csv-ingest-mounts/inbox \\
    --processed ./infra/docker/csv-ingest-mounts/processed --failed ./infra/docker/csv-ingest-mounts/failed
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def move_one(src: Path, dest_dir: Path, *, dry_run: bool) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = dest_dir / f"{stamp}_{src.name}"
    if dry_run:
        print(f"DRY-RUN {src} -> {target}")
        return target
    shutil.move(str(src), str(target))
    print(f"MOVED {src} -> {target}")
    return target


def main() -> int:
    p = argparse.ArgumentParser(description="Mueve CSV de inbox a processed o failed.")
    p.add_argument("--inbox", type=Path, required=True)
    p.add_argument("--processed", type=Path, required=True)
    p.add_argument("--failed", type=Path, required=True)
    p.add_argument("--to", choices=("processed", "failed"), default="processed")
    p.add_argument("--pattern", default="*.csv")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    inbox = args.inbox.resolve()
    dest = (args.processed if args.to == "processed" else args.failed).resolve()
    if not inbox.is_dir():
        print(f"Inbox no existe: {inbox}", file=sys.stderr)
        return 1

    files = sorted(inbox.glob(args.pattern))
    if not files:
        print(f"Sin ficheros {args.pattern} en {inbox}")
        return 0

    for f in files:
        if f.is_file():
            move_one(f, dest, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

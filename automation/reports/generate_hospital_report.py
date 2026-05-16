#!/usr/bin/env python3
"""Genera el informe operativo HTML vía API (automatización de informes)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests


def main() -> int:
    p = argparse.ArgumentParser(description="Descarga informe hospitalario HTML desde la API.")
    p.add_argument("--api", default=os.environ.get("API_BASE_URL", "http://localhost:8000"))
    p.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@admin.com"))
    p.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", "hospital"))
    p.add_argument("-o", "--output", type=Path, default=Path("informe-hospital.html"))
    args = p.parse_args()
    base = args.api.rstrip("/")

    login = requests.post(
        f"{base}/auth/login",
        json={"email": args.email, "password": args.password},
        timeout=30,
    )
    login.raise_for_status()
    token = login.json().get("access_token")
    if not token:
        print("login sin access_token", file=sys.stderr)
        return 1

    res = requests.get(
        f"{base}/reports/hospital",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    res.raise_for_status()
    args.output.write_text(res.text, encoding="utf-8")
    print(f"Informe guardado en {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

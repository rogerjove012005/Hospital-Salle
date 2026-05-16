#!/usr/bin/env python3
"""
Worker de ingesta CSV automatizada: vigilancia de carpeta + tirada HTTP (API simulada).
Emite líneas JSON en stdout para logs de contenedor y mueve ficheros tras éxito o error.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(message)s",
)
_log = logging.getLogger("csv_ingest_worker")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(**fields: Any) -> None:
    payload = {"ts": utc_now_iso(), **fields}
    _log.info(json.dumps(payload, ensure_ascii=False))


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"files": {}, "urls": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"files": {}, "urls": {}}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=0, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def obtain_token(api_base: str, email: str, password: str, timeout: int) -> str:
    r = requests.post(
        f"{api_base.rstrip('/')}/auth/login",
        json={"email": email, "password": password},
        timeout=timeout,
    )
    if not r.ok:
        raise RuntimeError(f"login failed {r.status_code}: {r.text[:400]}")
    data = r.json()
    tok = data.get("access_token")
    if not tok:
        raise RuntimeError("login response missing access_token")
    return str(tok)


def post_pipeline_event(
    api_base: str,
    token: str,
    stage: str,
    status: str,
    message: str,
    timeout: int,
) -> None:
    try:
        requests.post(
            f"{api_base.rstrip('/')}/imports/pipeline-events",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"stage": stage, "status": status, "message": message[:2000]},
            timeout=min(30, timeout),
        )
    except Exception as e:
        log_event(event="pipeline_event_failed", error=str(e))


def post_csv(
    api_base: str,
    token: str,
    filename: str,
    content: bytes,
    timeout: int,
) -> tuple[int, dict[str, Any] | None, str]:
    r = requests.post(
        f"{api_base.rstrip('/')}/imports/csv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, "text/csv")},
        timeout=timeout,
    )
    text = r.text[:2000]
    body: dict[str, Any] | None = None
    try:
        if "application/json" in (r.headers.get("content-type") or ""):
            body = r.json()
    except Exception:
        pass
    return r.status_code, body, text


def safe_move(src: Path, dest_dir: Path, ok: bool) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / src.name
    if target.exists():
        target = dest_dir / f"{src.stem}-{int(time.time())}{src.suffix}"
    shutil.move(str(src), str(target))
    log_event(event="file_moved", success=ok, src=str(src), dest=str(target))


def filename_from_url(url: str) -> str:
    path = urlparse(url).path
    leaf = Path(path).name.strip() if path else ""
    return leaf if leaf.lower().endswith(".csv") else "simulated_feed.csv"


def pull_url_once(url: str, timeout: int) -> tuple[int, bytes, str]:
    r = requests.get(url, timeout=timeout)
    if not r.ok:
        return r.status_code, b"", r.text[:500]
    return r.status_code, r.content, ""


def process_urls(
    urls: list[str],
    state: dict[str, Any],
    api_base: str,
    token: str,
    timeout: int,
) -> None:
    bucket = state.setdefault("urls", {})
    for raw in urls:
        url = raw.strip()
        if not url:
            continue
        try:
            code, content, err = pull_url_once(url, timeout=min(timeout, 120))
            if code >= 400 or not content.strip():
                log_event(event="pull_error", url=url, http_status=code, detail=err)
                continue

            fname = filename_from_url(url)
            digest = hashlib.sha256(content).hexdigest()
            prev = bucket.get(url)
            if isinstance(prev, dict) and prev.get("sha256") == digest:
                log_event(event="skipped_unchanged_url", url=url)
                continue

            hc, body, raw = post_csv(api_base, token, fname, content, timeout=max(timeout, 60))
            if hc >= 400:
                log_event(event="upload_error", source="http_pull", url=url, detail=raw)
                continue

            dup = isinstance(body, dict) and body.get("duplicate_file") is True
            bid = (
                body.get("batch", {}).get("batch_id")
                if isinstance(body, dict) and isinstance(body.get("batch"), dict)
                else None
            )
            log_event(event="upload_ok", source="http_pull", url=url, duplicate=dup, batch_id=bid)

            bucket[url] = {
                "sha256": digest,
                "processed_at": utc_now_iso(),
                "filename": fname,
            }
        except requests.RequestException as e:
            log_event(event="url_cycle_error", url=url, error=str(e))


def process_inbox(
    inbox: Path,
    processed_dir: Path,
    failed_dir: Path,
    state: dict[str, Any],
    api_base: str,
    token: str,
    timeout: int,
) -> None:
    if not inbox.is_dir():
        return
    bucket = state.setdefault("files", {})

    for path in sorted(inbox.glob("*.csv")):
        if not path.is_file():
            continue
        key = f"path:{path.resolve()}"

        try:
            content = path.read_bytes()
            if not content.strip():
                log_event(event="skipped_empty_file", path=str(path))
                safe_move(path, failed_dir, ok=False)
                continue

            digest = hashlib.sha256(content).hexdigest()
            prev = bucket.get(key)
            if isinstance(prev, dict) and prev.get("sha256") == digest:
                log_event(event="dedupe_skip_upload_file", path=str(path))
                safe_move(path, processed_dir, ok=True)
                continue

            code, body, raw = post_csv(api_base, token, path.name, content, timeout=timeout)

            if code >= 400:
                log_event(event="upload_error", source="inbox", path=str(path), http_status=code, detail=raw)
                post_pipeline_event(
                    api_base,
                    token,
                    "csv_ingestion",
                    "error",
                    f"Fallo subida {path.name}: HTTP {code}",
                    timeout,
                )
                safe_move(path, failed_dir, ok=False)
                continue

            dup = isinstance(body, dict) and body.get("duplicate_file") is True
            bid = (
                body.get("batch", {}).get("batch_id")
                if isinstance(body, dict) and isinstance(body.get("batch"), dict)
                else None
            )
            log_event(event="upload_ok", source="inbox", path=str(path), duplicate=dup, batch_id=bid)
            bucket[key] = {"sha256": digest, "processed_at": utc_now_iso(), "name": path.name}
            safe_move(path, processed_dir, ok=True)
        except OSError as e:
            log_event(event="inbox_fs_error", path=str(path), error=str(e))


def cycle() -> int:
    api_base = os.environ.get("API_BASE_URL", "http://api:8000").strip()
    email = os.environ.get("INGEST_LOGIN_EMAIL") or os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("INGEST_LOGIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        log_event(event="fatal", detail="missing INGEST_LOGIN_EMAIL/PASSWORD or ADMIN_EMAIL/PASSWORD")
        return 1

    inbox = Path(os.getenv("CSV_INBOX", "/data/inbox")).resolve()
    processed_dir = Path(os.getenv("CSV_PROCESSED", "/data/processed")).resolve()
    failed_dir = Path(os.getenv("CSV_FAILED", "/data/failed")).resolve()
    state_path = Path(os.getenv("CSV_INGEST_STATE", "/data/state/ingest_state.json")).resolve()
    urls_raw = os.getenv("CSV_PULL_URLS", "").strip()

    timeout = max(15, min(int(os.getenv("INGEST_HTTP_TIMEOUT_SECONDS", "120")), 900))
    poll_interval = max(15, min(int(os.getenv("INGEST_POLL_INTERVAL_SECONDS", "90")), 3600))

    urls = [u for u in urls_raw.split(",") if u.strip()]

    inbox.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    log_event(event="startup", api_base=api_base, inbox=str(inbox), pull_urls=len(urls))

    while True:
        state = load_state(state_path)

        try:
            token = obtain_token(api_base, email, password, timeout=min(30, timeout))
            process_urls(urls, state, api_base, token, timeout)
            process_inbox(inbox, processed_dir, failed_dir, state, api_base, token, timeout)
            save_state(state_path, state)
        except Exception as e:
            log_event(event="cycle_error", error=str(e))
            try:
                token = obtain_token(api_base, email, password, timeout=min(30, timeout))
                post_pipeline_event(
                    api_base,
                    token,
                    "csv_ingest_worker",
                    "error",
                    f"Error en ciclo de ingesta: {e}",
                    timeout,
                )
            except Exception:
                pass

        time.sleep(poll_interval)


def main() -> None:
    try:
        cycle()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

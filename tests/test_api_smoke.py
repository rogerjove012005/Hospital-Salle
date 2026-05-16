"""
Smoke tests de integración contra API en ejecución.

Requiere: API en http://localhost:8000 (docker compose up).
Sin API: los tests se omiten (pytest -m integration).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

API = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "rogerjove012005@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "hospital")

pytestmark_integration = pytest.mark.integration


def _api_available() -> bool:
    try:
        with urllib.request.urlopen(f"{API}/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


skip_no_api = pytest.mark.skipif(not _api_available(), reason="API no disponible en localhost:8000")


def _login(email: str, password: str) -> str:
    payload = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)["access_token"]


@skip_no_api
@pytest.mark.integration
def test_health():
    with urllib.request.urlopen(f"{API}/health", timeout=5) as resp:
        assert resp.status == 200


@skip_no_api
@pytest.mark.integration
def test_health_pipeline():
    with urllib.request.urlopen(f"{API}/health/pipeline", timeout=5) as resp:
        body = json.load(resp)
        assert body.get("status") in ("ok", "unknown", "degraded")


@skip_no_api
@pytest.mark.integration
def test_login_admin_and_dashboard():
    token = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    req = urllib.request.Request(
        f"{API}/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
        assert data["role"] == "admin"


@skip_no_api
@pytest.mark.integration
def test_login_local_domain_email():
    """Cuentas demo con dominio .local (entorno académico)."""
    token = _login("fronttest@hospital.local", "hospital")
    assert len(token) > 20


@skip_no_api
@pytest.mark.integration
def test_radiology_metrics():
    token = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    req = urllib.request.Request(
        f"{API}/radiology/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
        assert "available" in data

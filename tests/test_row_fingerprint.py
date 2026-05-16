"""Tests unitarios ligeros (sin Docker)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_APP = ROOT / "services" / "api"
if str(API_APP) not in sys.path:
    sys.path.insert(0, str(API_APP))

from app.dashboard_imports import _row_fingerprint  # noqa: E402


def test_row_fingerprint_stable():
    row = {"b": "2", "a": "1"}
    fp1 = _row_fingerprint(row)
    fp2 = _row_fingerprint({"a": "1", "b": "2"})
    assert fp1 == fp2
    data = json.loads(fp1)
    assert ("a", "1") in data
    assert ("b", "2") in data


def test_row_fingerprint_empty_values():
    assert _row_fingerprint({"x": ""}) == _row_fingerprint({"x": "  "})

# test/test_watermark_endpoints.py
import pytest
from pathlib import Path
import server

# -----------------------------
# Mock utilities for watermarking
# -----------------------------
def mock_apply_watermark(**kwargs):
    """Simulate successful watermark application (returns JSON as route expects)."""
    return {"documentid": 1, "method": kwargs.get("method"), "size": 7}

def mock_is_applicable(**kwargs):
    """Simulate watermarking method being applicable."""
    return True

def mock_read_watermark(**kwargs):
    """Simulate reading a watermark successfully."""
    return "SECRET123"

# -----------------------------
# Tests for create-watermark endpoint
# -----------------------------
def test_create_watermark_success(client_with_auth, tmp_path, monkeypatch):
    """✅ Successful watermark creation with valid input."""
    file_path = tmp_path / "sample.pdf"
    file_path.write_bytes(b"PDF-1.4\n%EOF")

    monkeypatch.setattr(server.WMUtils, "apply_watermark", mock_apply_watermark)
    monkeypatch.setattr(server.WMUtils, "is_watermarking_applicable", mock_is_applicable)
    monkeypatch.setattr(Path, "exists", lambda self: True)

    payload = {
        "method": "toy-eof",
        "intended_for": "Alice",
        "secret": "topSecret",
        "key": "strongKey",
        "position": "bottom",
    }
    resp = client_with_auth.post("/api/create-watermark/1", json=payload)
    resp_json = resp.get_json()
    assert resp.status_code in [200, 201]
    assert resp_json["documentid"] == 1
    assert resp_json["method"] == "toy-eof"

def test_create_watermark_invalid_doc_id(client_with_auth):
    """❌ 400 if document_id is invalid."""
    payload = {
        "id": "xyz",
        "method": "m",
        "intended_for": "a",
        "secret": "s",
        "key": "k",
    }
    resp = client_with_auth.post("/api/create-watermark", json=payload)
    assert resp.status_code == 400

def test_create_watermark_db_failure(client_with_auth, monkeypatch):
    """❌ Returns 500 if DB fails."""
    monkeypatch.setattr(server, "get_engine", lambda: server.FailingEngine())
    payload = {
        "method": "toy-eof",
        "intended_for": "Alice",
        "secret": "topSecret",
        "key": "strongKey",
        "position": "bottom",
    }
    resp = client_with_auth.post("/api/create-watermark/1", json=payload)
    # Route returns 500 on DB connection failure
    assert resp.status_code in [500, 503]

# -----------------------------
# Tests for read-watermark endpoint
# -----------------------------
def test_read_watermark_success(client_with_auth, tmp_path, monkeypatch):
    """✅ Successfully read watermark."""
    file_path = tmp_path / "demo.pdf"
    file_path.write_bytes(b"PDF content")

    monkeypatch.setattr(server.WMUtils, "read_watermark", mock_read_watermark)
    monkeypatch.setattr(Path, "exists", lambda self: True)

    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    resp_json = resp.get_json()
    assert resp.status_code in [200, 201]
    assert resp_json["secret"] == "SECRET123"
    assert resp_json["documentid"] == 1

def test_read_watermark_db_failure(client_with_auth, monkeypatch):
    """❌ Returns 500 if DB fails during read-watermark."""
    monkeypatch.setattr(server, "get_engine", lambda: server.FailingEngine())
    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code in [400, 500, 503]

def test_read_watermark_wm_fail(client_with_auth, monkeypatch):
    """❌ Returns 500 if read_watermark throws exception."""
    monkeypatch.setattr(server.WMUtils, "read_watermark", lambda **kw: (_ for _ in ()).throw(Exception("wm fail")))
    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code in [400, 500]


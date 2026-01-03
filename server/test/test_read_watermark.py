# test/test_read_watermark.py
import pytest
from pathlib import Path
import server
from test.test_mocks import MockWatermarkUtils

class DummyDocumentRow:
    id = 1
    name = "demo.pdf"
    path = "demo.pdf"

class DummyVersionRow:
    def __init__(self, path="demo.pdf"):
        self.path = str(path)

class DummyConn:
    def __init__(self, rows=None):
        self._rows = rows or []

    def __enter__(self): return self
    def __exit__(self, *a): pass
    def execute(self, *a, **kw): return self
    def all(self): return self._rows
    def first(self): return self._rows[0] if self._rows else None

class DummyEngine:
    def __init__(self, rows=None):
        self._rows = rows or []
    def connect(self): return DummyConn(self._rows)
    def begin(self): return DummyConn(self._rows)

@pytest.fixture
def patch_engine(monkeypatch):
    monkeypatch.setattr(server, "get_engine", lambda: DummyEngine())

def test_read_watermark_invalid_id(client_with_auth):
    resp = client_with_auth.post("/api/read-watermark", json={"method": "hash-eof", "key": "k"})
    assert resp.status_code == 400

def test_read_watermark_missing_params(client_with_auth):
    resp = client_with_auth.post("/api/read-watermark/1", json={"method": None})
    assert resp.status_code == 400

def test_read_watermark_success(client_with_auth, tmp_path, monkeypatch, patch_engine):
    file_path = tmp_path / "demo.pdf"
    file_path.write_text("PDF content")
    monkeypatch.setattr(server.WMUtils, "read_watermark", lambda **kw: "SECRET123")
    monkeypatch.setattr(Path, "exists", lambda self: True)

    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["secret"] == "SECRET123"


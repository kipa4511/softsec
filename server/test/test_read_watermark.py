import pytest
from pathlib import Path
from conftest import _patch_get_engine_for_endpoint, FailingEngine


def test_read_watermark_invalid_id(client_with_auth):
    """❌ Missing/invalid document_id returns 400."""
    resp = client_with_auth.post("/api/read-watermark", json={"method": "hash-eof", "key": "k"})
    assert resp.status_code == 400
    assert "document_id" in resp.get_data(as_text=True)


def test_read_watermark_missing_params(client_with_auth):
    """❌ Missing method/key returns 400."""
    resp = client_with_auth.post("/api/read-watermark/1", json={"method": None})
    assert resp.status_code == 400
    assert "method and key" in resp.get_data(as_text=True)


def test_read_watermark_db_error(monkeypatch, client_with_auth):
    """❌ Returns 503 when DB fails."""
    app = client_with_auth.application

    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyEngine:
        def connect(self): raise Exception("DB failure")

    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code == 503
    assert "database error" in resp.get_data(as_text=True)


def test_read_watermark_missing_file(monkeypatch, client_with_auth):
    """❌ Returns 410 if file missing."""
    app = client_with_auth.application
    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyVersionRow:
        path = "nonexistent.pdf"

    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

        def execute(self, *a, **kw):
            sql = str(a[0]) if a else ""
            if "FROM Documents" in sql and "JOIN" not in sql:
                self._rows = [DummyDocumentRow()]
            elif "FROM Versions" in sql:
                self._rows = [DummyVersionRow()]
            else:
                self._rows = [DummyDocumentRow()]
            return self

        def all(self): return getattr(self, "_rows", [])
        def first(self): return DummyVersionRow()

    class DummyEngine:
        def connect(self): return DummyConn()


    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code == 410
    assert "file missing" in resp.get_data(as_text=True)


def test_read_watermark_invalid_path(monkeypatch, client_with_auth):
    """❌ Returns 500 if file path escapes root."""
    app = client_with_auth.application
    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyVersionRow:
        path = "/etc/passwd"

    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

        def execute(self, *a, **kw):
            sql = str(a[0]) if a else ""
            if "FROM Documents" in sql and "JOIN" not in sql:
                self._rows = [DummyDocumentRow()]
            elif "FROM Versions" in sql:
                self._rows = [DummyVersionRow()]
            else:
                self._rows = [DummyDocumentRow()]
            return self

        def all(self): return getattr(self, "_rows", [])
        def first(self): return DummyVersionRow()
    class DummyEngine:
        def connect(self): return DummyConn()


    monkeypatch.setattr(Path, "exists", lambda self: True)

    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code == 500
    assert "document path invalid" in resp.get_data(as_text=True)


def test_read_watermark_success(monkeypatch, client_with_auth, tmp_path):
    """✅ Returns 201 and watermark details."""
    app = client_with_auth.application
    _patch_get_engine_for_endpoint(app, FailingEngine)
    file_path = tmp_path / "demo.pdf"
    file_path.write_text("PDF content")

    class DummyVersionRow:
        path = str(file_path)

    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

        def execute(self, *a, **kw):
            sql = str(a[0]) if a else ""
            if "FROM Documents" in sql and "JOIN" not in sql:
                self._rows = [DummyDocumentRow()]
            elif "FROM Versions" in sql:
                self._rows = [DummyVersionRow()]
            else:
                self._rows = [DummyDocumentRow()]
            return self

        def all(self): return getattr(self, "_rows", [])
        def first(self): return DummyVersionRow()

    class DummyEngine:
        def connect(self): return DummyConn()

    import server
    monkeypatch.setattr(server.WMUtils, "read_watermark", lambda **kw: "SECRET123")


    resp = client_with_auth.post("/api/read-watermark/1", json={"method": "hash-eof", "key": "key"})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["secret"] == "SECRET123"
    assert data["method"] == "hash-eof"

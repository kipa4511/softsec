import io
import pytest
from pathlib import Path



def test_upload_no_file(client_with_auth):
    """❌ Returns 400 if file is missing."""
    resp = client_with_auth.post("/api/upload-document")
    assert resp.status_code == 400
    assert "file is required" in resp.get_data(as_text=True)


def test_upload_empty_filename(client_with_auth):
    """❌ Returns 400 if empty filename provided."""
    data = {"file": (io.BytesIO(b""), "")}
    resp = client_with_auth.post(
        "/api/upload-document", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    assert "empty filename" in resp.get_data(as_text=True)


def test_upload_database_error(monkeypatch, client_with_auth):
    """❌ Returns 503 if DB insert fails."""
    app = client_with_auth.application
 
    _patch_get_engine_for_endpoint(app, FailingEngine)

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
        def begin(self): return DummyConn()

    data = {"file": (io.BytesIO(b"PDFDATA"), "demo.pdf")}
    resp = client_with_auth.post(
        "/api/upload-document", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code == 503
    assert "database error" in resp.get_data(as_text=True)


def test_upload_success(monkeypatch, client_with_auth, tmp_path):
    """✅ Returns 201 and metadata when upload succeeds."""
    app = client_with_auth.application

    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyRow:
        id, name, creation, sha256_hex, size = 1, "demo.pdf", "2025-01-01T00:00:00", "ABC123", 10

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
        def begin(self): return DummyConn()


    data = {"file": (io.BytesIO(b"%PDF-1.4 content"), "demo.pdf")}
    resp = client_with_auth.post(
        "/api/upload-document", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "id" in data
    assert "sha256" in data

import pytest
from conftest import _patch_get_engine_for_endpoint, FailingEngine


def test_list_documents_success(monkeypatch, client_with_auth):
    """✅ Returns 200 with list of documents."""
    app = client_with_auth.application
    
    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyRow:
        id, name, creation, sha256_hex, size = 1, "demo.pdf", "2025-01-01T00:00:00", "ABC", 123

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

    resp = client_with_auth.get("/api/list-documents")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert "documents" in resp.get_json()


def test_list_documents_db_error(client_with_auth):
    """❌ Returns 503 when DB fails."""
    app = client_with_auth.application

    # Dummy engine that simulates DB connection failure
    class FailingEngine:
        def connect(self): raise Exception("DB failure")

    # ✅ Force every route to use this failing engine
    for name, view in app.view_functions.items():
        g = view.__globals__
        g["get_engine"] = lambda: FailingEngine()

    # Perform GET request
    resp = client_with_auth.get("/api/list-documents")

    # ✅ Expect HTTP 503
    assert resp.status_code == 503, resp.get_data(as_text=True)
    assert "database error" in resp.get_data(as_text=True)

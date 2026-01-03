import pytest


def test_list_versions_invalid_id(client_with_auth):
    """❌ Returns 400 when id missing or invalid."""
    resp = client_with_auth.get("/api/list-versions")
    assert resp.status_code == 400
    assert "document id required" in resp.get_data(as_text=True)


def test_list_versions_success(monkeypatch, client_with_auth):
    """✅ Returns 200 with versions list."""
    app = client_with_auth.application
    
    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyRow:
        id, documentid, link, intended_for, secret, method = 1, 99, "abc", "tester", "s3cr3t", "hash-eof"

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


    resp = client_with_auth.get("/api/list-versions?id=99")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "versions" in data


def test_list_versions_db_error(monkeypatch, client_with_auth):
    """❌ Returns 503 when DB fails."""
    app = client_with_auth.application

    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyEngine:
        def connect(self): raise Exception("DB fail")


    resp = client_with_auth.get("/api/list-versions?id=99")
    assert resp.status_code == 503
    assert "database error" in resp.get_data(as_text=True)


def test_list_all_versions_success(monkeypatch, client_with_auth):
    """✅ Returns 200 and all versions list."""
    app = client_with_auth.application

    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyRow:
        id, documentid, link, intended_for, method = 1, 101, "xyz", "tester", "hash-eof"

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


    resp = client_with_auth.get("/api/list-all-versions")
    assert resp.status_code == 200
    assert "versions" in resp.get_json()


def test_list_all_versions_db_error(monkeypatch, client_with_auth):
    """❌ Returns 503 on DB error."""
    app = client_with_auth.application
    _patch_get_engine_for_endpoint(app, FailingEngine)

    class DummyEngine:
        def connect(self): raise Exception("DB failure")


    resp = client_with_auth.get("/api/list-all-versions")
    assert resp.status_code == 503
    assert "database error" in resp.get_data(as_text=True)

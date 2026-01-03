from pathlib import Path



def test_delete_document_success(monkeypatch, client_with_auth, tmp_path):
    """✅ Successfully deletes a document and removes its file."""
    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path

    # Create a dummy file inside storage (the one to be "deleted")
    file_path = tmp_path / "test.pdf"
    file_path.write_text("PDF content")

    # Dummy DB row simulating document record
    class DummyRow:
        id = 1
        path = str(file_path)

    # Dummy connection that returns the row on SELECT
    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

        def execute(self, *a, **kw):
            sql = str(a[0]) if a else ""
            # SELECT mock
            if "SELECT" in sql:
                self._result = self
            else:
                self._result = None
            return self

        def first(self): return DummyRow()
        def all(self): return [DummyRow()]
        def scalar(self): return 1

    # Dummy engine mimicking SQLAlchemy engine
    class DummyEngine:
        def connect(self): return DummyConn()
        def begin(self): return DummyConn()

    # Force patching of get_engine
    _patch_get_engine_for_endpoint(app, DummyEngine)

    # Monkeypatch path.exists() and unlink() to simulate file removal
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(Path, "unlink", lambda self: None)

    # Perform delete request
    resp = client_with_auth.delete("/api/delete-document/1")

    # ✅ Assertions
    data = resp.get_json()
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert data["deleted"] is True
    assert data["id"] == "1"
    assert data["file_deleted"] is True
    assert data["file_missing"] is False


def test_delete_document_via_post(monkeypatch, client_with_auth, tmp_path):
    """✅ Deletion also works via POST with JSON body."""
    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path

    # Dummy file to simulate document
    file_path = tmp_path / "doc.pdf"
    file_path.write_text("dummy")

    class DummyRow:
        id = 42
        path = str(file_path)

    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **kw): return self
        def first(self): return DummyRow()

    class DummyEngine:
        def connect(self): return DummyConn()
        def begin(self): return DummyConn()

    _patch_get_engine_for_endpoint(app, DummyEngine)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(Path, "unlink", lambda self: None)

    # ✅ POST request with JSON payload
    resp = client_with_auth.post("/api/delete-document", json={"id": "42"})
    data = resp.get_json()

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert data["deleted"] is True
    assert data["id"] == "42"


def test_delete_document_file_missing(monkeypatch, client_with_auth, tmp_path):
    """✅ Handles gracefully when the file doesn't exist (file_missing=True)."""
    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path

    class DummyRow:
        id = 9
        path = str(tmp_path / "missing.pdf")

    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **kw): return self
        def first(self): return DummyRow()

    class DummyEngine:
        def connect(self): return DummyConn()
        def begin(self): return DummyConn()

    _patch_get_engine_for_endpoint(app, DummyEngine)
    monkeypatch.setattr(Path, "exists", lambda self: False)  # simulate missing file

    resp = client_with_auth.delete("/api/delete-document/9")

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["deleted"] is True
    assert data["file_missing"] is True

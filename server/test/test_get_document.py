import importlib
from pathlib import Path


def test_get_document_success(monkeypatch, client_with_auth, tmp_path):
    """✅ Successfully serves a PDF inline when file and DB entry are valid."""

    # Ensure Flask app instance
    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path

    # Create dummy file inside STORAGE_DIR
    pdf_path = tmp_path / "demo.pdf"
    pdf_path.write_text("PDF content")

    # Dummy DB row
    class DummyRow:
        id = 1
        name = "demo.pdf"
        path = str(pdf_path)
        sha256_hex = "ABC123"
        size = 100

    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **kw): return self
        def first(self): return DummyRow()

    class DummyEngine:
        def connect(self): return DummyConn()

    # ✅ Force all routes to use DummyEngine
    for name, view in app.view_functions.items():
        g = view.__globals__
        g["get_engine"] = lambda: DummyEngine()

    monkeypatch.setattr(Path, "exists", lambda self: True)

    # Perform the GET request
    resp = client_with_auth.get("/api/get-document/1")

    # ✅ Assertions
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.mimetype == "application/pdf"
    assert "private" in resp.headers.get("Cache-Control", "")
    assert b"PDF content" in resp.data

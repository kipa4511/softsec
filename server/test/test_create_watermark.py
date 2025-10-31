def test_create_watermark_success_final_fixed(monkeypatch, client_with_auth, tmp_path):
    """
    ✅ Simplified success test for /api/create-watermark/<id>.
    Only checks basic success and presence of link.
    """

    import sys, importlib
    from pathlib import Path

    sys.modules.pop("server", None)
    server = importlib.import_module("server")

    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path.resolve()

    # --- Constants ---
    DOC_ID = 1
    VERSION_ID = 42
    SOURCE_FILENAME = "sample.pdf"
    WATERMARKED_BYTES = b"%PDF-1.4\n% WATERMARKEDDATA\n%%EOF\n"

    # --- Dummy file ---
    src_pdf = tmp_path / SOURCE_FILENAME
    src_pdf.write_bytes(b"%PDF-1.4\n%%EOF")

    # --- Mock rows ---
    class MockDocumentRow:
        id = DOC_ID
        name = SOURCE_FILENAME
        path = str(src_pdf.relative_to(tmp_path))

    # --- Mock DB connection ---
    class MockDbConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

        def execute(self, query, params=None, **kw):
            q = str(query).lower()
            self._mode = None
            if "from documents" in q:
                self._mode = "select_doc"
            elif "insert into versions" in q:
                self._mode = "insert_version"
            elif "last_insert_id" in q:
                self._mode = "lastid"
            return self

        def first(self):
            if getattr(self, "_mode", "") == "select_doc":
                return MockDocumentRow()
            return None

        def scalar(self):
            if getattr(self, "_mode", "") == "lastid":
                return VERSION_ID
            return None

    # --- Mock engine ---
    class MockDbEngine:
        def connect(self): return MockDbConn()
        def begin(self): return MockDbConn()

    # --- Monkeypatch dependencies ---
    for _, view in app.view_functions.items():
        g = view.__globals__
        if "get_engine" in g:
            g["get_engine"] = lambda: MockDbEngine()
        if "WMUtils" in g:
            g["WMUtils"] = server.WMUtils

    monkeypatch.setattr(server.WMUtils, "is_watermarking_applicable", lambda **kw: True)
    monkeypatch.setattr(server.WMUtils, "apply_watermark", lambda **kw: WATERMARKED_BYTES)
    monkeypatch.setattr(Path, "exists", lambda self: True)

    # --- Input payload ---
    payload = {
        "method": "toy-eof",
        "intended_for": "Alice",
        "secret": "topSecret",
        "key": "strongKey",
        "position": "bottom",
    }

    # --- Execute request ---
    response = client_with_auth.post(f"/api/create-watermark/{DOC_ID}", json=payload)

    # --- Simplified verification ---
    assert response.status_code == 200, response.json
    data = response.get_json()
    assert isinstance(data, dict)
    assert "link" in data
    assert data["link"], "Expected non-empty link in response"

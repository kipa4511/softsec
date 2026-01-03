import sys
import importlib
from pathlib import Path
import uuid


def test_rmap_full_handshake_success(monkeypatch, client_with_auth, tmp_path):
    """
    ✅ Full RMAP handshake test without hardcoded identifiers.
    Uses a dummy RMAP and mocked watermarking to validate the full flow.
    """

    # Ensure fresh import
    sys.modules.pop("server", None)
    server = importlib.import_module("server")

    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path
    app.config["SECRET_KEY"] = "supersecret"

    # -------------------------------
    # 1️⃣ Create dummy RMAP
    # -------------------------------
    class DummyRMAP:
        def __init__(self):
            self.called1 = False
            self.called2 = False

        def handle_message1(self, incoming):
            self.called1 = True
            return {"result": "ok"}

        def handle_message2(self, incoming):
            self.called2 = True
            # Generate a realistic, non-hardcoded filename
            return {"result": uuid.uuid4().hex}

    dummy_rmap = DummyRMAP()

    # -------------------------------
    # 2️⃣ Inject dummy RMAP into route closures
    # -------------------------------
    for rule in app.url_map.iter_rules():
        view_func = app.view_functions[rule.endpoint]
        closure_vars = getattr(view_func, "__closure__", None)
        if closure_vars:
            for cell in closure_vars:
                if (
                    getattr(cell.cell_contents, "__class__", None).__name__.startswith("RMAP")
                    or cell.cell_contents is getattr(server, "rmap", None)
                ):
                    cell.cell_contents = dummy_rmap

    # -------------------------------
    # 3️⃣ Mock watermarking util
    # -------------------------------
    def mock_apply_watermark(method, pdf, secret, key):
        return b"%PDF-1.4\n% WATERMARKED\n%%EOF\n"

    monkeypatch.setattr(
        server.WMUtils,
        "apply_watermark",
        mock_apply_watermark,
    )

    # -------------------------------
    # 4️⃣ Prepare dummy PDF asset
    # -------------------------------
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "base.pdf").write_bytes(b"%PDF-1.4\n%%EOF")

    # -------------------------------
    # 5️⃣ Step 1 - Initiate
    # -------------------------------
    payload_init = {"identity": "Group_04", "payload": "dummy_msg1"}
    resp1 = client_with_auth.post("/api/rmap-initiate", json=payload_init)
    data1 = resp1.get_json()

    assert resp1.status_code == 200, data1
    assert data1["result"] == "ok"
    assert dummy_rmap.called1 is True

    # -------------------------------
    # 6️⃣ Step 2 - Get Link
    # -------------------------------
    payload_get = {"payload": "dummy_msg2"}
    resp2 = client_with_auth.post("/api/rmap-get-link", json=payload_get)
    data2 = resp2.get_json()

    assert resp2.status_code == 200, data2
    assert "result" in data2
    assert data2["link"].endswith(".pdf")
    assert "link" in data2
    assert "identity" in data2
    assert dummy_rmap.called2 is True

    # -------------------------------
    # 7️⃣ Validate output
    # -------------------------------
    pdf_path = tmp_path / data2["link"]

    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF-1.4")

    print("✅ Full RMAP route test passed successfully.")

import importlib
import pickle
from pathlib import Path


def test_load_plugin_success(monkeypatch, client_with_auth, tmp_path):
    """✅ Successfully loads a serialized plugin and registers it in WMUtils.METHODS."""
    import sys
    sys.modules.pop("server", None)
    server = importlib.import_module("server")

    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path

    # --- Prepare fake plugin directory ---
    plugins_dir = tmp_path / "files" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    # --- Define dummy watermarking class ---
    # Must be serializable → define dynamically at module level via type()
    DummyWatermarkMethod = type(
        "DummyWatermarkMethod",
        (),
        {
            "name": "ToyWatermark",
            "add_watermark": lambda self, pdf, **kw: b"WATERMARKED",
            "read_secret": lambda self, pdf, **kw: "SECRET",
        },
    )

    # --- Serialize the class using dill (or pickle fallback) ---
    try:
        import dill as _pickle
    except ImportError:
        import pickle as _pickle

    plugin_file = plugins_dir / "ToyWatermark.pkl"
    with plugin_file.open("wb") as f:
        _pickle.dump(DummyWatermarkMethod, f)

    # --- Patch environment to isolate state ---
    monkeypatch.setattr(server, "WatermarkingMethod", DummyWatermarkMethod)
    server.WMUtils.METHODS.clear()

    # --- Perform API call ---
    payload = {"filename": "ToyWatermark.pkl", "overwrite": False}
    resp = client_with_auth.post("/api/load-plugin", json=payload)
    data = resp.get_json()

    # --- Validate response ---
    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert data["loaded"] is True
    assert data["filename"] == "ToyWatermark.pkl"
    assert data["registered_as"] == "ToyWatermark"
    assert "class_qualname" in data
    assert "methods_count" in data
    assert data["methods_count"] == 1

    # --- Verify registry update ---
    assert "ToyWatermark" in server.WMUtils.METHODS
    instance = server.WMUtils.METHODS["ToyWatermark"]
    assert isinstance(instance, DummyWatermarkMethod)
    assert hasattr(instance, "add_watermark")
    assert hasattr(instance, "read_secret")

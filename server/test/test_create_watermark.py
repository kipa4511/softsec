# test/test_create_watermark.py
import pytest
from pathlib import Path
import server
from server import WMUtils, get_engine
from sqlalchemy import text

# ----------------------------
# Mock Watermark Utils
# ----------------------------
class MockWMUtils:
    @staticmethod
    def apply_watermark(**kwargs):
        if kwargs.get("fail"):
            raise Exception("mock watermark failure")
        return b"%PDF-1.4\n%%EOF\n"

    @staticmethod
    def read_watermark(**kwargs):
        return "SECRET123"

    @staticmethod
    def is_watermarking_applicable(**kwargs):
        return kwargs.get("applicable", True)

# Patch WMUtils globally
server.WMUtils = MockWMUtils

# ----------------------------
# Dummy DB Row / Engine
# ----------------------------
class DummyDocumentRow:
    def __init__(self, doc_id=1, name="sample.pdf", path="sample.pdf"):
        self.id = doc_id
        self.name = name
        self.path = str(path)

class DummyConn:
    def __enter__(self): return self
    def __exit__(self, *a): pass

    def execute(self, query, *args, **kwargs):
        # Return a dummy document row
        self._row = DummyDocumentRow()
        return self

    def first(self):
        return self._row

class DummyEngine:
    def connect(self): return DummyConn()

# ----------------------------
# Fixture to patch engine
# ----------------------------
@pytest.fixture
def patch_engine(monkeypatch):
    monkeypatch.setattr(server, "get_engine", lambda: DummyEngine())

# ----------------------------
# Test Cases
# ----------------------------

def test_create_watermark_success(client_with_auth, tmp_path, patch_engine):
    """✅ Successful watermark creation with valid input."""
    DOC_ID = 1
    file_path = tmp_path / "sample.pdf"
    file_path.write_bytes(b"%PDF-1.4\n%%EOF")

    app = client_with_auth.application
    app.config["STORAGE_DIR"] = tmp_path.resolve()


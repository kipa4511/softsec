import io
import types
import pytest
import hashlib
import builtins
import sys

import watermarking_utils as wu


class DummyMethod:
    name = "dummy"

    def __init__(self):
        self.added = None
        self.read = None
        self.applicable = None

    def add_watermark(self, **kw):
        self.added = kw
        return b"PDFDATA"

    def read_secret(self, **kw):
        self.read = kw
        return "SECRET"

    def is_watermark_applicable(self, **kw):
        self.applicable = kw
        return True


def test_register_and_get_method_success():
    m = DummyMethod()
    wu.register_method(m)
    assert wu.get_method("dummy") is m
    assert wu.get_method(m) is m  # instance passthrough


def test_get_method_unknown():
    with pytest.raises(KeyError) as e:
        wu.get_method("nonexistent")
    assert "Unknown watermarking method" in str(e.value)


def test_apply_and_read_and_applicable(monkeypatch):
    m = DummyMethod()
    wu.register_method(m)
    assert wu.apply_watermark("dummy", b"pdf", "s", "k") == b"PDFDATA"
    assert wu.read_watermark("dummy", b"pdf", "k") == "SECRET"
    assert wu.is_watermarking_applicable("dummy", b"pdf")


def test_sha1_function():
    data = b"abc"
    assert wu._sha1(data) == hashlib.sha1(data).hexdigest()


def test_explore_pdf_with_fitz(monkeypatch):
    """Simulate full fitz path."""
    called = {}

    class DummyDoc:
        page_count = 2
        def load_page(self, i):
            called["page"] = True
            class B:
                def bound(self): return (0,0,100,100)
            return B()
        def xref_length(self): return 3
        def xref_object(self, xref, compressed=False): return "objdata"
        def xref_is_stream(self, xref): return False
        def close(self): called["closed"] = True

    monkeypatch.setattr(wu, "load_pdf_bytes", lambda pdf: b"%PDF-1.4 mock")
    monkeypatch.setitem(sys.modules, "fitz", types.SimpleNamespace(open=lambda **kw: DummyDoc()))

    result = wu.explore_pdf(b"pdfdata")
    assert result["type"] == "Document"
    assert any(c["type"] in ("Page", "Object") for c in result["children"])
    assert "closed" in called


def test_explore_pdf_fallback(monkeypatch):
    """Fallback path when fitz is not available."""
    pdf_bytes = b"1 0 obj\n/Type /Page\nendobj\n2 0 obj\n/Type /Font\nendobj\n"
    monkeypatch.setattr(wu, "load_pdf_bytes", lambda pdf: pdf_bytes)
    # Simulate import error
    monkeypatch.setitem(sys.modules, "fitz", None)
    result = wu.explore_pdf(pdf_bytes)
    assert result["type"] == "Document"
    assert any("Page" in c["type"] for c in result["children"])
    assert any("obj" in c["id"] for c in result["children"])
    assert "children" in result


def test_explore_pdf_handles_invalid_object(monkeypatch):
    """Ensure even broken PDF bytes return deterministic structure."""
    monkeypatch.setattr(wu, "load_pdf_bytes", lambda pdf: b"random bytes no obj markers")
    result = wu.explore_pdf(b"dummy")
    assert result["type"] == "Document"
    assert isinstance(result["children"], list)


def test_methods_registry_contains_expected_keys():
    assert isinstance(wu.METHODS, dict)
    for name, method in wu.METHODS.items():
        assert hasattr(method, "add_watermark")

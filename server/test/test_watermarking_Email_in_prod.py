import io
import os
import hmac
import hashlib
import pytest
from pathlib import Path

import email_in_producer as eip


@pytest.fixture
def pdf_path(tmp_path):
    # Create a dummy "PDF" file for pikepdf.open()
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%%EOF")
    return pdf_file


class DummyPdf:
    """A fake PDF-like object to mock pikepdf behavior."""
    def __init__(self):
        self.docinfo = {}

    def save(self, path):
        # simulate file save
        Path(path).write_text("dummy-pdf-data")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_usage():
    usage = eip.EmailInProducer.get_usage()
    assert "Toy method" in usage


def test_is_email_valid_and_invalid():
    wm = eip.EmailInProducer()
    assert wm.is_email("user@example.com")
    assert not wm.is_email("invalid-email")
    assert not wm.is_email("missing@domain")


def test_extract_email_parts():
    wm = eip.EmailInProducer()
    assert wm.extract_email_parts("john.doe@example.com").startswith("jo")
    assert wm.extract_email_parts("abc@xyz.com").endswith("yz")


def test_build_payload_creates_secret_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_DIR", str(tmp_path))
    wm = eip.EmailInProducer()
    result = wm._build_payload("user@example.com", "key123")
    # Verify secret.txt file was created and contains expected concatenated secret
    secret_path = tmp_path / "secret.txt"
    content = secret_path.read_text()
    assert "user@example.com" in content
    assert isinstance(result, str)
    # verify HMAC calculation consistency
    expected = hmac.new(
        b"key123",
        wm._CONTEXT + content.encode(),
        hashlib.sha256
    ).hexdigest()
    assert result == expected


def test_mac_hex_computation():
    wm = eip.EmailInProducer()
    result = wm._mac_hex(b"secret", "key")
    expected = hmac.new(b"key", wm._CONTEXT + b"secret", hashlib.sha256).hexdigest()
    assert result == expected


def test_add_watermark_success(monkeypatch, tmp_path, pdf_path):
    wm = eip.EmailInProducer()
    monkeypatch.setattr(eip, "pikepdf", type("PikePdf", (), {"open": lambda *a, **kw: DummyPdf()}))
    monkeypatch.setattr(eip, "load_pdf_bytes", lambda p: b"%PDF")
    monkeypatch.setattr(wm, "_build_payload", lambda s, k: "payload123")

    result = wm.add_watermark(pdf_path, "user@example.com", "key123")
    assert result == b"%PDF"


@pytest.mark.parametrize("secret,key", [
    ("", "valid"),
    ("user@example.com", ""),
    ("invalid-email", "key"),
])
def test_add_watermark_invalid_inputs(monkeypatch, pdf_path, secret, key):
    wm = eip.EmailInProducer()
    monkeypatch.setattr(eip, "pikepdf", type("PikePdf", (), {"open": lambda *a, **kw: DummyPdf()}))
    with pytest.raises(ValueError):
        wm.add_watermark(pdf_path, secret, key)


def test_is_watermark_applicable_always_true(pdf_path):
    wm = eip.EmailInProducer()
    assert wm.is_watermark_applicable(pdf_path)


def test_read_secret_success(monkeypatch, tmp_path, pdf_path):
    secret_dir = tmp_path / "storage"
    secret_dir.mkdir()
    secret_file = secret_dir / "secret.txt"
    secret_file.write_text("user@example.comjoex")

    wm = eip.EmailInProducer()
    monkeypatch.setenv("SECRET_DIR", str(secret_dir))

    mac_hex = wm._mac_hex(b"user@example.comjoex", "key123")

    dummy_pdf = DummyPdf()
    dummy_pdf.docinfo["/Producer"] = mac_hex
    monkeypatch.setattr(eip, "pikepdf", type("PikePdf", (), {"open": lambda *a, **kw: dummy_pdf}))

    result = wm.read_secret(pdf_path, "key123")
    assert result == "user@example.comjoex"


def test_read_secret_invalid_key(monkeypatch, tmp_path, pdf_path):
    secret_dir = tmp_path / "storage"
    secret_dir.mkdir()
    (secret_dir / "secret.txt").write_text("content")

    wm = eip.EmailInProducer()
    monkeypatch.setenv("SECRET_DIR", str(secret_dir))
    dummy_pdf = DummyPdf()
    dummy_pdf.docinfo["/Producer"] = "wrongmac"

    monkeypatch.setattr(eip, "pikepdf", type("PikePdf", (), {"open": lambda *a, **kw: dummy_pdf}))

    with pytest.raises(eip.InvalidKeyError):
        wm.read_secret(pdf_path, "key123")


def test_read_secret_file_missing(monkeypatch, tmp_path, pdf_path):
    wm = eip.EmailInProducer()
    secret_dir = tmp_path / "storage"
    secret_dir.mkdir()
    monkeypatch.setenv("SECRET_DIR", str(secret_dir))
    dummy_pdf = DummyPdf()
    dummy_pdf.docinfo["/Producer"] = "whatever"

    monkeypatch.setattr(eip, "pikepdf", type("PikePdf", (), {"open": lambda *a, **kw: dummy_pdf}))

    with pytest.raises(eip.SecretNotFoundError):
        wm.read_secret(pdf_path, "key123")


def test_read_secret_invalid_key_type(monkeypatch, pdf_path):
    wm = eip.EmailInProducer()
    with pytest.raises(ValueError):
        wm.read_secret(pdf_path, 123)

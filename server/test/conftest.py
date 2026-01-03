# test/conftest.py
import sys
import pytest
from pathlib import Path
from functools import wraps
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))


@pytest.fixture
def client_with_auth(monkeypatch, tmp_path):
    """Fully isolates DB, disables auth, and prevents real I/O."""
    sys.modules.pop("server", None)
    import server
    import sqlalchemy

    # -------------------------------------------------
    # Dummy DB Rows
    # -------------------------------------------------
    class DummyDocumentRow:
        id = 1
        name = "demo.pdf"
        creation = "2025-01-01T00:00:00"
        sha256_hex = "ABC123"
        size = 123
        ownerid = 1

    class DummyVersionRow:
        id = 10
        documentid = 1
        link = "xyz"
        intended_for = "tester"
        secret = "SECRET"
        method = "hash-eof"
        path = str(tmp_path / "dummy.pdf")
        name = "dummy.pdf"

    # -------------------------------------------------
    # Dummy Connection
    # -------------------------------------------------
    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

        def execute(self, *a, **kw):
            sql = str(a[0]) if a else ""
            # Return document list queries
            if "FROM Documents" in sql and "JOIN" not in sql:
                self._rows = [DummyDocumentRow()]
            # Return version list queries
            elif "FROM Versions" in sql:
                self._rows = [DummyVersionRow()]
            else:
                self._rows = [DummyDocumentRow()]
            return self

        def all(self): return getattr(self, "_rows", [])
        def first(self): return DummyVersionRow()
        def one(self): return DummyDocumentRow()
        def scalar(self): return 1

    class DummyEngine:
        def connect(self): return DummyConn()
        def begin(self): return DummyConn()

    # Engine that simulates DB failure
    class FailingEngine:
        def connect(self): raise Exception("DB failure")
        def begin(self): raise Exception("DB failure")

    # -------------------------------------------------
    # Patch DB and Auth
    # -------------------------------------------------
    monkeypatch.setattr(sqlalchemy, "text", lambda sql: sql)
    monkeypatch.setattr(server, "create_engine", lambda *a, **kw: DummyEngine(), raising=False)
    monkeypatch.setattr(server, "get_engine", lambda: DummyEngine(), raising=False)

    def no_auth(f):
        @wraps(f)
        def wrapper(*a, **kw):
            return f(*a, **kw)
        return wrapper
    monkeypatch.setattr(server, "require_auth", no_auth, raising=False)

    # -------------------------------------------------
    # Flask App
    # -------------------------------------------------
    app = server.create_app()
    app.config.update(TESTING=True, STORAGE_DIR=tmp_path, SECRET_KEY="test_secret")

    @app.before_request
    def fake_user():
        from flask import g
        g.user = {"id": 1, "login": "tester", "email": "tester@example.com"}

    # Ensure all views use dummy engine
    for name, view in app.view_functions.items():
        view.__globals__["get_engine"] = lambda: DummyEngine()
        if hasattr(view, "__wrapped__"):
            app.view_functions[name] = view.__wrapped__

    # -------------------------------------------------
    # Filesystem Stubbing
    # -------------------------------------------------
    dummy_file = tmp_path / "dummy.pdf"
    dummy_file.write_text("dummy content")
    monkeypatch.setattr(Path, "exists", lambda self: str(self).endswith("dummy.pdf"))

    # Prevent any real MySQL
    try:
        import pymysql
        monkeypatch.setattr(pymysql, "connect", lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("Blocked")))
    except ImportError:
        pass

    with app.test_client() as c:
        yield c


# -------------------------------------------------
# Utility: patch endpoint engine dynamically
# -------------------------------------------------
# In test/conftest.py (replace the helper)
def _patch_get_engine_for_endpoint(app, EngineClass):
    """Force Flask routes to use a specific engine."""
    for name, view in app.view_functions.items():
        g = view.__globals__
        g["get_engine"] = lambda: EngineClass()
        if hasattr(view, "__wrapped__"):
            view.__globals__["get_engine"] = lambda: EngineClass()


# -------------------------------------------------
# Expose FailingEngine for tests
# -------------------------------------------------
class FailingEngine:
    def connect(self): raise Exception("DB failure")
    def begin(self): raise Exception("DB failure")

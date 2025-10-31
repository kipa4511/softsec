import pytest
import json
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from flask import Flask, request, jsonify
from contextlib import ExitStack # Needed for chained context managers

# --- Mock Dependencies ---

# Mock the RMAP class and its methods
class MockRMAP:
    """Mock class to simulate the RMAP handler."""
    def __init__(self, identity_manager):
        self.identity_manager = identity_manager
        self.last_identity = None

    def handle_message1(self, incoming):
        # Mock successful initiation or error based on identity
        if incoming.get("identity") == "ErrorGroup":
            return {"error": "initiation failed"}
        return {"result": "session_id_123"}

    def handle_message2(self, incoming):
        # Mock successful link retrieval or error
        if incoming.get("session_id") == "fail_link":
            return {"error": "link retrieval failed"}
        return {"result": "session_secret_xyz"}

# Mock IdentityManager
class MockIdentityManager:
    """Mock class to simulate the IdentityManager being initialized."""
    def __init__(self, client_keys_dir, server_public_key_path, server_private_key_path, server_private_key_passphrase):
        pass

# Mock WMUtils (Watermarking) - Reverted to simpler version
class MockWMUtils:
    """Mock class to simulate watermarking logic."""
    @staticmethod
    def apply_watermark(method, pdf, secret, key):
        # Simulate a watermarking failure if the pdf path contains 'error' (not used in tests, but safe to keep)
        if "error_pdf" in str(pdf):
            raise Exception("Simulated Watermarking Tool Failure")
        # Default successful return
        return b"watermarked_pdf_content"

# Mock the logger
class MockLogger:
    """Simple mock logger to prevent console output during tests."""
    def warning(self, msg): pass
    def info(self, msg): pass
    def exception(self, msg): pass

# --- Mock Path Class for File Operations ---
# Reverted to simpler version, only supporting basic Path operations
class MockPath(MagicMock):
    """Mock Path class to simulate file existence and write operations."""
    _exists_map = {}
    _written_files = {}

    def __init__(self, *args, **kwargs):
        super().__init__()
        # Use a normalized string path for consistent mapping keys
        self._path_key = os.path.join(*args).replace('\\', '/')
        self.name = args[-1] if args else ""
        self.is_file = True
        # Attach methods dynamically for path manipulation consistency
        self.exists = self.exists_func
        self.parent = MockPath("mock_parent") # Ensure parent has a name for mkdir logging
        self.parent.mkdir = lambda parents=True, exist_ok=True: None
        self.mkdir = lambda parents=True, exist_ok=True: None
        self.write_bytes = self.write_bytes_func

    def __truediv__(self, other):
        # Simulate path joining (e.g., Path("assets") / "file.pdf")
        if isinstance(other, Path):
            other = str(other)
        new_parts = self._path_key.split('/') + [str(other)]
        # Create a new MockPath instance
        new_path = MockPath(*new_parts)
        return new_path

    def exists_func(self):
        """Checks if this path has been mocked as existing."""
        return self._path_key in MockPath._exists_map and MockPath._exists_map[self._path_key]

    def write_bytes_func(self, data):
        """Stores the written content in the mock dictionary."""
        MockPath._written_files[self._path_key] = data

    def __str__(self):
        # Return the normalized key for assertion consistency
        return self._path_key

    @staticmethod
    def reset_mocks():
        """Resets the mock file system state for a fresh test."""
        MockPath._exists_map = {}
        MockPath._written_files = {}

# --- Fixture for Flask Client Setup ---

@pytest.fixture
def client():
    # Use ExitStack to chain multiple context managers (like patch.dict and patch)
    with ExitStack() as stack:
        # 1. Patch environment variables
        stack.enter_context(patch.dict(os.environ, {"SERVER_KEY_PASSPHRASE": "test_passphrase"}))
        # 2. PATCH PATHLIB.PATH HERE to avoid decorator module resolution issues
        stack.enter_context(patch("pathlib.Path", MockPath))

        # Setup minimal Flask app
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test_secret"
        app.config["STORAGE_DIR"] = "/tmp/storage"
        app.logger = MockLogger() # Inject the mock logger

        # Inject Mock Classes into the setup function
        IdentityManager = MockIdentityManager
        RMAP = MockRMAP
        WMUtils = MockWMUtils # WMUtils is the Mock class here
        logger = app.logger

        # Define the provided application logic (setup and routes)
        def setup_rmap_routes(app):
            # -----------------------
            # RMAP setup (Original Code)
            # -----------------------
            _server_pass = os.environ.get("SERVER_KEY_PASSPHRASE")

            identity_manager = IdentityManager(
                client_keys_dir="./keys/clients",
                server_public_key_path="./keys/server_pub.asc",
                server_private_key_path="./keys/server_priv.asc",
                server_private_key_passphrase=_server_pass,
            )
            rmap = RMAP(identity_manager)
            app.config["RMAP_INSTANCE"] = rmap # Store for inspection

            # -----------------------
            # RMAP INITIATE endpoint (Original Code)
            # -----------------------
            CLIENT_KEYS_DIR = Path("./keys/clients")

            @app.route("/rmap-initiate", methods=["POST"], strict_slashes=False)
            @app.route("/api/rmap-initiate", methods=["POST"], strict_slashes=False)
            def rmap_initiate():
                incoming = request.get_json(force=True) or {}
                result = rmap.handle_message1(incoming)
                # Store identity for later use
                rmap.last_identity = incoming.get("identity", "Unknown_Group")
                app.config["LAST_RMAP_REQUEST"] = incoming
                return jsonify(result), (200 if "error" not in result else 400)


            # -----------------------
            # RMAP GET LINK endpoint (Original Code)
            # -----------------------
            @app.route("/rmap-get-link", methods=["POST"], strict_slashes=False)
            @app.route("/api/rmap-get-link", methods=["POST"], strict_slashes=False)
            def rmap_get_link():
                incoming = request.get_json(force=True) or {}
                result = rmap.handle_message2(incoming)
                if "error" in result:
                    return jsonify(result), 400

                session_secret = result["result"]
                # Note: Path is already patched to MockPath
                assets_dir = Path("assets")
                storage_dir = Path(app.config["STORAGE_DIR"])

                # Derive or reuse identity
                identity = getattr(rmap, "last_identity", "Unknown_Group")

                # Determine source PDF
                base_pdf_path = assets_dir / f"{identity}.pdf"
                if not base_pdf_path.exists():
                    base_pdf_path = assets_dir / "base.pdf"
                    if not base_pdf_path.exists():
                        logger.warning(f"No specific PDF found for {identity}, creating placeholder.")
                        base_pdf_path.parent.mkdir(parents=True, exist_ok=True)
                        base_pdf_path.write_bytes(b"%PDF-1.4\n% Placeholder PDF\n")

                # Output PDF path
                pdf_name = f"{session_secret}.pdf"
                pdf_path = storage_dir / pdf_name

                try:
                    # Apply watermark using the local WMUtils (which is MockWMUtils)
                    data = WMUtils.apply_watermark(
                        method="hash-eof",
                        pdf=base_pdf_path,
                        secret=f"Session{session_secret}@test.com",
                        key=app.config["SECRET_KEY"],
                    )

                    storage_dir.mkdir(parents=True, exist_ok=True)
                    if isinstance(data, (bytes, bytearray)):
                        pdf_path.write_bytes(data)
                        logger.info(f"✅ Watermarked PDF written for {identity}: {pdf_path}")
                    else:
                        logger.warning("⚠️ Watermark function did not return bytes")

                except Exception as e:
                    logger.exception(f"❌ Failed to create watermarked PDF: {e}")
                    return jsonify({"error": "watermarking failed"}), 500


                # Return the response
                return jsonify({
                    "result": session_secret,
                    "link": pdf_name,
                    "identity": identity
                }), 200

        setup_rmap_routes(app)

        # Create and yield test client
        with app.test_client() as client:
            yield client

# --- Test Case Class ---

class TestRMAPEndpoints:

    def setup_method(self):
        # Reset mock file system state before each test
        MockPath.reset_mocks()

    # --- RMAP Initiate Tests ---

    def test_rmap_initiate_success(self, client):
        """Test the rmap-initiate endpoint for a successful response (200)."""
        data = {"identity": "TestGroup", "msg1": "data"}
        response = client.post("/api/rmap-initiate", json=data)

        assert response.status_code == 200
        assert response.get_json() == {"result": "session_id_123"}

        # Verify rmap state update
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        assert rmap_instance.last_identity == "TestGroup"

    def test_rmap_initiate_failure(self, client):
        """Test the rmap-initiate endpoint for a failure response (400)."""
        data = {"identity": "ErrorGroup", "msg1": "data"}
        response = client.post("/rmap-initiate", json=data)

        assert response.status_code == 400
        assert response.get_json() == {"error": "initiation failed"}
        # Check that last_identity is still set even on error
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        assert rmap_instance.last_identity == "ErrorGroup"

    # --- RMAP Get Link Tests ---

    def test_rmap_get_link_success_specific_pdf(self, client):
        """Test get-link success with a specific identity PDF found."""
        # 1. Setup RMAP state
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        rmap_instance.last_identity = "TestGroup"

        # 2. Mock file existence: TestGroup.pdf exists
        MockPath._exists_map[str(Path("assets") / "TestGroup.pdf")] = True

        # 3. Request /rmap-get-link
        response = client.post("/api/rmap-get-link", json={"session_id": "success_link"})
        result_json = response.get_json()

        assert response.status_code == 200
        assert result_json["result"] == "session_secret_xyz"
        assert result_json["identity"] == "TestGroup"

        # 4. Verify file was written
        expected_path = str(Path("/tmp/storage") / "session_secret_xyz.pdf")
        assert expected_path in MockPath._written_files
        assert MockPath._written_files[expected_path] == b"watermarked_pdf_content"

    def test_rmap_get_link_success_fallback_pdf(self, client):
        """Test get-link success with fallback to base.pdf."""
        # 1. Setup RMAP state
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        rmap_instance.last_identity = "SpecialGroup"

        # 2. Mock file existence: Specific PDF does NOT exist, but base.pdf DOES exist
        MockPath._exists_map[str(Path("assets") / "SpecialGroup.pdf")] = False
        MockPath._exists_map[str(Path("assets") / "base.pdf")] = True

        # 3. Request /rmap-get-link
        response = client.post("/rmap-get-link", json={"session_id": "success_link"})
        assert response.status_code == 200

    def test_rmap_get_link_success_placeholder_pdf(self, client):
        """Test get-link success when neither specific nor base PDF exists (placeholder created)."""
        # 1. Setup RMAP state
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        rmap_instance.last_identity = "NoPDFGroup"

        # 2. Mock file existence: NEITHER specific nor base PDF exists
        MockPath._exists_map[str(Path("assets") / "NoPDFGroup.pdf")] = False
        MockPath._exists_map[str(Path("assets") / "base.pdf")] = False

        # 3. Request /rmap-get-link
        response = client.post("/rmap-get-link", json={"session_id": "success_link"})
        assert response.status_code == 200

        # 4. Verify placeholder was created
        placeholder_path = str(Path("assets") / "base.pdf")
        assert placeholder_path in MockPath._written_files
        assert MockPath._written_files[placeholder_path] == b"%PDF-1.4\n% Placeholder PDF\n"


    def test_rmap_get_link_rmap_failure(self, client):
        """Test get-link failure due to RMAP handle_message2 error (400)."""
        data = {"session_id": "fail_link"}
        response = client.post("/rmap-get-link", json=data)

        assert response.status_code == 400
        assert response.get_json() == {"error": "link retrieval failed"}

    # Patch the MockWMUtils.apply_watermark function directly
    @patch.object(MockWMUtils, "apply_watermark", side_effect=Exception("Tool Broken"))
    def test_rmap_get_link_watermarking_exception(self, mock_apply_watermark, client):
        """Test get-link failure due to a watermarking exception (500)."""
        # 1. Setup RMAP state
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        rmap_instance.last_identity = "TestGroup"
        # We need a PDF to exist so the flow reaches the WMUtils call
        MockPath._exists_map[str(Path("assets") / "TestGroup.pdf")] = True 

        # 2. Request /rmap-get-link
        response = client.post("/rmap-get-link", json={"session_id": "watermark_fail"})

        assert response.status_code == 500
        assert response.get_json() == {"error": "watermarking failed"}

    # Patch the MockWMUtils.apply_watermark function directly
    @patch.object(MockWMUtils, "apply_watermark", return_value=None)
    def test_rmap_get_link_watermarking_non_bytes_return(self, mock_apply_watermark, client):
        """Test get-link case where watermarking returns non-bytes (should still succeed at 200)."""
        # 1. Setup RMAP state
        rmap_instance = client.application.config["RMAP_INSTANCE"]
        rmap_instance.last_identity = "NonBytesGroup"
        # We need a PDF to exist so the flow reaches the WMUtils call
        MockPath._exists_map[str(Path("assets") / "NonBytesGroup.pdf")] = True 

        # 2. Request /rmap-get-link
        response = client.post("/rmap-get-link", json={"session_id": "non_bytes_return"})

        assert response.status_code == 200
        # Check that no file was written, but the request was successful
        expected_path = str(Path("/tmp/storage") / "session_secret_xyz.pdf")
        assert expected_path not in MockPath._written_files

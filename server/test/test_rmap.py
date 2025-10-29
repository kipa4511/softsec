import os
import subprocess
import time
import shutil
import pytest
from pathlib import Path

from server import create_app


@pytest.mark.skipif(shutil.which("rmap-client") is None, reason="rmap-client not on PATH")
def test_rmap_client_calls_server(tmp_path):
    """Start the Flask app on port 5000 and call rmap-client to exercise /api/rmap-initiate."""

    # Isolated storage directory
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    app = create_app()
    app.config.update(TESTING=True, STORAGE_DIR=str(storage_dir), SECRET_KEY="test_secret")

    # Run on the port expected by rmap-client
    host, port = "127.0.0.1", 5000

    # Start server in background thread
    from threading import Thread
    from werkzeug.serving import make_server

    server = make_server(host, port, app)
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    time.sleep(0.5)  # give server a moment

    try:
        client_priv = "keys/clients/Group_24_priv.asc"
        server_pub = "keys/server_pub.asc"

        assert os.path.exists(client_priv), f"missing: {client_priv}"
        assert os.path.exists(server_pub), f"missing: {server_pub}"

        cmd = [
            "rmap-client",
            "--client-priv", client_priv,
            "--identity", "Group_24",
            "--server-pub", server_pub,
            "--server", host,   # ✅ no port here
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=25,
            text=True,
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        assert proc.returncode == 0, (
            f"rmap-client failed (rc={proc.returncode})\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )

    finally:
        server.shutdown()
        thread.join(timeout=2)

from __future__ import annotations

import io
import time

from garimpo.webapp import create_app


def test_dashboard_page_loads(tmp_path):
    app = create_app(base_dir=tmp_path / "webdata")
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Garimpo Web" in response.get_data(as_text=True)


def test_session_creation_and_completion(tmp_path):
    app = create_app(base_dir=tmp_path / "webdata")
    client = app.test_client()

    image_bytes = b"\xff\xd8\xff\xe0JFIF\x00" + (b"A" * 128) + b"\xff\xd9"
    data = {
        "title": "Teste web",
        "mode": "fast",
        "report_format": "json",
        "max_size": "1MB",
        "chunk_size": "4KB",
        "validate": "on",
        "compute_hashes": "on",
        "skip_duplicates": "on",
        "max_files": "0",
        "image": (io.BytesIO(image_bytes), "evidencia.img"),
    }

    response = client.post("/api/sessions", data=data, content_type="multipart/form-data")

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"]

    deadline = time.time() + 10
    final_payload = None
    while time.time() < deadline:
        status_response = client.get(payload["api_url"])
        assert status_response.status_code == 200
        final_payload = status_response.get_json()
        if final_payload["status"] in {"completed", "error"}:
            break
        time.sleep(0.2)

    assert final_payload is not None
    assert final_payload["status"] == "completed"
    assert final_payload["report_files"]

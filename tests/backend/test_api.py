import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app

client = TestClient(app)

FIXTURE_GLB = Path("tests/pipeline/fixtures/two_box_assembly.glb")


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_job_returns_job_id():
    if not FIXTURE_GLB.exists():
        pytest.skip("Run create_test_assembly.py first")

    with open(FIXTURE_GLB, "rb") as f:
        resp = client.post(
            "/jobs",
            files={"file": ("assembly.glb", f, "application/octet-stream")},
            data={"explode_scalar": "1.5", "style_prompt": "Matte black industrial, dark studio"},
        )
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert len(body["job_id"]) > 0


def test_get_job_status():
    if not FIXTURE_GLB.exists():
        pytest.skip("Run create_test_assembly.py first")

    with open(FIXTURE_GLB, "rb") as f:
        create_resp = client.post(
            "/jobs",
            files={"file": ("assembly.glb", f, "application/octet-stream")},
            data={"explode_scalar": "1.5", "style_prompt": "Matte black industrial, dark studio"},
        )
    job_id = create_resp.json()["job_id"]

    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["job_id"] == job_id
    assert body["status"] in {"queued", "running", "done", "error"}


def test_get_unknown_job_returns_404():
    resp = client.get("/jobs/nonexistent-job-id")
    assert resp.status_code == 404


def test_preview_returns_six_images():
    """Test /preview endpoint with mocked rendering (pyrender requires main thread on macOS)."""
    if not FIXTURE_GLB.exists():
        pytest.skip("Run create_test_assembly.py first")

    dummy_images = {
        face: f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        for face in ("front", "back", "left", "right", "top", "bottom")
    }

    with patch("pipeline.orientation_preview.render_orientation_previews", return_value=dummy_images), \
         patch("pipeline.format_loader.load_assembly", return_value=[]):
        with open(FIXTURE_GLB, "rb") as f:
            resp = client.post(
                "/preview",
                files={"file": ("assembly.glb", f, "application/octet-stream")},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "preview_id" in body
    assert "images" in body
    for face in ("front", "back", "left", "right", "top", "bottom"):
        assert face in body["images"]
        assert body["images"][face].startswith("data:image/png;base64,")


def test_create_job_with_preview_id():
    """Test /jobs with preview_id created from a prior /preview call."""
    if not FIXTURE_GLB.exists():
        pytest.skip("Run create_test_assembly.py first")

    dummy_images = {
        face: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        for face in ("front", "back", "left", "right", "top", "bottom")
    }

    with patch("pipeline.orientation_preview.render_orientation_previews", return_value=dummy_images), \
         patch("pipeline.format_loader.load_assembly", return_value=[]):
        with open(FIXTURE_GLB, "rb") as f:
            preview_resp = client.post(
                "/preview",
                files={"file": ("assembly.glb", f, "application/octet-stream")},
            )
    assert preview_resp.status_code == 200
    preview_id = preview_resp.json()["preview_id"]

    job_resp = client.post(
        "/jobs",
        data={
            "preview_id": preview_id,
            "explode_scalar": "1.5",
            "style_prompt": "",
            "master_angle": "front",
            "rotation_offset_deg": "0.0",
        },
    )
    assert job_resp.status_code == 202
    assert "job_id" in job_resp.json()


def test_create_job_without_file_or_preview_returns_422():
    resp = client.post(
        "/jobs",
        data={"explode_scalar": "1.5"},
    )
    assert resp.status_code == 422

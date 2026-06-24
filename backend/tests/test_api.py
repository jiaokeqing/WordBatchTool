import json
import time
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def make_docx(path: Path) -> None:
    document = Document()
    document.add_paragraph("hello")
    document.save(path)


def test_create_job_rejects_empty_upload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "max_files_per_job", 100)
    with TestClient(app) as client:
        response = client.post("/api/jobs", data={"template_config": json.dumps({})})

    assert response.status_code == 400


def test_template_preview(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    sample = tmp_path / "sample.docx"
    make_docx(sample)
    with TestClient(app) as client:
        with sample.open("rb") as handle:
            response = client.post("/api/templates/preview", files={"sample_template": ("sample.docx", handle)})

    assert response.status_code == 200
    assert response.json()["paragraphs"] == 1


def test_create_job_with_upload_finishes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "max_files_per_job", 100)
    sample = tmp_path / "sample.docx"
    make_docx(sample)
    with TestClient(app) as client:
        with sample.open("rb") as handle:
            response = client.post(
                "/api/jobs",
                data={"template_config": json.dumps({}), "export_pdf": "false"},
                files=[("files", ("sample.docx", handle, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
            )

        assert response.status_code == 200
        job_id = response.json()["id"]
        for _ in range(60):
            detail = client.get(f"/api/jobs/{job_id}").json()
            if detail["status"] in {"succeeded", "partial_failed", "failed"}:
                break
            time.sleep(0.05)

    assert detail["status"] == "succeeded"
    assert detail["total_files"] == 1
    assert detail["succeeded_files"] == 1
    assert detail["download_ready"] is True

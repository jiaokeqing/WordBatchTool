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


def test_template_library_crud_and_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with TestClient(app) as client:
        templates = client.get("/api/templates").json()
        assert len([item for item in templates if item["is_default"]]) == 1
        builtin_id = templates[0]["id"]

        created = client.post(
            "/api/templates",
            json={
                "name": "办公室模板",
                "description": "常用内部文件格式",
                "config": {"builtin": {"body_size": 15, "line_spacing_pt": 24}},
            },
        )
        assert created.status_code == 200
        template_id = created.json()["id"]

        updated = client.put(
            f"/api/templates/{template_id}",
            json={
                "name": "办公室模板 A",
                "description": "更新后的说明",
                "config": {"builtin": {"body_size": 16}},
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "办公室模板 A"

        assert client.post(f"/api/templates/{template_id}/default").status_code == 200
        templates = client.get("/api/templates").json()
        assert [item["id"] for item in templates if item["is_default"]] == [template_id]

        assert client.post(f"/api/templates/{builtin_id}/duplicate").status_code == 200
        assert client.delete(f"/api/templates/{builtin_id}").status_code == 400
        assert client.delete(f"/api/templates/{template_id}").status_code == 400
        assert client.post(f"/api/templates/{builtin_id}/default").status_code == 200
        assert client.delete(f"/api/templates/{template_id}").status_code == 200


def test_create_job_with_template_id_finishes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    sample = tmp_path / "sample.docx"
    make_docx(sample)
    with TestClient(app) as client:
        template = client.post(
            "/api/templates",
            json={"name": "测试模板", "description": "", "config": {"builtin": {"body_size": 14}}},
        ).json()
        with sample.open("rb") as handle:
            response = client.post(
                "/api/jobs",
                data={"template_id": template["id"], "export_pdf": "false"},
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


def test_server_directory_is_not_accepted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/jobs", data={"server_directory": str(tmp_path)})

    assert response.status_code == 400
    assert response.json()["detail"] == "请至少选择一个 Word 文件。"


def test_app_and_platform_info_are_available(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "github_repo", "")
    with TestClient(app) as client:
        app_response = client.get("/api/app/info")
        platform_response = client.get("/api/platform")
        update_response = client.get("/api/app/update-check")

    assert app_response.status_code == 200
    assert platform_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "not_configured"


def test_app_settings_persist_default_open_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with TestClient(app) as client:
        response = client.put(
            "/api/app/settings",
            json={
                "default_open_dir": str(tmp_path / "docs"),
                "max_files_per_job": 120,
                "retention_hours": 48,
                "github_repo": "owner/repo",
            },
        )
        info = client.get("/api/app/info")

    assert response.status_code == 200
    assert info.json()["default_open_dir"] == str(tmp_path / "docs")
    assert info.json()["max_files_per_job"] == 120
    assert info.json()["retention_hours"] == 48
    assert info.json()["github_repo"] == "owner/repo"

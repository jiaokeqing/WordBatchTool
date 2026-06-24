from __future__ import annotations

import json
import mimetypes
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import repository
from .config import settings
from .database import init_db
from .schemas import JobDetail, JobSummary, TemplateConfig, TemplatePreview
from .services.cleanup import cleanup_expired_jobs
from .services.docx_formatter import preview_template
from .services.queue import enqueue_job


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    cleanup_expired_jobs()
    yield


app = FastAPI(title="批量 Word 格式处理", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def bundled_frontend_dir() -> Optional[Path]:
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")) / "frontend",
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
    ]
    for candidate in candidates:
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
    return None


frontend_dir = bundled_frontend_dir()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

@app.post("/api/jobs", response_model=JobSummary)
async def create_job(
    files: list[UploadFile] = File(default=[]),
    template_config: str = Form(default="{}"),
    export_pdf: bool = Form(default=True),
    server_directory: Optional[str] = Form(default=None),
    sample_template: Optional[UploadFile] = File(default=None),
) -> dict:
    config = TemplateConfig.model_validate(json.loads(template_config or "{}"))
    upload_items = [file for file in files if file.filename]
    if server_directory:
        upload_items.extend(_files_from_server_directory(server_directory))
    if not upload_items:
        raise HTTPException(status_code=400, detail="请至少选择一个 Word 文件。")
    if len(upload_items) > settings.max_files_per_job:
        raise HTTPException(status_code=400, detail=f"每批最多 {settings.max_files_per_job} 个文件。")

    job_id = repository.create_job(config, export_pdf, len(upload_items))
    job_dir = settings.jobs_dir / job_id
    upload_dir = job_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        if sample_template and sample_template.filename:
            sample_path = job_dir / "sample_template.docx"
            _save_upload(sample_template, sample_path)
            config.mode = "sample"
            config.sample_template_filename = "sample_template.docx"

        for item in upload_items:
            if _is_upload_file(item):
                relative = _safe_relative_path(item.filename or "unnamed.docx")
                destination = upload_dir / relative
                _save_upload(item, destination)
            else:
                source = item
                relative = _safe_relative_path(source.name)
                destination = upload_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            repository.add_job_file(job_id, destination.name, str(relative))

        # Store the final template config after optional sample upload.
        job = repository.get_job(job_id)
        if job:
            from .database import connect, utc_now

            with connect() as db:
                db.execute(
                    "UPDATE jobs SET template_config = ?, updated_at = ? WHERE id = ?",
                    (config.model_dump_json(), utc_now(), job_id),
                )
    except Exception as exc:
        repository.update_job_status(job_id, "failed")
        raise HTTPException(status_code=500, detail=f"创建任务失败：{exc}") from exc

    enqueue_job(job_id, job_dir)
    return _job_summary(repository.get_job(job_id))


@app.get("/api/jobs", response_model=list[JobSummary])
def list_jobs() -> list[dict]:
    cleanup_expired_jobs()
    return [_job_summary(job) for job in repository.list_jobs()]


@app.get("/api/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str) -> dict:
    cleanup_expired_jobs()
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在。")
    files = repository.get_job_files(job_id)
    detail = _job_summary(job)
    detail["files"] = files
    detail["download_ready"] = bool(job["zip_path"]) and Path(job["zip_path"]).exists()
    return detail


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict:
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在。")
    job_dir = settings.jobs_dir / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    repository.delete_job(job_id)
    return {"ok": True}


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    job = repository.get_job(job_id)
    if not job or not job["zip_path"]:
        raise HTTPException(status_code=404, detail="结果包尚未生成。")
    path = Path(job["zip_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="结果包已不存在。")
    return FileResponse(path, filename=f"{job_id}.zip", media_type="application/zip")


@app.post("/api/templates/preview", response_model=TemplatePreview)
async def template_preview(sample_template: UploadFile = File(...)) -> TemplatePreview:
    if not sample_template.filename or not sample_template.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="样本文档必须是 .docx 文件。")
    temp_dir = settings.data_dir / "template_previews"
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / _safe_filename(sample_template.filename)
    _save_upload(sample_template, path)
    return preview_template(path)


def _job_summary(job: Optional[dict]) -> dict:
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return {
        "id": job["id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "expires_at": job["expires_at"],
        "total_files": job["total_files"],
        "succeeded_files": job["succeeded_files"],
        "failed_files": job["failed_files"],
        "export_pdf": bool(job["export_pdf"]),
    }


def _save_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)


def _is_upload_file(item: object) -> bool:
    return hasattr(item, "filename") and hasattr(item, "file")


def _safe_filename(name: str) -> str:
    return Path(name.replace("\\", "/")).name


def _safe_relative_path(name: str) -> Path:
    parts = [part for part in Path(name.replace("\\", "/")).parts if part not in {"", ".", ".."}]
    if not parts:
        return Path("unnamed.docx")
    return Path(*parts)


def _files_from_server_directory(directory: str) -> list[Path]:
    requested = Path(directory).resolve()
    if not any(requested == allowed or requested.is_relative_to(allowed) for allowed in settings.allowed_dirs):
        raise HTTPException(status_code=400, detail="该服务器目录不在允许导入范围内。")
    return [path for path in requested.rglob("*") if path.suffix.lower() in {".doc", ".docx"} and path.is_file()]


if frontend_dir:
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

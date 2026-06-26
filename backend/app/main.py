from __future__ import annotations

import json
import mimetypes
import platform
import shutil
import sys
import urllib.error
import urllib.request
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
from .schemas import (
    AppInfo,
    AppSettingsUpdate,
    JobDetail,
    JobSummary,
    PlatformInfo,
    TemplateConfig,
    TemplateCreate,
    TemplateLibraryItem,
    TemplatePreview,
    TemplateUpdate,
    UpdateCheck,
)
from .services.cleanup import cleanup_expired_jobs
from .services.converter import detect_engines, recommended_engine_id
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
    template_id: Optional[str] = Form(default=None),
    export_pdf: bool = Form(default=True),
    sample_template: Optional[UploadFile] = File(default=None),
) -> dict:
    config = _resolve_template_config(template_config, template_id)
    upload_items = [file for file in files if file.filename]
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


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "name": "文档工作台 API", "version": settings.app_version}


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


@app.get("/api/templates", response_model=list[TemplateLibraryItem])
def list_templates() -> list[dict]:
    return repository.list_templates()


@app.post("/api/templates", response_model=TemplateLibraryItem)
def create_template(payload: TemplateCreate) -> dict:
    return repository.create_template(payload)


@app.put("/api/templates/{template_id}", response_model=TemplateLibraryItem)
def update_template(template_id: str, payload: TemplateUpdate) -> dict:
    try:
        template = repository.update_template(template_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在。")
    return template


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str) -> dict:
    try:
        deleted = repository.delete_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="模板不存在。")
    return {"ok": True}


@app.post("/api/templates/{template_id}/duplicate", response_model=TemplateLibraryItem)
def duplicate_template(template_id: str) -> dict:
    template = repository.duplicate_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在。")
    return template


@app.post("/api/templates/{template_id}/default", response_model=TemplateLibraryItem)
def set_default_template(template_id: str) -> dict:
    template = repository.set_default_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在。")
    return template


@app.get("/api/app/info", response_model=AppInfo)
def app_info() -> dict:
    return {
        "name": "文档工作台",
        "version": settings.app_version,
        "mode": "desktop" if getattr(sys, "frozen", False) else "web",
        "data_dir": str(settings.data_dir.resolve()),
        "default_open_dir": repository.get_setting("default_open_dir", ""),
        "max_files_per_job": _configured_int("max_files_per_job", settings.max_files_per_job),
        "retention_hours": _configured_int("retention_hours", settings.retention_hours),
        "worker_count": settings.worker_count,
        "github_repo": _configured_github_repo(),
    }


@app.put("/api/app/settings", response_model=AppInfo)
def update_app_settings(payload: AppSettingsUpdate) -> dict:
    repository.set_setting("default_open_dir", payload.default_open_dir.strip())
    repository.set_setting("max_files_per_job", str(payload.max_files_per_job))
    repository.set_setting("retention_hours", str(payload.retention_hours))
    repository.set_setting("github_repo", payload.github_repo.strip())
    return app_info()


@app.get("/api/app/update-check", response_model=UpdateCheck)
def update_check() -> dict:
    repo = _configured_github_repo()
    if not repo:
        return {
            "ok": False,
            "status": "not_configured",
            "current_version": settings.app_version,
            "message": "尚未配置 GitHub 仓库，无法检查更新。",
        }
    try:
        latest = _fetch_latest_release(repo)
    except Exception as exc:
        return {
            "ok": False,
            "status": "offline",
            "current_version": settings.app_version,
            "message": f"无法连接 GitHub，离线功能不受影响：{exc}",
        }
    repository.set_setting("last_update_check", latest["checked_at"])
    is_newer = _normalize_version(latest["tag_name"]) != _normalize_version(settings.app_version)
    return {
        "ok": True,
        "status": "update_available" if is_newer else "latest",
        "current_version": settings.app_version,
        "latest_version": latest["tag_name"],
        "release_url": latest["html_url"],
        "message": "发现新版本。" if is_newer else "当前已是最新版本。",
    }


@app.get("/api/platform", response_model=PlatformInfo)
def platform_info() -> dict:
    system = platform.system()
    machine = platform.machine() or "unknown"
    return {
        "os": system,
        "machine": machine,
        "platform_label": _platform_label(system),
        "engines": [engine.__dict__ for engine in detect_engines()],
        "recommended_engine": recommended_engine_id(),
        "offline_ready": True,
        "message": "模板、排版、任务记录、本地导出均可离线使用。",
    }


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


def _resolve_template_config(template_config: str, template_id: Optional[str]) -> TemplateConfig:
    if template_config and template_config.strip() not in {"", "{}"}:
        return TemplateConfig.model_validate(json.loads(template_config))
    if template_id:
        template = repository.get_template(template_id)
        if not template:
            raise HTTPException(status_code=400, detail="选择的模板不存在。")
        return template["config"]
    default = repository.get_default_template()
    return default["config"] if default else TemplateConfig()


def _configured_int(key: str, default: int) -> int:
    value = repository.get_setting(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def _configured_github_repo() -> str:
    return repository.get_setting("github_repo", settings.github_repo).strip()


def _fetch_latest_release(repo: str) -> dict:
    from .database import utc_now

    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "WordBatchTool"},
    )
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub 返回 {exc.code}") from exc
    return {
        "tag_name": payload.get("tag_name") or payload.get("name") or "",
        "html_url": payload.get("html_url") or f"https://github.com/{repo}/releases",
        "checked_at": utc_now(),
    }


def _normalize_version(value: str) -> str:
    return value.strip().lower().removeprefix("v")


def _platform_label(system: str) -> str:
    if system == "Windows":
        return "Windows"
    if system == "Linux":
        return "Linux / 统信 UOS"
    if system == "Darwin":
        return "macOS"
    return system or "未知系统"


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


if frontend_dir:
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

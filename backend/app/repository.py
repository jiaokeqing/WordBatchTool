from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import settings
from .database import connect, utc_now
from .schemas import TemplateConfig


def create_job(template_config: TemplateConfig, export_pdf: bool, total_files: int) -> str:
    job_id = str(uuid.uuid4())
    now = utc_now()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=settings.retention_hours)).isoformat()
    with connect() as db:
        db.execute(
            """
            INSERT INTO jobs (id, status, template_config, export_pdf, created_at, updated_at, expires_at, total_files)
            VALUES (?, 'queued', ?, ?, ?, ?, ?, ?)
            """,
            (job_id, template_config.model_dump_json(), int(export_pdf), now, now, expires_at, total_files),
        )
    return job_id


def add_job_file(job_id: str, original_name: str, relative_path: str) -> str:
    file_id = str(uuid.uuid4())
    now = utc_now()
    with connect() as db:
        db.execute(
            """
            INSERT INTO job_files (id, job_id, original_name, relative_path, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'queued', ?, ?)
            """,
            (file_id, job_id, original_name, relative_path, now, now),
        )
    return file_id


def list_jobs() -> list[dict]:
    with connect() as db:
        return db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()


def get_job(job_id: str) -> Optional[dict]:
    with connect() as db:
        return db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def get_job_files(job_id: str) -> list[dict]:
    with connect() as db:
        return db.execute("SELECT * FROM job_files WHERE job_id = ? ORDER BY relative_path", (job_id,)).fetchall()


def delete_job(job_id: str) -> bool:
    with connect() as db:
        job = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return False
        db.execute("DELETE FROM job_files WHERE job_id = ?", (job_id,))
        db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return True


def update_job_status(job_id: str, status: str, zip_path: Optional[str] = None) -> None:
    with connect() as db:
        db.execute(
            "UPDATE jobs SET status = ?, zip_path = COALESCE(?, zip_path), updated_at = ? WHERE id = ?",
            (status, zip_path, utc_now(), job_id),
        )


def update_file_result(file_id: str, status: str, message: str = "", output_path: Optional[str] = None) -> None:
    with connect() as db:
        db.execute(
            """
            UPDATE job_files SET status = ?, message = ?, output_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, message, output_path, utc_now(), file_id),
        )


def refresh_job_counts(job_id: str) -> None:
    with connect() as db:
        succeeded = db.execute(
            "SELECT COUNT(*) AS count FROM job_files WHERE job_id = ? AND status = 'succeeded'",
            (job_id,),
        ).fetchone()["count"]
        failed = db.execute(
            "SELECT COUNT(*) AS count FROM job_files WHERE job_id = ? AND status = 'failed'",
            (job_id,),
        ).fetchone()["count"]
        db.execute(
            "UPDATE jobs SET succeeded_files = ?, failed_files = ?, updated_at = ? WHERE id = ?",
            (succeeded, failed, utc_now(), job_id),
        )


def parse_template_config(job: dict) -> TemplateConfig:
    return TemplateConfig.model_validate(json.loads(job["template_config"]))

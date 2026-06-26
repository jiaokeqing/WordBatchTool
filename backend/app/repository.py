from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import settings
from .database import connect, utc_now
from .schemas import TemplateConfig, TemplateCreate, TemplateUpdate


def create_job(template_config: TemplateConfig, export_pdf: bool, total_files: int) -> str:
    job_id = str(uuid.uuid4())
    now = utc_now()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=configured_int("retention_hours", settings.retention_hours))).isoformat()
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


def list_templates() -> list[dict]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT * FROM templates
            ORDER BY is_default DESC, is_builtin DESC, updated_at DESC, name COLLATE NOCASE
            """
        ).fetchall()
    return [_template_row(row) for row in rows]


def get_template(template_id: str) -> Optional[dict]:
    with connect() as db:
        row = db.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    return _template_row(row) if row else None


def get_default_template() -> Optional[dict]:
    with connect() as db:
        row = db.execute("SELECT * FROM templates WHERE is_default = 1 ORDER BY is_builtin DESC LIMIT 1").fetchone()
    return _template_row(row) if row else None


def create_template(payload: TemplateCreate) -> dict:
    template_id = str(uuid.uuid4())
    now = utc_now()
    with connect() as db:
        db.execute(
            """
            INSERT INTO templates (id, name, description, config_json, is_builtin, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (
                template_id,
                payload.name.strip(),
                payload.description.strip(),
                payload.config.model_dump_json(),
                now,
                now,
            ),
        )
    template = get_template(template_id)
    if not template:
        raise RuntimeError("模板创建失败。")
    return template


def update_template(template_id: str, payload: TemplateUpdate) -> Optional[dict]:
    with connect() as db:
        row = db.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            return None
        if row["is_builtin"]:
            raise ValueError("内置模板不能直接修改，请先复制。")
        db.execute(
            """
            UPDATE templates
            SET name = ?, description = ?, config_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.name.strip(),
                payload.description.strip(),
                payload.config.model_dump_json(),
                utc_now(),
                template_id,
            ),
        )
    return get_template(template_id)


def delete_template(template_id: str) -> bool:
    with connect() as db:
        row = db.execute("SELECT is_builtin, is_default FROM templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            return False
        if row["is_builtin"]:
            raise ValueError("内置模板不能删除。")
        if row["is_default"]:
            raise ValueError("默认模板不能删除，请先设置其他默认模板。")
        db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        return True


def duplicate_template(template_id: str) -> Optional[dict]:
    source = get_template(template_id)
    if not source:
        return None
    return create_template(
        TemplateCreate(
            name=f"{source['name']} 副本",
            description=source["description"],
            config=source["config"],
        )
    )


def set_default_template(template_id: str) -> Optional[dict]:
    with connect() as db:
        row = db.execute("SELECT id FROM templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            return None
        now = utc_now()
        db.execute("UPDATE templates SET is_default = 0, updated_at = ?", (now,))
        db.execute("UPDATE templates SET is_default = 1, updated_at = ? WHERE id = ?", (now, template_id))
    return get_template(template_id)


def get_setting(key: str, default: str = "") -> str:
    with connect() as db:
        row = db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def configured_int(key: str, default: int) -> int:
    value = get_setting(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def set_setting(key: str, value: str) -> None:
    now = utc_now()
    with connect() as db:
        db.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )


def _template_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "config": TemplateConfig.model_validate(json.loads(row["config_json"])),
        "is_builtin": bool(row["is_builtin"]),
        "is_default": bool(row["is_default"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

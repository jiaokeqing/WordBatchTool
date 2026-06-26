import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import settings
from .schemas import BuiltInTemplate, TemplateConfig


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                template_config TEXT NOT NULL,
                export_pdf INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                total_files INTEGER NOT NULL DEFAULT 0,
                succeeded_files INTEGER NOT NULL DEFAULT 0,
                failed_files INTEGER NOT NULL DEFAULT 0,
                zip_path TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS job_files (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                output_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                config_json TEXT NOT NULL,
                is_builtin INTEGER NOT NULL DEFAULT 0,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        seed_builtin_template(db)


def seed_builtin_template(db: sqlite3.Connection) -> None:
    row = db.execute("SELECT id FROM templates WHERE id = ?", ("builtin-paper-photo",)).fetchone()
    if row:
        return
    now = utc_now()
    db.execute(
        """
        INSERT INTO templates (id, name, description, config_json, is_builtin, is_default, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, 1, ?, ?)
        """,
        (
            "builtin-paper-photo",
            "图片格式要求",
            "标题居中，正文仿宋，标题顶格，正文首行缩进。",
            TemplateConfig(builtin=BuiltInTemplate(preset="paper-photo")).model_dump_json(),
            now,
            now,
        ),
    )


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.database_path)
    db.row_factory = dict_factory
    try:
        yield db
        db.commit()
    finally:
        db.close()

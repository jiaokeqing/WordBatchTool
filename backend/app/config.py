from __future__ import annotations

from pathlib import Path
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return Path("data")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORD_BATCH_")

    app_version: str = "1.0.0"
    github_repo: str = ""
    data_dir: Path = default_data_dir()
    max_files_per_job: int = 100
    retention_hours: int = 24
    worker_count: int = 2

    @property
    def database_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

settings = Settings()

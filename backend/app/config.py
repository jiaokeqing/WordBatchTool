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

    data_dir: Path = default_data_dir()
    allowed_import_dirs: str = ""
    max_files_per_job: int = 100
    retention_hours: int = 24
    worker_count: int = 2

    @property
    def database_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def allowed_dirs(self) -> list[Path]:
        return [Path(item).resolve() for item in self.allowed_import_dirs.split(";") if item.strip()]


settings = Settings()

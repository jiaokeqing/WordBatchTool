from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..config import settings
from .processor import process_job


executor = ThreadPoolExecutor(max_workers=settings.worker_count)


def enqueue_job(job_id: str, job_dir: Path) -> None:
    executor.submit(process_job, job_id, job_dir)

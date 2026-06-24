import shutil
from datetime import datetime, timezone

from ..config import settings
from ..database import connect, utc_now


def cleanup_expired_jobs() -> int:
    now = datetime.now(timezone.utc)
    removed = 0
    with connect() as db:
        jobs = db.execute("SELECT * FROM jobs WHERE status != 'expired'").fetchall()
        for job in jobs:
            expires_at = datetime.fromisoformat(job["expires_at"])
            if expires_at > now:
                continue
            job_dir = settings.jobs_dir / job["id"]
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
            db.execute("UPDATE jobs SET status = 'expired', updated_at = ? WHERE id = ?", (utc_now(), job["id"]))
            removed += 1
    return removed

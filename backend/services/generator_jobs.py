"""
In-memory job state for signal generator progress tracking.
"""
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict

_jobs: Dict[str, dict] = {}
_lock = threading.Lock()


def create_job() -> str:
    """Create a new job entry, return job_id."""
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "current_pair": "",
            "last_completed": "",
            "pairs_total": 0,
            "pairs_scanned": 0,
            "signals_found": 0,
            "signals_created": 0,
            "signals_failed": 0,
            "log": "",
            "error": None,
        }
    return job_id


def update_job(job_id: str, **kwargs):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def get_job(job_id: str) -> dict:
    with _lock:
        return dict(_jobs.get(job_id, {}))


def cleanup_old_jobs(max_age_seconds: int = 3600):
    """Remove jobs older than 1 hour."""
    now = datetime.now(timezone.utc)
    with _lock:
        to_delete = []
        for job_id, job in _jobs.items():
            if job.get("started_at"):
                try:
                    started = datetime.fromisoformat(job["started_at"])
                    if (now - started).total_seconds() > max_age_seconds:
                        to_delete.append(job_id)
                except:
                    pass
        for job_id in to_delete:
            del _jobs[job_id]
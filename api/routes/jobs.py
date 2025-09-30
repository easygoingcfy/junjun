# TODO
# - /jobs/{id} 查询状态，/jobs/{id}/cancel 取消

from fastapi import APIRouter
from core.jobs.queue import JobQueue

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def job_status(job_id: str):
    q = JobQueue.instance()
    return q.status(job_id)


@router.post("/{job_id}/cancel")
async def job_cancel(job_id: str):
    q = JobQueue.instance()
    ok = q.cancel(job_id)
    return {"job_id": job_id, "cancelled": ok}

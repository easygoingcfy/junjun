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

@router.get("/stats")
async def get_job_stats():
    """获取任务统计信息"""
    q = JobQueue.instance()
    # 统计各种状态的任务数量
    running_count = 0
    pending_count = 0
    
    # 遍历所有任务状态
    for job_id in q._futures.keys():
        status_info = q.status(job_id)
        status = status_info.get("status", "unknown")
        if status == "running":
            running_count += 1
        elif status == "pending":
            pending_count += 1
    
    return {
        "running_tasks": running_count,
        "pending_tasks": pending_count,
        "total_tasks": len(q._futures)
    }

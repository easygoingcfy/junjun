import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict


class JobQueue:
    """内存线程池实现(简版)
    - submit 返回 job_id
    - status 查询状态(pending/running/success/failed)
    - cancel 尝试取消(若任务未开始)
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: Dict[str, Future] = {}

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = JobQueue()
            return cls._instance

    def submit(self, func, *args, **kwargs) -> str:
        job_id = str(uuid.uuid4())
        future = self._executor.submit(func, *args, **kwargs)
        self._futures[job_id] = future
        return job_id

    def status(self, job_id: str) -> dict:
        f = self._futures.get(job_id)
        if f is None:
            return {"job_id": job_id, "status": "not_found"}
        if f.running():
            return {"job_id": job_id, "status": "running"}
        if f.cancelled():
            return {"job_id": job_id, "status": "cancelled"}
        if f.done():
            try:
                result = f.result()
                return {"job_id": job_id, "status": "success", "result": result}
            except Exception as e:
                return {"job_id": job_id, "status": "failed", "error": str(e)}
        return {"job_id": job_id, "status": "pending"}

    def cancel(self, job_id: str) -> bool:
        f = self._futures.get(job_id)
        if f is None:
            return False
        return f.cancel()

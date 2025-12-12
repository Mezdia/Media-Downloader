from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from .config import Settings
from .database import Database
from .i18n import I18n
from .progress import AdminLogger
from .youtube import YoutubeService


@dataclass(slots=True)
class TaskInfo:
    job_id: str
    user_id: int
    chat_id: int
    youtube_id: str
    quality: int
    title: str
    started_at: datetime
    task: asyncio.Task


class AppState:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        i18n: I18n,
        youtube: YoutubeService,
    ) -> None:
        self.settings = settings
        self.db = db
        self.i18n = i18n
        self.youtube = youtube
        self.download_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        self.tasks: dict[str, TaskInfo] = {}
        self._tasks_lock = asyncio.Lock()
        self.admin_logger: AdminLogger | None = None

    async def get_admin_ids(self) -> set[int]:
        return await self.db.list_admins()

    async def is_admin(self, user_id: int) -> bool:
        return user_id in await self.get_admin_ids()

    async def register_task(self, info: TaskInfo) -> None:
        async with self._tasks_lock:
            self.tasks[info.job_id] = info

    async def unregister_task(self, job_id: str) -> None:
        async with self._tasks_lock:
            self.tasks.pop(job_id, None)

    async def get_task(self, job_id: str) -> TaskInfo | None:
        async with self._tasks_lock:
            return self.tasks.get(job_id)

    async def list_tasks(self) -> list[TaskInfo]:
        async with self._tasks_lock:
            return list(self.tasks.values())

    async def cancel_task(self, job_id: str) -> bool:
        async with self._tasks_lock:
            info = self.tasks.get(job_id)
            if info is None:
                return False
            info.task.cancel()
            return True


def utcnow() -> datetime:
    return datetime.now(UTC)
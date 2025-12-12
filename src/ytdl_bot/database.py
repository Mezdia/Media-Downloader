from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite

from .models import ActiveJob, CacheEntry, PendingRequest


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    language TEXT,
    daily_usage_bytes INTEGER NOT NULL DEFAULT 0,
    usage_window_start TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_created_at ON usage_events(user_id, created_at);

CREATE TABLE IF NOT EXISTS cache (
    youtube_id TEXT NOT NULL,
    quality INTEGER NOT NULL,
    group_chat_id INTEGER NOT NULL,
    group_message_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    filesize_bytes INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL,
    uploader_id INTEGER NOT NULL,
    PRIMARY KEY (youtube_id, quality)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    youtube_id TEXT NOT NULL,
    title TEXT NOT NULL,
    quality INTEGER NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS pending_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    youtube_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    thumbnail_url TEXT,
    quality_sizes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pending_requests_user ON pending_requests(user_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    added_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path.as_posix())
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._ensure_users_columns()
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def _ensure_users_columns(self) -> None:
        cur = await self.conn.execute("PRAGMA table_info(users)")
        rows = await cur.fetchall()
        columns = {row["name"] for row in rows}
        if "daily_usage_bytes" not in columns:
            await self.conn.execute("ALTER TABLE users ADD COLUMN daily_usage_bytes INTEGER NOT NULL DEFAULT 0")
        if "usage_window_start" not in columns:
            await self.conn.execute("ALTER TABLE users ADD COLUMN usage_window_start TEXT")

    async def seed_admins(self, admins: set[int]) -> None:
        if not admins:
            return
        now = _utcnow_iso()
        await self.conn.executemany(
            "INSERT OR IGNORE INTO admins(user_id, added_at) VALUES (?, ?)",
            [(admin_id, now) for admin_id in admins],
        )
        await self.conn.commit()

    async def list_admins(self) -> set[int]:
        cur = await self.conn.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return {int(row["user_id"]) for row in rows}

    async def add_admin(self, user_id: int) -> None:
        await self.conn.execute(
            "INSERT OR REPLACE INTO admins(user_id, added_at) VALUES (?, ?)",
            (user_id, _utcnow_iso()),
        )
        await self.conn.commit()

    async def remove_admin(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def upsert_user(self, user_id: int, username: str | None, language: str | None = None) -> None:
        now = _utcnow_iso()
        cur = await self.conn.execute("SELECT user_id, language FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            next_language = language if language is not None else row["language"]
            await self.conn.execute(
                "UPDATE users SET username = ?, language = ?, updated_at = ? WHERE user_id = ?",
                (username, next_language, now, user_id),
            )
        else:
            await self.conn.execute(
                "INSERT INTO users(user_id, username, language, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, language, now, now),
            )
        await self.conn.commit()

    async def set_user_language(self, user_id: int, language: str) -> None:
        now = _utcnow_iso()
        await self.conn.execute(
            """
            INSERT INTO users(user_id, username, language, created_at, updated_at)
            VALUES (?, NULL, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language, updated_at = excluded.updated_at
            """,
            (user_id, language, now, now),
        )
        await self.conn.commit()

    async def get_user_language(self, user_id: int) -> str | None:
        cur = await self.conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return row["language"]

    async def add_usage_event(self, user_id: int, bytes_used: int) -> None:
        await self.conn.execute(
            "INSERT INTO usage_events(user_id, bytes, created_at) VALUES (?, ?, ?)",
            (user_id, bytes_used, _utcnow_iso()),
        )
        await self.conn.commit()

    async def get_usage_bytes(self, user_id: int, rolling_window_seconds: int) -> int:
        threshold = (datetime.now(UTC) - timedelta(seconds=rolling_window_seconds)).isoformat()
        cur = await self.conn.execute(
            "SELECT COALESCE(SUM(bytes), 0) AS total FROM usage_events WHERE user_id = ? AND created_at >= ?",
            (user_id, threshold),
        )
        row = await cur.fetchone()
        return int(row["total"] if row else 0)

    async def reset_usage(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM usage_events WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def upsert_cache(
        self,
        youtube_id: str,
        quality: int,
        group_chat_id: int,
        group_message_id: int,
        file_id: str,
        filesize_bytes: int,
        uploader_id: int,
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO cache(
                youtube_id, quality, group_chat_id, group_message_id, file_id,
                filesize_bytes, uploaded_at, uploader_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(youtube_id, quality)
            DO UPDATE SET
                group_chat_id = excluded.group_chat_id,
                group_message_id = excluded.group_message_id,
                file_id = excluded.file_id,
                filesize_bytes = excluded.filesize_bytes,
                uploaded_at = excluded.uploaded_at,
                uploader_id = excluded.uploader_id
            """,
            (
                youtube_id,
                quality,
                group_chat_id,
                group_message_id,
                file_id,
                filesize_bytes,
                _utcnow_iso(),
                uploader_id,
            ),
        )
        await self.conn.commit()

    async def get_cache(self, youtube_id: str, quality: int) -> CacheEntry | None:
        cur = await self.conn.execute(
            "SELECT * FROM cache WHERE youtube_id = ? AND quality = ?",
            (youtube_id, quality),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return CacheEntry(
            youtube_id=row["youtube_id"],
            quality=int(row["quality"]),
            group_chat_id=int(row["group_chat_id"]),
            group_message_id=int(row["group_message_id"]),
            file_id=row["file_id"],
            filesize_bytes=int(row["filesize_bytes"]),
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            uploader_id=int(row["uploader_id"]),
        )

    async def delete_cache(self, youtube_id: str, quality: int) -> None:
        await self.conn.execute(
            "DELETE FROM cache WHERE youtube_id = ? AND quality = ?",
            (youtube_id, quality),
        )
        await self.conn.commit()

    async def create_pending_request(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        youtube_id: str,
        url: str,
        title: str,
        description: str,
        thumbnail_url: str | None,
        quality_sizes: dict[int, int | None],
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO pending_requests(
                user_id, chat_id, message_id, youtube_id, url, title,
                description, thumbnail_url, quality_sizes_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                chat_id,
                message_id,
                youtube_id,
                url,
                title,
                description,
                thumbnail_url,
                json.dumps({str(k): v for k, v in quality_sizes.items()}),
                _utcnow_iso(),
            ),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_pending_request(self, request_id: int) -> PendingRequest | None:
        cur = await self.conn.execute(
            "SELECT * FROM pending_requests WHERE request_id = ?",
            (request_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None

        quality_sizes_raw = json.loads(row["quality_sizes_json"])
        quality_sizes = {int(k): (int(v) if v is not None else None) for k, v in quality_sizes_raw.items()}

        return PendingRequest(
            request_id=int(row["request_id"]),
            user_id=int(row["user_id"]),
            chat_id=int(row["chat_id"]),
            message_id=int(row["message_id"]),
            youtube_id=row["youtube_id"],
            url=row["url"],
            title=row["title"],
            description=row["description"],
            thumbnail_url=row["thumbnail_url"],
            quality_sizes=quality_sizes,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def delete_pending_request(self, request_id: int) -> None:
        await self.conn.execute("DELETE FROM pending_requests WHERE request_id = ?", (request_id,))
        await self.conn.commit()

    async def prune_pending_requests(self, older_than_seconds: int = 3600) -> None:
        threshold = (datetime.now(UTC) - timedelta(seconds=older_than_seconds)).isoformat()
        await self.conn.execute("DELETE FROM pending_requests WHERE created_at < ?", (threshold,))
        await self.conn.commit()

    async def create_job(
        self,
        job_id: str,
        user_id: int,
        chat_id: int,
        youtube_id: str,
        title: str,
        quality: int,
        status: str,
    ) -> None:
        now = _utcnow_iso()
        await self.conn.execute(
            """
            INSERT INTO jobs(job_id, user_id, chat_id, youtube_id, title, quality, status, progress, created_at, updated_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL)
            """,
            (job_id, user_id, chat_id, youtube_id, title, quality, status, now, now),
        )
        await self.conn.commit()

    async def update_job(
        self,
        job_id: str,
        status: str,
        progress: float,
        error: str | None = None,
    ) -> None:
        await self.conn.execute(
            "UPDATE jobs SET status = ?, progress = ?, updated_at = ?, error = ? WHERE job_id = ?",
            (status, progress, _utcnow_iso(), error, job_id),
        )
        await self.conn.commit()

    async def delete_job(self, job_id: str) -> None:
        await self.conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        await self.conn.commit()

    async def list_active_jobs(self) -> list[ActiveJob]:
        cur = await self.conn.execute(
            "SELECT * FROM jobs WHERE status IN ('queued', 'downloading', 'merging', 'uploading') ORDER BY created_at"
        )
        rows = await cur.fetchall()
        return [
            ActiveJob(
                job_id=row["job_id"],
                user_id=int(row["user_id"]),
                chat_id=int(row["chat_id"]),
                youtube_id=row["youtube_id"],
                title=row["title"],
                quality=int(row["quality"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def set_setting(self, key: str, value: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, _utcnow_iso()),
        )
        await self.conn.commit()

    async def get_setting(self, key: str) -> str | None:
        cur = await self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        if not row:
            return None
        return row["value"]


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()
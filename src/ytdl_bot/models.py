from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ALLOWED_QUALITIES = (240, 360, 480, 720, 1080, 2160)


@dataclass(slots=True)
class QualityOption:
    quality: int
    format_id: str | None
    requires_merge: bool
    ext: str
    filesize_bytes: int | None


@dataclass(slots=True)
class ProbeResult:
    youtube_id: str
    url: str
    title: str
    description: str
    thumbnail_url: str | None
    duration_seconds: int | None
    qualities: dict[int, QualityOption]


@dataclass(slots=True)
class DownloadResult:
    youtube_id: str
    quality: int
    file_path: Path
    file_size_bytes: int
    title: str
    description: str


@dataclass(slots=True)
class CacheEntry:
    youtube_id: str
    quality: int
    group_chat_id: int
    group_message_id: int
    file_id: str
    filesize_bytes: int
    uploaded_at: datetime
    uploader_id: int


@dataclass(slots=True)
class PendingRequest:
    request_id: int
    user_id: int
    chat_id: int
    message_id: int
    youtube_id: str
    url: str
    title: str
    description: str
    thumbnail_url: str | None
    quality_sizes: dict[int, int | None]
    created_at: datetime


@dataclass(slots=True)
class ActiveJob:
    job_id: str
    user_id: int
    chat_id: int
    youtube_id: str
    title: str
    quality: int
    created_at: datetime
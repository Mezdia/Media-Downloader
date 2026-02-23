from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when environment configuration is invalid."""


@dataclass(slots=True)
class Settings:
    bot_token: str
    bot_telegram_id: str
    admins: set[int]
    group_chat_id: int | None
    github_developer_url: str
    github_project_url: str
    database_path: Path
    storage_path: Path
    max_daily_traffic_bytes: int
    max_concurrent_downloads: int
    download_timeout_seconds: int
    ffmpeg_path: str
    log_level: str
    rolling_window_seconds: int = 24 * 60 * 60

    @property
    def cache_key_prefix(self) -> str:
        return "yt"


def _parse_admins(raw: str | None) -> set[int]:
    if not raw:
        return set()
    raw = raw.strip()
    if not raw:
        return set()

    try:
        if raw.startswith("["):
            parsed = json.loads(raw)
            return {int(item) for item in parsed}
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return {int(item) for item in values}
    except (ValueError, json.JSONDecodeError) as exc:
        raise ConfigError("ADMINS must be a JSON array or comma-separated numeric IDs") from exc


def _parse_int(raw: str | None, default: int | None = None) -> int | None:
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Expected integer but got: {raw}") from exc


def _resolve_database_path(database_uri: str | None) -> Path:
    uri = (database_uri or "sqlite:///./bot.db").strip()
    if not uri.startswith("sqlite:///"):
        raise ConfigError("Only sqlite:/// URIs are supported in this build")
    raw_path = uri.removeprefix("sqlite:///")
    if not raw_path:
        raise ConfigError("DATABASE_URI sqlite path cannot be empty")
    return Path(raw_path).expanduser().resolve()


def load_settings(env_files: Iterable[str | os.PathLike[str]] | None = None) -> Settings:
    if env_files:
        for env_file in env_files:
            load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ConfigError("BOT_TOKEN is required")

    bot_telegram_id = os.getenv("BOT_TELEGRAM_ID", "").strip().lstrip("@")
    if not bot_telegram_id:
        raise ConfigError("BOT_TELEGRAM_ID is required")

    admins = _parse_admins(os.getenv("ADMINS"))
    group_chat_id = _parse_int(os.getenv("GROUP_CHAT_ID"), default=None)

    github_developer_url = os.getenv("GITHUB_DEVELOPER_URL", "https://github.com/Mezdia").strip()
    github_project_url = os.getenv("GITHUB_PROJECT_URL", "https://github.com/Mezdia/YouTubeDownloaderBot").strip()

    database_path = _resolve_database_path(os.getenv("DATABASE_URI"))

    storage_path = Path(os.getenv("STORAGE_PATH", "./data/downloads")).expanduser().resolve()
    storage_path.mkdir(parents=True, exist_ok=True)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    max_daily_traffic_bytes = _parse_int(os.getenv("MAX_DAILY_TRAFFIC_BYTES"), default=500 * 1024 * 1024)
    max_concurrent_downloads = _parse_int(os.getenv("MAX_CONCURRENT_DOWNLOADS"), default=2)
    download_timeout_seconds = _parse_int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS"), default=1800)

    assert max_daily_traffic_bytes is not None
    assert max_concurrent_downloads is not None
    assert download_timeout_seconds is not None

    if max_daily_traffic_bytes <= 0:
        raise ConfigError("MAX_DAILY_TRAFFIC_BYTES must be positive")
    if max_concurrent_downloads <= 0:
        raise ConfigError("MAX_CONCURRENT_DOWNLOADS must be positive")
    if download_timeout_seconds <= 0:
        raise ConfigError("DOWNLOAD_TIMEOUT_SECONDS must be positive")

    ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg").strip() or "ffmpeg"
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    return Settings(
        bot_token=bot_token,
        bot_telegram_id=bot_telegram_id,
        admins=admins,
        group_chat_id=group_chat_id,
        github_developer_url=github_developer_url,
        github_project_url=github_project_url,
        database_path=database_path,
        storage_path=storage_path,
        max_daily_traffic_bytes=max_daily_traffic_bytes,
        max_concurrent_downloads=max_concurrent_downloads,
        download_timeout_seconds=download_timeout_seconds,
        ffmpeg_path=ffmpeg_path,
        log_level=log_level,
    )

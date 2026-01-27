from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FileHealth:
    ok: bool
    reason: str | None
    file_size_bytes: int
    duration_seconds: float | None = None


def validate_local_video_file(file_path: Path, ffmpeg_path: str, timeout_seconds: int = 30) -> FileHealth:
    resolved = file_path.resolve()
    if not resolved.exists():
        return FileHealth(ok=False, reason="file_missing", file_size_bytes=0, duration_seconds=None)

    file_size = resolved.stat().st_size
    if file_size <= 0:
        return FileHealth(ok=False, reason="file_is_empty", file_size_bytes=file_size, duration_seconds=None)

    ffprobe_path = _resolve_ffprobe_path(ffmpeg_path)
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration,size",
        "-of",
        "json",
        resolved.as_posix(),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except FileNotFoundError:
        # Fallback for environments that only provide ffmpeg binary.
        return FileHealth(ok=True, reason="ffprobe_missing_fallback", file_size_bytes=file_size, duration_seconds=None)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return FileHealth(ok=False, reason="ffprobe_failed", file_size_bytes=file_size, duration_seconds=None)

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return FileHealth(ok=False, reason="ffprobe_json_invalid", file_size_bytes=file_size, duration_seconds=None)

    fmt = payload.get("format") or {}
    duration_raw = fmt.get("duration")
    duration_seconds = None
    if duration_raw is not None:
        try:
            duration_seconds = float(duration_raw)
        except (TypeError, ValueError):
            duration_seconds = None

    if duration_seconds is not None and duration_seconds <= 0:
        return FileHealth(ok=False, reason="duration_invalid", file_size_bytes=file_size, duration_seconds=duration_seconds)

    return FileHealth(ok=True, reason=None, file_size_bytes=file_size, duration_seconds=duration_seconds)


def upload_size_looks_valid(local_size: int, telegram_size: int | None) -> bool:
    if local_size <= 0 or telegram_size is None or telegram_size <= 0:
        return False
    tolerance = max(2 * 1024 * 1024, int(local_size * 0.1))
    return abs(local_size - telegram_size) <= tolerance


def remove_file_and_empty_parents(file_path: Path, stop_at: Path) -> None:
    resolved_file = file_path.resolve()
    resolved_stop = stop_at.resolve()

    resolved_file.unlink(missing_ok=True)
    current = resolved_file.parent
    while current.exists() and current != resolved_stop:
        if any(current.iterdir()):
            break
        current.rmdir()
        current = current.parent


def _resolve_ffprobe_path(ffmpeg_path: str) -> str:
    ffmpeg_binary = Path(ffmpeg_path)
    if ffmpeg_binary.name.lower().startswith("ffmpeg"):
        candidate = ffmpeg_binary.with_name("ffprobe")
        if candidate.suffix:
            return candidate.as_posix()
        if ffmpeg_binary.suffix:
            return candidate.with_suffix(ffmpeg_binary.suffix).as_posix()
        return candidate.as_posix()
    return "ffprobe"

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


YOUTUBE_URL_RE = re.compile(
    r"(?P<url>https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]+|youtube\.com/shorts/[^\s/?]+|youtu\.be/[^\s/?]+))",
    re.IGNORECASE,
)


def extract_first_youtube_url(text: str | None) -> str | None:
    if not text:
        return None
    match = YOUTUBE_URL_RE.search(text)
    if not match:
        return None
    return match.group("url")


def extract_youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id or None

    if "youtube.com" in host:
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]
            return video_id
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]

    return None


def format_bytes(size: int | None) -> str:
    if size is None:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def trim_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def build_final_caption(title: str, description: str, bot_telegram_id: str) -> str:
    safe_title = trim_text(title or "Untitled", 180)
    safe_description = trim_text(description or "", 760)
    parts = [safe_title]
    if safe_description:
        parts.append(safe_description)
    parts.append(f"@{bot_telegram_id.lstrip('@')}")
    caption = "\n\n".join(parts)
    if len(caption) > 1024:
        allowed_description = max(0, 1024 - len(parts[0]) - len(parts[-1]) - 4)
        parts[1] = trim_text(safe_description, allowed_description)
        caption = "\n\n".join(parts)
    return caption


def build_progress_bar(percent: float) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int(round(percent / 20))
    return "▮" * max(1, filled)
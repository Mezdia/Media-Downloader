from __future__ import annotations

from datetime import UTC, datetime

from aiogram.exceptions import TelegramBadRequest

from ytdl_bot.logic import serve_cached_video
from ytdl_bot.models import CacheEntry


class FakeBot:
    def __init__(self, fail_copy: bool = False) -> None:
        self.fail_copy = fail_copy
        self.copy_calls: list[tuple[int, int, int]] = []
        self.send_video_calls: list[tuple[int, str, str]] = []

    async def copy_message(self, chat_id: int, from_chat_id: int, message_id: int):
        self.copy_calls.append((chat_id, from_chat_id, message_id))
        if self.fail_copy:
            raise TelegramBadRequest(method="copyMessage", message="copy failed")
        return {"ok": True, "method": "copy"}

    async def send_video(self, chat_id: int, video: str, caption: str, supports_streaming: bool = True):
        self.send_video_calls.append((chat_id, video, caption))
        return {"ok": True, "method": "send_video"}


async def test_cache_hit_serves_by_copy_message() -> None:
    bot = FakeBot()
    cache = CacheEntry(
        youtube_id="abc123",
        quality=720,
        group_chat_id=-1001,
        group_message_id=77,
        file_id="file_1",
        filesize_bytes=100,
        uploaded_at=datetime.now(UTC),
        uploader_id=1,
    )

    result = await serve_cached_video(bot, cache, chat_id=999, caption="cap")

    assert result["method"] == "copy"
    assert bot.copy_calls == [(999, -1001, 77)]
    assert bot.send_video_calls == []


async def test_cache_hit_falls_back_to_file_id_send() -> None:
    bot = FakeBot(fail_copy=True)
    cache = CacheEntry(
        youtube_id="abc123",
        quality=720,
        group_chat_id=-1001,
        group_message_id=77,
        file_id="file_1",
        filesize_bytes=100,
        uploaded_at=datetime.now(UTC),
        uploader_id=1,
    )

    result = await serve_cached_video(bot, cache, chat_id=999, caption="cap")

    assert result["method"] == "send_video"
    assert bot.copy_calls == [(999, -1001, 77)]
    assert bot.send_video_calls == [(999, "file_1", "cap")]
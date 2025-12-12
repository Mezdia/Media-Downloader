from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest

from .models import CacheEntry


def quota_allows(used_bytes: int, limit_bytes: int, required_bytes: int, is_admin: bool) -> bool:
    if is_admin:
        return True
    if required_bytes < 0:
        return False
    return used_bytes + required_bytes <= limit_bytes


def quota_remaining(used_bytes: int, limit_bytes: int) -> int:
    return max(0, limit_bytes - used_bytes)


async def serve_cached_video(bot, cache_entry: CacheEntry, chat_id: int, caption: str):
    try:
        return await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=cache_entry.group_chat_id,
            message_id=cache_entry.group_message_id,
        )
    except TelegramBadRequest:
        return await bot.send_video(
            chat_id=chat_id,
            video=cache_entry.file_id,
            caption=caption,
            supports_streaming=True,
        )
from __future__ import annotations

import asyncio
import random
from typing import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

try:
    from aiogram.types import ReactionTypeEmoji
except Exception:  # pragma: no cover - fallback for older aiogram builds
    ReactionTypeEmoji = None  # type: ignore


async def apply_random_reaction(bot: Bot, message: Message) -> str:
    emoji = random.choice(["👀", "🤖"])

    if ReactionTypeEmoji is not None and hasattr(bot, "set_message_reaction"):
        try:
            await bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
                is_big=False,
            )
            return emoji
        except Exception:
            pass

    fallback = await message.reply(emoji)
    asyncio.create_task(_delete_later(bot, message.chat.id, fallback.message_id, delay=5))
    return emoji


async def send_processing_messages(message: Message, processing_text: str) -> tuple[Message, Message]:
    ghost = await message.reply("👾")
    processing = await message.reply(processing_text)
    return ghost, processing


async def safe_delete_messages(bot: Bot, chat_id: int, message_ids: Iterable[int]) -> None:
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            continue


async def _delete_later(bot: Bot, chat_id: int, message_id: int, delay: float) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass
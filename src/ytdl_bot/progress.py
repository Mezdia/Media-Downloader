from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from .i18n import I18n
from .utils import build_progress_bar, format_bytes


@dataclass(slots=True)
class JobLogContext:
    user_id: int
    username: str | None
    youtube_id: str
    title: str
    quality: int


class AdminLogger:
    def __init__(self, bot: Bot, admin_ids_provider) -> None:
        self._bot = bot
        self._admin_ids_provider = admin_ids_provider

    async def notify(self, text: str) -> None:
        admin_ids = await self._admin_ids_provider()
        for admin_id in admin_ids:
            try:
                await self._bot.send_message(admin_id, text)
            except TelegramBadRequest:
                continue

    async def stage(
        self,
        stage: str,
        context: JobLogContext,
        progress: float | None = None,
        eta: str | None = None,
        size_bytes: int | None = None,
        cache_message_id: int | None = None,
        cache_uploaded_at: str | None = None,
        error: str | None = None,
    ) -> None:
        timestamp = datetime.now(UTC).isoformat()
        username = f"@{context.username}" if context.username else "-"
        fields = [
            f"[{timestamp}] {stage}",
            f"user: {context.user_id} ({username})",
            f"video: {context.youtube_id}",
            f"title: {context.title}",
            f"quality: {context.quality}p",
        ]
        if progress is not None:
            fields.append(f"progress: {progress:.1f}%")
        if eta:
            fields.append(f"ETA: {eta}")
        if size_bytes is not None:
            fields.append(f"size: {format_bytes(size_bytes)}")
        if cache_message_id is not None:
            fields.append(f"SERVED_FROM_CACHE — group_message_id: {cache_message_id}")
        if cache_uploaded_at:
            fields.append(f"cache_uploaded_at: {cache_uploaded_at}")
        if error:
            fields.append(f"error: {error}")

        await self.notify(", ".join(fields))


class ProgressSession:
    def __init__(
        self,
        bot: Bot,
        i18n: I18n,
        admin_logger: AdminLogger,
        admin_ids: Iterable[int],
        user_chat_id: int,
        user_lang: str,
        context: JobLogContext,
    ) -> None:
        self.bot = bot
        self.i18n = i18n
        self.admin_logger = admin_logger
        self.admin_ids = list(admin_ids)
        self.user_chat_id = user_chat_id
        self.user_lang = user_lang
        self.context = context
        self.user_status_message_id: int | None = None
        self.admin_status_message_ids: dict[int, int] = {}
        self._last_percent: float = -1.0

    async def start(self) -> None:
        text = self._user_text("queued", 0.0)
        msg = await self.bot.send_message(self.user_chat_id, text)
        self.user_status_message_id = msg.message_id

        for admin_id in self.admin_ids:
            try:
                admin_msg = await self.bot.send_message(admin_id, self._admin_text("queued", 0.0))
                self.admin_status_message_ids[admin_id] = admin_msg.message_id
            except TelegramBadRequest:
                continue

        await self.admin_logger.stage("Queued", self.context, progress=0.0)

    async def update(
        self,
        stage_key: str,
        percent: float,
        eta: str | None = None,
        force: bool = False,
    ) -> None:
        if not force and abs(percent - self._last_percent) < 1.0 and stage_key == "downloading":
            return

        self._last_percent = percent
        user_text = self._user_text(stage_key, percent, eta=eta)
        admin_text = self._admin_text(stage_key, percent, eta=eta)

        if self.user_status_message_id is not None:
            try:
                await self.bot.edit_message_text(user_text, self.user_chat_id, self.user_status_message_id)
            except TelegramBadRequest:
                pass

        for admin_id, message_id in self.admin_status_message_ids.items():
            try:
                await self.bot.edit_message_text(admin_text, admin_id, message_id)
            except TelegramBadRequest:
                continue

    async def finish(self) -> None:
        if self.user_status_message_id is None:
            return
        try:
            await self.bot.delete_message(self.user_chat_id, self.user_status_message_id)
        except TelegramBadRequest:
            pass

    async def stage_log(
        self,
        stage: str,
        progress: float | None = None,
        eta: str | None = None,
        size_bytes: int | None = None,
        cache_message_id: int | None = None,
        cache_uploaded_at: str | None = None,
        error: str | None = None,
    ) -> None:
        await self.admin_logger.stage(
            stage=stage,
            context=self.context,
            progress=progress,
            eta=eta,
            size_bytes=size_bytes,
            cache_message_id=cache_message_id,
            cache_uploaded_at=cache_uploaded_at,
            error=error,
        )

    def _user_text(self, stage_key: str, percent: float, eta: str | None = None) -> str:
        stage_localized = self.i18n.t(self.user_lang, f"status_{stage_key}")
        if stage_key in {"finished", "done"}:
            return stage_localized
        bar = build_progress_bar(percent)
        if eta:
            return f"{stage_localized} — {percent:.0f}% {bar}\nETA: {eta}"
        return f"{stage_localized} — {percent:.0f}% {bar}"

    def _admin_text(self, stage_key: str, percent: float, eta: str | None = None) -> str:
        timestamp = datetime.now(UTC).isoformat()
        base = (
            f"[{timestamp}] {stage_key.upper()} | user={self.context.user_id}"
            f" | video={self.context.youtube_id} | quality={self.context.quality}p"
        )
        if stage_key in {"finished", "done"}:
            return base
        if eta:
            return f"{base} | progress={percent:.1f}% | ETA={eta}"
        return f"{base} | progress={percent:.1f}%"
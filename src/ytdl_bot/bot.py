from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from .keyboards import (
    about_keyboard,
    active_jobs_keyboard,
    admin_panel_keyboard,
    language_keyboard,
    main_menu_keyboard,
    quality_keyboard,
)
from .models import PendingRequest
from .progress import AdminLogger, JobLogContext, ProgressSession
from .state import AppState, TaskInfo, utcnow
from .utils import build_final_caption, extract_first_youtube_url, format_bytes, trim_text
from .ux import apply_random_reaction, safe_delete_messages, send_processing_messages
from .youtube import YoutubeServiceError
from .logic import serve_cached_video
from .media import remove_file_and_empty_parents, upload_size_looks_valid, validate_local_video_file


def build_dispatcher(app_state: AppState) -> Dispatcher:
    router = Router()
    dp = Dispatcher()
    dp.include_router(router)

    async def _lang_for(user_id: int) -> str:
        language = await app_state.db.get_user_language(user_id)
        return app_state.i18n.language(language)

    async def _is_admin(user_id: int) -> bool:
        return await app_state.is_admin(user_id)

    async def _ensure_user(message: Message) -> str:
        assert message.from_user is not None
        await app_state.db.upsert_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
        )
        return await _lang_for(message.from_user.id)

    async def _effective_group_chat_id() -> int | None:
        value = await app_state.db.get_setting("group_chat_id")
        if value is not None and value.strip() != "":
            try:
                return int(value)
            except ValueError:
                return None
        return app_state.settings.group_chat_id

    async def _cache_enabled() -> bool:
        value = await app_state.db.get_setting("cache_enabled")
        if value is None:
            return (await _effective_group_chat_id()) is not None
        return value == "1"

    async def _set_cache_enabled(enabled: bool) -> None:
        await app_state.db.set_setting("cache_enabled", "1" if enabled else "0")

    async def _send_main_menu(message: Message, lang: str, is_admin: bool) -> None:
        await message.answer(
            app_state.i18n.t(lang, "main_menu_prompt"),
            reply_markup=main_menu_keyboard(app_state.i18n, lang, is_admin),
        )

    async def _send_about(message: Message, lang: str) -> None:
        about_text = "\n\n".join(
            [
                app_state.i18n.t(lang, "about_title"),
                app_state.i18n.t(lang, "about_designed_en"),
                app_state.i18n.t(lang, "about_designed_fa"),
                app_state.i18n.t(lang, "about_body"),
            ]
        )
        await message.answer(
            about_text,
            reply_markup=about_keyboard(
                app_state.i18n,
                lang,
                app_state.settings.github_developer_url,
                app_state.settings.github_project_url,
            ),
        )

    async def _send_about_callback(callback: CallbackQuery, lang: str) -> None:
        if callback.message is None:
            return
        about_text = "\n\n".join(
            [
                app_state.i18n.t(lang, "about_title"),
                app_state.i18n.t(lang, "about_designed_en"),
                app_state.i18n.t(lang, "about_designed_fa"),
                app_state.i18n.t(lang, "about_body"),
            ]
        )
        await callback.message.answer(
            about_text,
            reply_markup=about_keyboard(
                app_state.i18n,
                lang,
                app_state.settings.github_developer_url,
                app_state.settings.github_project_url,
            ),
        )

    def _duration_text(duration_seconds: int | None, lang: str) -> str:
        if duration_seconds is None:
            return app_state.i18n.t(lang, "duration_unknown")
        minutes, seconds = divmod(duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    async def _quota_remaining(user_id: int) -> tuple[int, int]:
        used = await app_state.db.get_usage_bytes(user_id, app_state.settings.rolling_window_seconds)
        remaining = max(0, app_state.settings.max_daily_traffic_bytes - used)
        return used, remaining

    async def _admin_guard(message: Message) -> tuple[bool, str]:
        assert message.from_user is not None
        lang = await _lang_for(message.from_user.id)
        if not await _is_admin(message.from_user.id):
            await message.answer(app_state.i18n.t(lang, "admin_not_allowed"))
            return False, lang
        return True, lang

    @router.message(CommandStart())
    async def on_start(message: Message) -> None:
        lang = await _ensure_user(message)
        await message.answer(
            app_state.i18n.t(lang, "language_prompt"),
            reply_markup=language_keyboard(app_state.i18n),
        )

    @router.callback_query(F.data.startswith("lang:"))
    async def on_language_selected(callback: CallbackQuery) -> None:
        assert callback.data is not None
        assert callback.from_user is not None

        _, language = callback.data.split(":", maxsplit=1)
        language = app_state.i18n.language(language)

        await app_state.db.set_user_language(callback.from_user.id, language)
        await app_state.db.upsert_user(callback.from_user.id, callback.from_user.username, language)

        is_admin = await _is_admin(callback.from_user.id)
        text = "\n".join(
            [
                app_state.i18n.t(language, "language_saved"),
                app_state.i18n.t(language, "welcome_message"),
            ]
        )

        if callback.message:
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_keyboard(app_state.i18n, language, is_admin),
            )
        await callback.answer()

    @router.callback_query(F.data == "menu:language")
    async def on_menu_language(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if callback.message:
            await callback.message.answer(
                app_state.i18n.t(lang, "language_prompt"),
                reply_markup=language_keyboard(app_state.i18n),
            )
        await callback.answer()

    @router.callback_query(F.data == "menu:about")
    async def on_menu_about(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        await _send_about_callback(callback, lang)
        await callback.answer()

    @router.message(Command("about"))
    async def on_about_command(message: Message) -> None:
        lang = await _ensure_user(message)
        await _send_about(message, lang)

    @router.callback_query(F.data == "admin:panel")
    async def on_admin_panel(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return
        if callback.message:
            await callback.message.answer(
                app_state.i18n.t(lang, "admin_panel_title"),
                reply_markup=admin_panel_keyboard(app_state.i18n, lang),
            )
        await callback.answer()

    @router.callback_query(F.data == "admin:active")
    async def on_admin_active(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return

        jobs = await app_state.db.list_active_jobs()
        if callback.message:
            if not jobs:
                await callback.message.answer(app_state.i18n.t(lang, "admin_no_active_jobs"))
            else:
                lines = [app_state.i18n.t(lang, "admin_active_downloads") + ":"]
                for job in jobs[:20]:
                    lines.append(f"{job.job_id} | user={job.user_id} | {job.youtube_id} | {job.quality}p")
                await callback.message.answer(
                    "\n".join(lines),
                    reply_markup=active_jobs_keyboard(app_state.i18n, lang, jobs),
                )
        await callback.answer()
    @router.callback_query(F.data.startswith("admin:cancel:"))
    async def on_admin_cancel_job(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return

        job_id = (callback.data or "").split(":", maxsplit=2)[2]
        cancelled = await app_state.cancel_task(job_id)
        if callback.message:
            if cancelled:
                await callback.message.answer(app_state.i18n.t(lang, "admin_job_cancelled", job_id=job_id))
            else:
                await callback.message.answer(app_state.i18n.t(lang, "admin_no_active_jobs"))
        await callback.answer()

    @router.callback_query(F.data == "admin:usage_help")
    async def on_admin_usage_help(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return
        if callback.message:
            await callback.message.answer(app_state.i18n.t(lang, "admin_help_usage"))
        await callback.answer()

    @router.callback_query(F.data == "admin:cache_help")
    async def on_admin_cache_help(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return
        if callback.message:
            await callback.message.answer(app_state.i18n.t(lang, "admin_help_cache"))
        await callback.answer()

    @router.callback_query(F.data == "admin:group_help")
    async def on_admin_group_help(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return
        if callback.message:
            await callback.message.answer(app_state.i18n.t(lang, "admin_help_group"))
        await callback.answer()

    @router.callback_query(F.data == "admin:force_help")
    async def on_admin_force_help(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return
        if callback.message:
            await callback.message.answer(app_state.i18n.t(lang, "admin_help_force"))
        await callback.answer()

    @router.callback_query(F.data == "admin:admins_help")
    async def on_admin_admins_help(callback: CallbackQuery) -> None:
        assert callback.from_user is not None
        lang = await _lang_for(callback.from_user.id)
        if not await _is_admin(callback.from_user.id):
            await callback.answer(app_state.i18n.t(lang, "admin_not_allowed"), show_alert=True)
            return
        if callback.message:
            await callback.message.answer(app_state.i18n.t(lang, "admin_help_admins"))
        await callback.answer()

    @router.message(Command("menu"))
    async def on_menu_command(message: Message) -> None:
        assert message.from_user is not None
        lang = await _ensure_user(message)
        await _send_main_menu(message, lang, await _is_admin(message.from_user.id))

    @router.message(Command("admin_usage"))
    async def on_admin_usage(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        user_id = int(parts[1])
        used, remaining = await _quota_remaining(user_id)
        await message.answer(
            app_state.i18n.t(
                lang,
                "usage_report",
                user_id=user_id,
                used=format_bytes(used),
                limit=format_bytes(app_state.settings.max_daily_traffic_bytes),
                remaining=format_bytes(remaining),
            )
        )

    @router.message(Command("admin_reset_usage"))
    async def on_admin_reset_usage(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        user_id = int(parts[1])
        await app_state.db.reset_usage(user_id)
        await message.answer(app_state.i18n.t(lang, "usage_reset_done", user_id=user_id))

    @router.message(Command("admin_set_group"))
    async def on_admin_set_group(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        group_chat_id = int(parts[1])
        await app_state.db.set_setting("group_chat_id", str(group_chat_id))
        await _set_cache_enabled(True)
        await message.answer(app_state.i18n.t(lang, "group_set_done", group_chat_id=group_chat_id))

    @router.message(Command("admin_clear_group"))
    async def on_admin_clear_group(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        await app_state.db.set_setting("group_chat_id", "")
        await _set_cache_enabled(False)
        await message.answer(app_state.i18n.t(lang, "group_cleared"))

    @router.message(Command("admin_cache_add"))
    async def on_admin_cache_add(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) not in {6, 7}:
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        youtube_id = parts[1]
        if not parts[2].isdigit() or not parts[3].lstrip("-").isdigit() or not parts[5].isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        quality = int(parts[2])
        group_message_id = int(parts[3])
        file_id = parts[4]
        filesize = int(parts[5])

        group_chat_id = await _effective_group_chat_id()
        if len(parts) == 7 and parts[6].lstrip("-").isdigit():
            group_chat_id = int(parts[6])

        if group_chat_id is None:
            await message.answer(app_state.i18n.t(lang, "admin_group_missing"))
            return

        assert message.from_user is not None
        await app_state.db.upsert_cache(
            youtube_id=youtube_id,
            quality=quality,
            group_chat_id=group_chat_id,
            group_message_id=group_message_id,
            file_id=file_id,
            filesize_bytes=filesize,
            uploader_id=message.from_user.id,
        )
        await message.answer(app_state.i18n.t(lang, "cache_added", youtube_id=youtube_id, quality=quality))

    @router.message(Command("admin_cache_remove"))
    async def on_admin_cache_remove(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 3 or not parts[2].isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        youtube_id = parts[1]
        quality = int(parts[2])
        existing = await app_state.db.get_cache(youtube_id, quality)
        if existing is None:
            await message.answer(app_state.i18n.t(lang, "cache_not_found", youtube_id=youtube_id, quality=quality))
            return

        await app_state.db.delete_cache(youtube_id, quality)
        await message.answer(app_state.i18n.t(lang, "cache_removed", youtube_id=youtube_id, quality=quality))
    @router.message(Command("admin_force_copy"))
    async def on_admin_force_copy(message: Message, bot: Bot) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 4 or not parts[2].isdigit() or not parts[3].lstrip("-").isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        youtube_id = parts[1]
        quality = int(parts[2])
        chat_id = int(parts[3])
        entry = await app_state.db.get_cache(youtube_id, quality)
        if entry is None:
            await message.answer(app_state.i18n.t(lang, "cache_not_found", youtube_id=youtube_id, quality=quality))
            return

        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=entry.group_chat_id, message_id=entry.group_message_id)
            await message.answer(app_state.i18n.t(lang, "force_copy_done", chat_id=chat_id))
        except TelegramBadRequest:
            await message.answer(app_state.i18n.t(lang, "force_copy_failed"))

    @router.message(Command("admin_add"))
    async def on_admin_add(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        user_id = int(parts[1])
        await app_state.db.add_admin(user_id)
        await message.answer(app_state.i18n.t(lang, "admin_added", user_id=user_id))

    @router.message(Command("admin_remove"))
    async def on_admin_remove(message: Message) -> None:
        ok, lang = await _admin_guard(message)
        if not ok:
            return

        parts = (message.text or "").split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer(app_state.i18n.t(lang, "command_bad_args"))
            return

        user_id = int(parts[1])
        await app_state.db.remove_admin(user_id)
        await message.answer(app_state.i18n.t(lang, "admin_removed", user_id=user_id))

    @router.callback_query(F.data.startswith("q:"))
    async def on_quality_selected(callback: CallbackQuery, bot: Bot) -> None:
        if callback.data is None or callback.from_user is None:
            return

        lang = await _lang_for(callback.from_user.id)
        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer(app_state.i18n.t(lang, "quality_obsolete"), show_alert=True)
            return

        _, request_id_raw, quality_raw, owner_id_raw = parts
        if not request_id_raw.isdigit() or not quality_raw.isdigit() or not owner_id_raw.isdigit():
            await callback.answer(app_state.i18n.t(lang, "quality_obsolete"), show_alert=True)
            return

        request_id = int(request_id_raw)
        quality = int(quality_raw)
        owner_id = int(owner_id_raw)
        is_admin = await _is_admin(callback.from_user.id)

        if callback.from_user.id != owner_id and not is_admin:
            await callback.answer(app_state.i18n.t(lang, "only_owner_can_use"), show_alert=True)
            return

        request = await app_state.db.get_pending_request(request_id)
        if request is None:
            await callback.answer(app_state.i18n.t(lang, "stale_request"), show_alert=True)
            return

        if quality not in request.quality_sizes:
            await callback.answer(app_state.i18n.t(lang, "quality_unavailable"), show_alert=True)
            await _refresh_quality_options(callback, request, lang)
            return

        await app_state.db.delete_pending_request(request_id)

        job_id = uuid.uuid4().hex[:12]
        task = asyncio.create_task(
            _process_quality_selection(
                bot=bot,
                request=request,
                selected_quality=quality,
                actor_user_id=callback.from_user.id,
                actor_username=callback.from_user.username,
                lang=lang,
                job_id=job_id,
            ),
            name=f"download-{job_id}",
        )
        await app_state.register_task(
            TaskInfo(
                job_id=job_id,
                user_id=request.user_id,
                chat_id=request.chat_id,
                youtube_id=request.youtube_id,
                quality=quality,
                title=request.title,
                started_at=utcnow(),
                task=task,
            )
        )
        await callback.answer(app_state.i18n.t(lang, "download_started"))

    @router.message(F.text)
    async def on_text_message(message: Message, bot: Bot) -> None:
        assert message.from_user is not None
        await _ensure_user(message)
        url = extract_first_youtube_url(message.text)
        if not url:
            return

        lang = await _lang_for(message.from_user.id)
        if not (await app_state.db.get_user_language(message.from_user.id)):
            await message.answer(app_state.i18n.t(lang, "send_language_first"))
            return

        await apply_random_reaction(bot, message)
        ghost_msg, processing_msg = await send_processing_messages(message, app_state.i18n.t(lang, "processing_text"))

        try:
            probe = await app_state.youtube.probe(url)
        except YoutubeServiceError as exc:
            await safe_delete_messages(bot, message.chat.id, [ghost_msg.message_id, processing_msg.message_id])
            await message.answer(app_state.i18n.t(lang, "error_download_failed"))
            await app_state.admin_logger.notify(
                f"[{datetime.now(UTC).isoformat()}] Probe error user={message.from_user.id} url={url} error={exc}"
            )
            return

        if not probe.qualities:
            await safe_delete_messages(bot, message.chat.id, [ghost_msg.message_id, processing_msg.message_id])
            await message.answer(app_state.i18n.t(lang, "no_supported_quality"))
            return

        quality_sizes = {quality: option.filesize_bytes for quality, option in probe.qualities.items()}
        pending_id = await app_state.db.create_pending_request(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            youtube_id=probe.youtube_id,
            url=url,
            title=probe.title,
            description=probe.description,
            thumbnail_url=probe.thumbnail_url,
            quality_sizes=quality_sizes,
        )

        duration_text = _duration_text(probe.duration_seconds, lang)
        caption = "\n\n".join(
            [
                app_state.i18n.t(lang, "choose_quality_for", title=trim_text(probe.title, 120)),
                app_state.i18n.t(
                    lang,
                    "video_info_line",
                    video_id=probe.youtube_id,
                    duration=duration_text,
                    count=len(probe.qualities),
                ),
            ]
        )
        quality_markup = quality_keyboard(pending_id, message.from_user.id, quality_sizes)

        if probe.thumbnail_url:
            try:
                await message.answer_photo(photo=probe.thumbnail_url, caption=caption, reply_markup=quality_markup)
            except TelegramBadRequest:
                await message.answer(caption, reply_markup=quality_markup)
        else:
            await message.answer(caption, reply_markup=quality_markup)

        await safe_delete_messages(bot, message.chat.id, [ghost_msg.message_id, processing_msg.message_id])
    async def _refresh_quality_options(callback: CallbackQuery, request: PendingRequest, lang: str) -> None:
        if callback.message is None:
            return
        try:
            probe = await app_state.youtube.probe(request.url)
        except YoutubeServiceError:
            return

        if not probe.qualities:
            await callback.message.answer(app_state.i18n.t(lang, "no_supported_quality"))
            return

        quality_sizes = {quality: option.filesize_bytes for quality, option in probe.qualities.items()}
        new_request_id = await app_state.db.create_pending_request(
            user_id=request.user_id,
            chat_id=request.chat_id,
            message_id=request.message_id,
            youtube_id=probe.youtube_id,
            url=request.url,
            title=probe.title,
            description=probe.description,
            thumbnail_url=probe.thumbnail_url,
            quality_sizes=quality_sizes,
        )

        await callback.message.answer(
            app_state.i18n.t(lang, "choose_quality_for", title=trim_text(probe.title, 120)),
            reply_markup=quality_keyboard(new_request_id, request.user_id, quality_sizes),
        )

    async def _process_quality_selection(
        bot: Bot,
        request: PendingRequest,
        selected_quality: int,
        actor_user_id: int,
        actor_username: str | None,
        lang: str,
        job_id: str,
    ) -> None:
        probe_file_path: Path | None = None
        context = JobLogContext(
            user_id=request.user_id,
            username=actor_username,
            youtube_id=request.youtube_id,
            title=trim_text(request.title, 80),
            quality=selected_quality,
        )

        admin_ids = await app_state.get_admin_ids()
        progress = ProgressSession(
            bot=bot,
            i18n=app_state.i18n,
            admin_logger=app_state.admin_logger,
            admin_ids=admin_ids,
            user_chat_id=request.chat_id,
            user_lang=lang,
            context=context,
        )

        await app_state.db.create_job(
            job_id=job_id,
            user_id=request.user_id,
            chat_id=request.chat_id,
            youtube_id=request.youtube_id,
            title=request.title,
            quality=selected_quality,
            status="queued",
        )

        try:
            await progress.start()
            await app_state.db.update_job(job_id, status="queued", progress=0)

            is_admin_user = await _is_admin(request.user_id)
            _, remaining = await _quota_remaining(request.user_id)

            cache_entry = await app_state.db.get_cache(request.youtube_id, selected_quality)
            if cache_entry:
                if not is_admin_user and cache_entry.filesize_bytes > remaining:
                    await bot.send_message(
                        request.chat_id,
                        "\n".join(
                            [
                                app_state.i18n.t(
                                    lang,
                                    "quota_exceeded",
                                    required=format_bytes(cache_entry.filesize_bytes),
                                    remaining=format_bytes(remaining),
                                ),
                                app_state.i18n.t(lang, "quota_tip"),
                            ]
                        ),
                    )
                    await progress.stage_log(
                        "Error",
                        error=f"quota exceeded for cached file size={cache_entry.filesize_bytes}",
                    )
                    await progress.finish()
                    return

                await progress.update("cache_copying", 15.0, force=True)
                await progress.stage_log(
                    "SERVED_FROM_CACHE",
                    progress=100.0,
                    size_bytes=cache_entry.filesize_bytes,
                    cache_message_id=cache_entry.group_message_id,
                    cache_uploaded_at=cache_entry.uploaded_at.isoformat(),
                )

                caption = build_final_caption(
                    request.title,
                    request.description,
                    app_state.settings.bot_telegram_id,
                )
                copied_message = await serve_cached_video(
                    bot=bot,
                    cache_entry=cache_entry,
                    chat_id=request.chat_id,
                    caption=caption,
                )

                if copied_message and not is_admin_user:
                    await app_state.db.add_usage_event(request.user_id, cache_entry.filesize_bytes)

                await progress.update("done", 100.0, force=True)
                await progress.stage_log("Done", progress=100.0, size_bytes=cache_entry.filesize_bytes)
                await progress.finish()
                await app_state.db.update_job(job_id, status="done", progress=100)
                return

            estimated_size = request.quality_sizes.get(selected_quality)
            if not is_admin_user and estimated_size is not None and estimated_size > remaining:
                await bot.send_message(
                    request.chat_id,
                    "\n".join(
                        [
                            app_state.i18n.t(
                                lang,
                                "quota_exceeded",
                                required=format_bytes(estimated_size),
                                remaining=format_bytes(remaining),
                            ),
                            app_state.i18n.t(lang, "quota_tip"),
                        ]
                    ),
                )
                await progress.stage_log("Error", error="quota exceeded on pre-check")
                await progress.finish()
                return

            await app_state.db.update_job(job_id, status="downloading", progress=0)
            await progress.update("downloading", 1.0, force=True)
            await progress.stage_log("Downloading", progress=1.0)

            async with app_state.download_semaphore:
                probe = await app_state.youtube.probe(request.url)
                option = probe.qualities.get(selected_quality)
                if option is None:
                    await bot.send_message(request.chat_id, app_state.i18n.t(lang, "quality_unavailable"))
                    await progress.stage_log("Error", error="selected quality missing after re-probe")
                    await progress.finish()
                    return

                if option.requires_merge:
                    await progress.update("merging", 10.0, force=True)
                    await progress.stage_log("Merging", progress=10.0)
                    await progress.update("downloading", 12.0, force=True)

                loop = asyncio.get_running_loop()

                async def on_progress(percent: float, eta: str | None) -> None:
                    await app_state.db.update_job(job_id, status="downloading", progress=percent)
                    await progress.update("downloading", percent, eta=eta)

                def hook(percent: float, eta: str | None) -> None:
                    asyncio.run_coroutine_threadsafe(on_progress(percent, eta), loop)

                download_result = await app_state.youtube.download(
                    probe=probe,
                    quality_option=option,
                    progress_callback=hook,
                )
                probe_file_path = download_result.file_path

            file_health = await asyncio.to_thread(
                validate_local_video_file,
                download_result.file_path,
                app_state.settings.ffmpeg_path,
            )
            if not file_health.ok:
                await bot.send_message(request.chat_id, app_state.i18n.t(lang, "error_file_invalid"))
                await progress.stage_log("Error", error=f"integrity_check_failed:{file_health.reason}")
                await app_state.admin_logger.notify(
                    f"[{datetime.now(UTC).isoformat()}] Integrity check failed user={request.user_id} "
                    f"video={request.youtube_id} quality={selected_quality}p reason={file_health.reason}"
                )
                await progress.finish()
                return

            await progress.stage_log(
                "Integrity check passed",
                size_bytes=file_health.file_size_bytes,
            )
            if not is_admin_user:
                _, remaining = await _quota_remaining(request.user_id)
                if download_result.file_size_bytes > remaining:
                    await bot.send_message(
                        request.chat_id,
                        "\n".join(
                            [
                                app_state.i18n.t(
                                    lang,
                                    "quota_exceeded",
                                    required=format_bytes(download_result.file_size_bytes),
                                    remaining=format_bytes(remaining),
                                ),
                                app_state.i18n.t(lang, "quota_tip"),
                            ]
                        ),
                    )
                    await progress.stage_log("Error", error="quota exceeded after final size check")
                    await progress.finish()
                    return

            await progress.update("finished", 100.0, force=True)
            await progress.stage_log(
                "Download finished",
                progress=100.0,
                size_bytes=download_result.file_size_bytes,
            )

            await app_state.db.update_job(job_id, status="uploading", progress=0)
            await progress.update("uploading", 10.0, force=True)
            await progress.stage_log("Uploading", progress=10.0)

            caption = build_final_caption(
                download_result.title,
                download_result.description,
                app_state.settings.bot_telegram_id,
            )

            user_video_message = await bot.send_video(
                chat_id=request.chat_id,
                video=FSInputFile(download_result.file_path.as_posix()),
                caption=caption,
                supports_streaming=True,
            )
            await progress.update("uploading", 100.0, force=True)

            user_remote_size = user_video_message.video.file_size if user_video_message.video else None
            if not upload_size_looks_valid(download_result.file_size_bytes, user_remote_size):
                await app_state.admin_logger.notify(
                    f"[{datetime.now(UTC).isoformat()}] Upload verification warning "
                    f"user={request.user_id} video={request.youtube_id} quality={selected_quality}p "
                    f"local_size={download_result.file_size_bytes} telegram_size={user_remote_size}"
                )

            if not is_admin_user:
                await app_state.db.add_usage_event(request.user_id, download_result.file_size_bytes)

            group_chat_id = await _effective_group_chat_id()
            cache_is_enabled = await _cache_enabled()
            if group_chat_id is None:
                cache_is_enabled = False

            if cache_is_enabled and group_chat_id is not None:
                if user_video_message.video:
                    try:
                        group_message = await bot.send_video(
                            chat_id=group_chat_id,
                            video=user_video_message.video.file_id,
                            caption=caption,
                            supports_streaming=True,
                        )
                        group_remote_size = group_message.video.file_size if group_message.video else None
                        if group_message.video and upload_size_looks_valid(download_result.file_size_bytes, group_remote_size):
                            await app_state.db.upsert_cache(
                                youtube_id=request.youtube_id,
                                quality=selected_quality,
                                group_chat_id=group_chat_id,
                                group_message_id=group_message.message_id,
                                file_id=group_message.video.file_id,
                                filesize_bytes=download_result.file_size_bytes,
                                uploader_id=request.user_id,
                            )
                        else:
                            await app_state.admin_logger.notify(
                                f"[{datetime.now(UTC).isoformat()}] Cache upload verification failed "
                                f"video={request.youtube_id} quality={selected_quality}p "
                                f"local_size={download_result.file_size_bytes} telegram_size={group_remote_size}"
                            )
                    except TelegramBadRequest as exc:
                        await _set_cache_enabled(False)
                        await app_state.admin_logger.notify(
                            f"[{datetime.now(UTC).isoformat()}] {app_state.i18n.t(lang, 'admin_cache_upload_failed')} error={exc}"
                        )
                else:
                    await app_state.admin_logger.notify(
                        f"[{datetime.now(UTC).isoformat()}] Cache skipped: user message video payload missing "
                        f"video={request.youtube_id} quality={selected_quality}p"
                    )
            else:
                await app_state.admin_logger.notify(
                    f"[{datetime.now(UTC).isoformat()}] {app_state.i18n.t(lang, 'cache_disabled_notice')}"
                )

            try:
                await asyncio.to_thread(
                    remove_file_and_empty_parents,
                    download_result.file_path,
                    app_state.settings.storage_path,
                )
                probe_file_path = None
            except Exception as exc:
                await app_state.admin_logger.notify(
                    f"[{datetime.now(UTC).isoformat()}] file_cleanup_failed path={download_result.file_path} error={exc}"
                )

            await progress.stage_log(
                "Done",
                progress=100.0,
                size_bytes=download_result.file_size_bytes,
            )
            await progress.update("done", 100.0, force=True)
            await progress.finish()
            await app_state.db.update_job(job_id, status="done", progress=100)

            if user_video_message.video:
                await app_state.admin_logger.notify(
                    f"[{datetime.now(UTC).isoformat()}] Completed user={request.user_id} video={request.youtube_id} quality={selected_quality}p file_id={user_video_message.video.file_id} msg_id={user_video_message.message_id}"
                )

        except asyncio.CancelledError:
            await app_state.db.update_job(job_id, status="error", progress=0, error="cancelled")
            await bot.send_message(request.chat_id, app_state.i18n.t(lang, "cancelled_by_admin"))
            await progress.stage_log("Error", error="cancelled by admin")
            await progress.finish()
            raise
        except YoutubeServiceError as exc:
            await app_state.db.update_job(job_id, status="error", progress=0, error=str(exc))
            user_message = (
                app_state.i18n.t(lang, "error_restricted")
                if "restricted" in str(exc).lower()
                else app_state.i18n.t(lang, "error_download_failed")
            )
            await bot.send_message(request.chat_id, user_message)
            details = traceback.format_exc()
            await progress.stage_log("Error", error=str(exc))
            await app_state.admin_logger.notify(
                f"[{datetime.now(UTC).isoformat()}] ERROR user={request.user_id} video={request.youtube_id} quality={selected_quality}p\n{details}"
            )
            await progress.finish()
        except Exception:
            details = traceback.format_exc()
            await app_state.db.update_job(job_id, status="error", progress=0, error=details[:4000])
            await bot.send_message(request.chat_id, app_state.i18n.t(lang, "error_generic"))
            await progress.stage_log("Error", error="unexpected exception")
            await app_state.admin_logger.notify(
                f"[{datetime.now(UTC).isoformat()}] ERROR user={request.user_id} video={request.youtube_id} quality={selected_quality}p\n{details}"
            )
            await progress.finish()
        finally:
            if probe_file_path is not None:
                try:
                    probe_file_path.unlink(missing_ok=True)
                    parent = probe_file_path.parent
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                except Exception:
                    pass

            await app_state.db.delete_job(job_id)
            await app_state.unregister_task(job_id)

    return dp


async def bootstrap_state(bot: Bot, app_state: AppState) -> None:
    if app_state.admin_logger is None:
        app_state.admin_logger = AdminLogger(bot, app_state.get_admin_ids)

    await app_state.db.connect()
    await app_state.db.seed_admins(app_state.settings.admins)

    existing_group = await app_state.db.get_setting("group_chat_id")
    if existing_group is None and app_state.settings.group_chat_id is not None:
        await app_state.db.set_setting("group_chat_id", str(app_state.settings.group_chat_id))

    existing_cache_enabled = await app_state.db.get_setting("cache_enabled")
    if existing_cache_enabled is None:
        enabled = "1" if (app_state.settings.group_chat_id is not None) else "0"
        await app_state.db.set_setting("cache_enabled", enabled)


async def shutdown_state(app_state: AppState) -> None:
    await app_state.db.close()

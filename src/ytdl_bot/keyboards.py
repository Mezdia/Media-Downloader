from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .i18n import I18n
from .models import ActiveJob
from .utils import format_bytes


def language_keyboard(i18n: I18n) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for item in i18n.languages:
        current_row.append(
            InlineKeyboardButton(
                text=item.label,
                callback_data=f"lang:{item.code}",
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard(i18n: I18n, lang: str, is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=i18n.t(lang, "button_about_me"), callback_data="menu:about")],
        [InlineKeyboardButton(text=i18n.t(lang, "button_change_language"), callback_data="menu:language")],
    ]
    if is_admin:
        rows.insert(0, [InlineKeyboardButton(text=i18n.t(lang, "button_admin_panel"), callback_data="admin:panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def about_keyboard(i18n: I18n, lang: str, developer_url: str, project_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(lang, "button_github_developer"), url=developer_url)],
            [InlineKeyboardButton(text=i18n.t(lang, "button_github_project"), url=project_url)],
        ]
    )


def quality_keyboard(
    request_id: int,
    user_id: int,
    quality_sizes: dict[int, int | None],
) -> InlineKeyboardMarkup:
    sorted_items = sorted(quality_sizes.items(), key=lambda item: item[0])
    rows: list[list[InlineKeyboardButton]] = []
    for quality, size in sorted_items:
        size_label = format_bytes(size) if size is not None else "?"
        text = f"{quality}p — ~{size_label}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"q:{request_id}:{quality}:{user_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_panel_keyboard(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(lang, "admin_active_downloads"), callback_data="admin:active")],
            [InlineKeyboardButton(text=i18n.t(lang, "admin_usage_lookup"), callback_data="admin:usage_help")],
            [InlineKeyboardButton(text=i18n.t(lang, "admin_cache_manage"), callback_data="admin:cache_help")],
            [InlineKeyboardButton(text=i18n.t(lang, "admin_group_manage"), callback_data="admin:group_help")],
            [InlineKeyboardButton(text=i18n.t(lang, "admin_force_copy"), callback_data="admin:force_help")],
            [InlineKeyboardButton(text=i18n.t(lang, "admin_admins_manage"), callback_data="admin:admins_help")],
        ]
    )


def active_jobs_keyboard(i18n: I18n, lang: str, jobs: list[ActiveJob]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for job in jobs[:20]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.t(lang, "admin_cancel_job", job_id=job.job_id),
                    callback_data=f"admin:cancel:{job.job_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
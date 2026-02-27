from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot

from .bot import bootstrap_state, build_dispatcher, shutdown_state
from .config import load_settings
from .database import Database
from .i18n import I18n
from .state import AppState
from .youtube import YoutubeService


def _resolve_locales_dir() -> Path:
    # 1) explicit override
    env_locales = os.getenv("LOCALES_DIR", "").strip()
    if env_locales:
        path = Path(env_locales).expanduser().resolve()
        if path.exists():
            return path

    # 2) common runtime locations (source and container)
    candidates = [
        Path.cwd() / "locales",
        Path(__file__).resolve().parents[2] / "locales",
        Path(__file__).resolve().parents[1] / "locales",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not locate locales directory. "
        "Set LOCALES_DIR or ensure ./locales exists in runtime working directory."
    )


async def _main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    locales_dir = _resolve_locales_dir()

    bot = Bot(token=settings.bot_token)
    db = Database(settings.database_path)
    i18n = I18n(locales_dir)
    youtube = YoutubeService(settings.storage_path, settings.ffmpeg_path)
    app_state = AppState(settings=settings, db=db, i18n=i18n, youtube=youtube)

    await bootstrap_state(bot, app_state)
    dp = build_dispatcher(app_state)

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown_state(app_state)
        await bot.session.close()


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()

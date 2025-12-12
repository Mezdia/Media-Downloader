from __future__ import annotations

import asyncio

from .config import load_settings
from .database import Database


async def _main() -> None:
    settings = load_settings()
    db = Database(settings.database_path)
    await db.connect()
    await db.seed_admins(settings.admins)

    if settings.group_chat_id is not None:
        await db.set_setting("group_chat_id", str(settings.group_chat_id))
        await db.set_setting("cache_enabled", "1")
    else:
        await db.set_setting("cache_enabled", "0")

    await db.close()
    print("Migration complete")


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()
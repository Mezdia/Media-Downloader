
from pathlib import Path

from ytdl_bot.i18n import I18n
from ytdl_bot.progress import AdminLogger, JobLogContext, ProgressSession


class FakeBot:
    def __init__(self) -> None:
        self._next_message_id = 100
        self.edits: list[dict] = []

    async def send_message(self, chat_id: int, text: str):
        msg = type("Msg", (), {"message_id": self._next_message_id})
        self._next_message_id += 1
        return msg

    async def edit_message_text(self, *, text: str, chat_id: int, message_id: int):
        # This keyword-only signature guarantees the production code does not use positional args.
        self.edits.append({"text": text, "chat_id": chat_id, "message_id": message_id})
        return True

    async def delete_message(self, chat_id: int, message_id: int):
        return True


async def test_progress_updates_use_keyword_arguments() -> None:
    bot = FakeBot()
    i18n = I18n(Path("locales"))

    async def admins_provider():
        return set()

    logger = AdminLogger(bot, admins_provider)
    context = JobLogContext(
        user_id=123,
        username="tester",
        youtube_id="abc123",
        title="Sample",
        quality=720,
    )
    session = ProgressSession(
        bot=bot,
        i18n=i18n,
        admin_logger=logger,
        admin_ids=[],
        user_chat_id=321,
        user_lang="en",
        context=context,
    )

    await session.start()
    await session.update("downloading", 10.0, force=True)

    assert len(bot.edits) >= 1
    assert bot.edits[0]["chat_id"] == 321

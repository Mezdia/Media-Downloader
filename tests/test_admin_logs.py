from ytdl_bot.progress import AdminLogger, JobLogContext


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str):
        self.sent.append((chat_id, text))
        return {"ok": True}


async def test_admin_stage_log_contains_required_fields() -> None:
    bot = FakeBot()

    async def admins_provider():
        return {101, 202}

    logger = AdminLogger(bot, admins_provider)
    context = JobLogContext(
        user_id=999,
        username="tester",
        youtube_id="abc123",
        title="Sample",
        quality=720,
    )

    await logger.stage(
        stage="Downloading",
        context=context,
        progress=42.0,
        eta="00:01:20",
        size_bytes=123456,
    )

    assert len(bot.sent) == 2
    for _, text in bot.sent:
        assert "Downloading" in text
        assert "user: 999 (@tester)" in text
        assert "video: abc123" in text
        assert "quality: 720p" in text
        assert "progress: 42.0%" in text
        assert "ETA: 00:01:20" in text
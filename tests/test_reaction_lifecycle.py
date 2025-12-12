import random
from types import SimpleNamespace

from ytdl_bot.ux import apply_random_reaction, safe_delete_messages, send_processing_messages


class FakeMessage:
    def __init__(self, chat_id: int = 1, message_id: int = 10) -> None:
        self.chat = SimpleNamespace(id=chat_id)
        self.message_id = message_id
        self.replies: list[str] = []
        self._next_id = 100

    async def reply(self, text: str):
        self.replies.append(text)
        msg = SimpleNamespace(chat=self.chat, message_id=self._next_id)
        self._next_id += 1
        return msg


class FakeBot:
    def __init__(self) -> None:
        self.reactions: list[tuple[int, int, str]] = []
        self.deleted: list[tuple[int, int]] = []

    async def set_message_reaction(self, chat_id: int, message_id: int, reaction, is_big: bool = False):
        emoji = reaction[0].emoji
        self.reactions.append((chat_id, message_id, emoji))

    async def delete_message(self, chat_id: int, message_id: int):
        self.deleted.append((chat_id, message_id))


async def test_reaction_and_temporary_message_lifecycle(monkeypatch) -> None:
    monkeypatch.setattr(random, "choice", lambda seq: "👀")

    bot = FakeBot()
    message = FakeMessage(chat_id=555, message_id=42)

    chosen = await apply_random_reaction(bot, message)
    assert chosen == "👀"
    assert bot.reactions == [(555, 42, "👀")]

    ghost, processing = await send_processing_messages(message, "Processing...")
    assert message.replies == ["👾", "Processing..."]

    await safe_delete_messages(bot, 555, [ghost.message_id, processing.message_id])
    assert bot.deleted == [(555, ghost.message_id), (555, processing.message_id)]
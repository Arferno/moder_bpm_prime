from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union


class ChatTypeFilter(BaseFilter):
    """Filter to check chat type."""

    def __init__(self, *chat_types: str):
        self.chat_types = chat_types

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if isinstance(event, Message):
            return event.chat.type in self.chat_types
        elif isinstance(event, CallbackQuery) and event.message:
            return event.message.chat.type in self.chat_types
        return False


# Common filters
GroupFilter = ChatTypeFilter("group", "supergroup")
PrivateFilter = ChatTypeFilter("private")
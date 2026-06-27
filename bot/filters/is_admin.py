from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.config import settings


class IsAdminFilter(BaseFilter):
    """Filter to check if user is admin."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        return message.from_user.id in settings.admin_ids


class IsSuperAdminFilter(BaseFilter):
    """Filter to check if user is super admin."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        return message.from_user.id == settings.super_admin_id


class IsNotBannedFilter(BaseFilter):
    """Filter to check if user is not banned."""

    async def __call__(self, message: Message) -> bool:
        # This will be checked in middleware with database
        return True
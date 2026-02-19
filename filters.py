"""Библиотеки для проверки пользователя"""

from datetime import datetime
from aiogram.filters import BaseFilter
from aiogram.types import Message

from models import Role, User, UserRole


class IsRole(BaseFilter):
    """Проверяет наличие привелегии у пользователя"""

    def __init__(self, role_name: str) -> None:
        self.role = Role.get(name=role_name)

    def check(self, user: User) -> bool:
        """Проверяет у пользователя роль"""

        user_role: UserRole = (
            UserRole.select()
            .where(
                (UserRole.user == user)
                & (UserRole.role == self.role)
            )
            .first()
        )
        return user_role is not None

    async def __call__(self, message: Message) -> bool:
        user: User = User.get_or_none(tg_id=message.from_user.id)

        if user is None:
            return False

        return self.check(user)

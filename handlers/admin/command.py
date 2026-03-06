from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from filters import IsRole
from handlers.common import start_room_handler
from keyboards import get_admin_menu
from models import Role, User, UserRole


ROUTER = Router()
ROUTER.message.filter(IsRole("Администратор"))
ROUTER.callback_query.filter(IsRole("Администратор"))


@ROUTER.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):

    if await start_room_handler(message, state):
        await message.answer(
            text="Добро пожаловать, администратор.", reply_markup=get_admin_menu()
        )


@ROUTER.message(Command("add_admin"))
async def add_admin_handler(message: Message):
    try:
        user_id = int(message.text.split()[-1])
        user, _ = User.get_or_create(id=user_id)
        UserRole.get_or_create(user=user, role=Role.get(name="Администратор"))
        await message.answer("Роль администратора добавлена")
    except Exception as ex:
        await message.answer(f"Ошибка: {ex}")
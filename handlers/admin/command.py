from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from filters import IsRole
from handlers.common import start_room_handler
from keyboards import get_admin_menu
from models import Role, User, UserRole


router = Router()
router.message.filter(IsRole("Администратор"))
router.callback_query.filter(IsRole("Администратор"))


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):

    if await start_room_handler(message, state):
        await message.answer(
            text="Добро пожаловать, администратор.", reply_markup=get_admin_menu()
        )


@router.message(Command("add_admin"))
async def add_admin_handler(message: Message):
    try:
        user_id = int(message.text.split()[-1])
        user = User.get_or_none(id=user_id)

        if user is None:
            await message.answer(text='Такой полдьзователь не запускал бота')
            return

        UserRole.get_or_create(user=user, role=Role.get(name="Администратор"))
        await message.answer("Роль администратора добавлена")
    except ValueError as ex:
        await message.answer(f"Ошибка: {ex}")

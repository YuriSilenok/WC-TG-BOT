from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from models import Appeal, Room, User
from states import UserStates
from handlers.common import start_room_handler

ROUTER = Router()

@ROUTER.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):

    if await start_room_handler(message, state):    
        await message.answer(
            text="Добро пожаловать!!!"
        )

@ROUTER.message(UserStates.waiting_for_appeal)
async def handle_appeal(message: Message, state: FSMContext):
    data = await state.get_data()
    room_id = data.get('room_id')
    
    if room_id is None:
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.clear()
        return
    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await message.answer("Помещение не найдено")
    
    # Сохраняем обращение
    Appeal.create(
        room=room,
        author=message.from_user.id,
        message=message.text
    )
    
    # Отправляем подтверждение пользователю
    await message.answer("Спасибо за обращение, мы уже его передали администрации")
    
    # Пересылаем обращение администратору
    # admin_user = User.gegek htrdtcnj dytnbt(User.user_id == room.admin_id)
    appeal_text = f"Новое обращение по помещению '{room.name}':\n\n{message.text}"
    await message.bot.send_message(room.creator.tg_id, appeal_text)
    await state.clear()


@ROUTER.message(Command('get_id'))
async def get_id_handler(message: Message):
    await message.answer(
        text=f'`{message.from_user.id}`',
        parse_mode=ParseMode.MARKDOWN_V2
    )

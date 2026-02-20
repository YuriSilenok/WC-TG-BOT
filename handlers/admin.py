import os
from typing import List

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.fsm.context import FSMContext

from filters import IsRole
from keyboards import get_admin_menu, get_delete_confirmation, get_room_actions
from models import Appeal, Room, User, UserRole, Role
from states import AdminStates
from utils import generate_qr_code
from handlers.common import start_room_handler


ROUTER = Router()
ROUTER.message.filter(IsRole('Администратор'))
ROUTER.callback_query.filter(IsRole('Администратор'))


@ROUTER.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):

    if await start_room_handler(message, state):
        await message.answer(
            text="Добро пожаловать, администратор.",
            reply_markup=get_admin_menu()
        )


@ROUTER.message(F.text == "Добавить помещение")
async def add_room_start(message: Message, state: FSMContext):
    
    await message.answer("Введите название помещения:")
    await state.set_state(AdminStates.waiting_for_room_name)



@ROUTER.message(AdminStates.waiting_for_room_name)
async def add_room_finish(message: Message, state: FSMContext):
    room_name = message.text.strip()
    
    # Создаем помещение
    Room.create(
        name=room_name,
        creator=message.from_user.id
    )
    
    await message.answer(f"Помещение '{room_name}' добавлено!")
    await state.clear()


@ROUTER.message(F.text == "Список помещений")
async def list_rooms(message: Message):
    rooms: List[Room] = Room.select().where(
        (Room.creator == message.from_user.id) &
        (Room.is_archived == False)
    )
    
    if len(rooms) == 0:
        await message.answer("Нет доступных помещений")
        return
    
    for room in rooms:
        await message.answer(
            text=f"Помещение: {room.name}",
            reply_markup=get_room_actions(room.id)
        )


@ROUTER.callback_query(F.data.startswith("appeals_"))
async def show_appeals(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[1])
    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return
    
    appeals: List[Appeal] = (Appeal.select()
                .where(Appeal.room == room)
                .order_by(Appeal.created_at.desc())
                .limit(10))
    
    if len(appeals) == 0:
        await callback.message.answer("Нет обращений для этого помещения")
        return
    
    response = "Последние обращения:\n\n"
    for appeal in appeals:
        date_str = appeal.created_at.strftime("%d.%m.%Y %H:%M")
        response += f"📅 {date_str}\n{appeal.message}\n\n"
    
    await callback.message.answer(response)
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("qrcode_"))
async def send_qr_code(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[1])
    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    qr_image, url = generate_qr_code(
        room_id=room_id, 
        bot_username=(await callback.bot.me()).username
    )
    
    # Создаем временный файл
    with open(f"qr_{room_id}.png", "wb") as f:
        f.write(qr_image.getvalue())
    
    # Отправляем изображение
    photo = FSInputFile(f"qr_{room_id}.png")
    await callback.message.answer_photo(
        photo, 
        caption=f"QR-код для помещения: {room.name}\nURL: {url}"
    )
    
    # Удhived = Trueаляем временный файл
    os.remove(f"qr_{room_id}.png")    
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("delete_"))
async def delete_room_start(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[1])

    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    keyboard = get_delete_confirmation(room_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[2])
    keyboard = get_room_actions(room_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[2])    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    room.is_archived = True
    room.save()
    
    await callback.message.edit_text(f"Помещение '{room.name}' удалено")
    await callback.answer()


@ROUTER.message(Command("add_admin"))
async def add_admin_handler(message: Message):
    try:
        user_id  = int(message.text.split()[-1])
        user, _ = User.get_or_create(tg_id=user_id)
        UserRole.get_or_create(
            user=user,
            role=Role.get(name='Администратор')
        )
        await message.answer('Роль администратора добавлена')
    except Exception as ex:
        await message.answer(f'Ошибка: {ex}')
import os
from typing import List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)

from filters import IsRole
from keyboards import get_delete_confirmation, get_room_actions, get_rooms
from models import Answer, Appeal, Room
from qr_code import generate
from states import AdminStates


router = Router()
router.message.filter(IsRole("Администратор"))
router.callback_query.filter(IsRole("Администратор"))


@router.message(F.text == "Добавить помещение")
async def add_room_start(message: Message, state: FSMContext):

    await message.answer("Введите название помещения:")
    await state.set_state(AdminStates.waiting_for_room_name)


@router.message(AdminStates.waiting_for_room_name)
async def add_room_finish(message: Message, state: FSMContext):
    room_name = message.text.strip()

    # Создаем помещение
    Room.create(name=room_name, creator=message.from_user.id)

    await message.answer(f"Помещение '{room_name}' добавлено!")
    await state.clear()


@router.message(F.text == "Список помещений")
async def list_rooms(message: Message):
    rooms: List[Room] = list(
        Room.select().where(
            (Room.creator == message.from_user.id) & (Room.is_archived == False)
        )
    )

    if len(rooms) == 0:
        await message.answer("Нет доступных помещений")
        return

    text = f"Помещения. Всего: {len(rooms)}"

    await message.answer(
        text=text,
        reply_markup=get_rooms(
            rooms=[(room.id, room.name) for room in rooms],
        )
    )


@router.callback_query(F.data.startswith("room_answers_"))
async def room_answers_handler(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    room: Room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.answer("Помещение не найдено")
        return

    answers: List[Answer] = list(Answer.select().where(Answer.room == room.id))

    inline_keyboard = []
    for answer in answers:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=str(answer.text),
                    callback_data=f"answer_menu_{answer.id}",
                ),
            ]
        )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    text = f"Вопросы для команты: {room.name}"

    await callback.message.answer(text=text, reply_markup=reply_markup)


@router.callback_query(F.data.startswith("room_info_"))
async def show_info_room(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    room: Room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.answer("Помещение не найдено")
        return

    text = f"Помещение: {room.name}"
    await callback.answer(text=text)


@router.callback_query(F.data.startswith("room_messages_"))
async def show_appeals(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])

    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.answer("Помещение не найдено")
        return

    appeals: List[Appeal] = (
        Appeal.select()
        .where(Appeal.room == room)
        .order_by(Appeal.created_at.desc())
        .limit(10)
    )

    if len(appeals) == 0:
        await callback.answer("Нет обращений для этого помещения")
        return

    response = "Последние обращения:\n\n"
    for appeal in appeals:
        date_str = appeal.created_at.strftime("%d.%m.%Y %H:%M")
        response += f"📅 {date_str}\n{appeal.message}\n\n"

    await callback.message.answer(response)
    await callback.answer()


@router.callback_query(F.data.startswith("room_qr_"))
async def send_qr_code(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])

    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    qr_image, url = generate(
        room_id=room_id, bot_username=(await callback.bot.me()).username
    )

    # Создаем временный файл
    with open(f"qr_{room_id}.png", "wb") as f:
        f.write(qr_image.getvalue())

    # Отправляем изображение
    photo = FSInputFile(f"qr_{room_id}.png")
    await callback.message.answer_photo(
        photo, caption=f"QR-код для помещения: {room.name}\nURL: {url}"
    )

    # Удhived = Trueаляем временный файл
    os.remove(f"qr_{room_id}.png")
    await callback.answer()


@router.callback_query(F.data.startswith("room_delete_"))
async def delete_room_start(callback: CallbackQuery):
    """Удалить помещение"""
    room_id = int(callback.data.split("_")[-1])

    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    keyboard = get_delete_confirmation(room_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    keyboard = get_room_actions(room_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    room.is_archived = True
    room.save()

    await callback.message.edit_text(
        text=f"Помещение '{room.name}' удалено", reply_markup=None
    )

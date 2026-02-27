import os
from typing import List, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, FSInputFile, Message, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from filters import IsRole
from keyboards import get_admin_menu, get_delete_confirmation, get_room_actions, room_notify
from models import Appeal, Question, Room, User, UserRole, Role
from states import AdminStates, AddNotify
from qr_code import generate
from handlers.common import start_room_handler


ROUTER = Router()
ROUTER.message.filter(IsRole('Администратор'))
ROUTER.callback_query.filter(IsRole('Администратор'))




def get_data_rooms(user_id:int) -> List[Tuple[int, str, bool]]:
    """Получает данные по комнатам в табличном виде для пользователя"""
    active_rooms = Room.get_active_by_user(
        user_id=user_id
    )
    return [(room.id, room.name, False) for room in active_rooms]
    

@ROUTER.message(F.text=='Назначить ответственных')
async def add_user_notify_handler(message: Message, state: FSMContext):
    """Выбрать комнаты для добалвения уведомлений по ним"""
    await state.set_state(state=AddNotify.waiting_rooms)
    active_rooms: List[Room] = Room.get_active_by_user(
        user_id=message.from_user.id
    )
    rooms = [(room.id, room.name, False) for room in active_rooms]
    await state.update_data(rooms=rooms)
    await message.answer(
        text='Вы перешли в режим добавления сотрудников, '
        'которые будут получать сообщения о проблемах '
        'в определенных помещениях. \n\nОтправьте id пользователя. '
        'Пользователь его может получить при помощи команды /get_id'
        '\n\nЕсли передумали, нажмите кнопку Отменить',
        reply_markup=room_notify(
            rooms=rooms
        )
    )


@ROUTER.callback_query(
        AddNotify.waiting_rooms,
        F.data.startswith('room_notify_'))
async def mark_romm_notify_handler(callback: CallbackQuery, state: FSMContext):
    """Выбрать комнаты для добалвения уведомлений по ним"""
    data = await state.get_data()
    rooms = data.get('rooms', None)

    if not rooms:
        rooms = get_data_rooms(callback.from_user.id)
    room_id = int(callback.data.split("_")[-1])

    for i, _ in enumerate(rooms):
        if rooms[i][0] == room_id:
            rooms[i] = rooms[i][0], rooms[i][1], not rooms[i][2]
            break

    await callback.message.edit_reply_markup(
        reply_markup=room_notify(
            rooms=rooms
        )
    )

@ROUTER.message(
        AddNotify.waiting_user_id,
        F.data.startswith('room_notify_'))
async def get_user_id_handler(message: Message, state: FSMContext):
    """Доабвление пользователей"""
    try:
        tg_id = int(message.text)
        user = User.get_or_none(tg_id=tg_id)
        if user in None:
            await message.answer(
                text=f'Пользователя с ID={tg_id} нет в БД. '
                'Попросите его запустить бота.'
            )
            return
        data: dict = await state.get_data()
        users: list = data.get('users', [])
        users.append(user)
        await message.answer(
            text=f'Пользователь с ID={tg_id} записан. Добавьте еще несколько пользователей или нажмите кнопку Далее, что бы перейти к добавлению помещений'
        )


    except ValueError as ex:
        await message.answer(f'Ошибка: {ex}')



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
    rooms: List[Room] = list(
        Room.select().where(
            (Room.creator == message.from_user.id) &
            (Room.is_archived == False)
        )
    )
    
    if len(rooms) == 0:
        await message.answer("Нет доступных помещений")
        return
    
    text = f'Помещения. Всего: {len(rooms)}'
    inline_keyboard = []
    for room in rooms:
        inline_keyboard.append([
            InlineKeyboardButton(text=str(room.name), callback_data=f'room_info_{room.id}'),
            InlineKeyboardButton(text='📃', callback_data=f'room_messages_{room.id}'),
            InlineKeyboardButton(text='❓', callback_data=f'room_questions_{room.id}'),
            InlineKeyboardButton(text='QR', callback_data=f'room_qr_{room.id}'),
            InlineKeyboardButton(text='🗑️', callback_data=f'room_delete_{room.id}'),
        ])
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=inline_keyboard
    )
    await message.answer(text=text, reply_markup=reply_markup)


@ROUTER.callback_query(F.data.startswith("room_questions_"))
async def room_questions_handler(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    room: Room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.answer("Помещение не найдено")
        return
    
    questions: List[Question] = (
        Question.select().where(Question.room_id==room.id))
    
    inline_keyboard = []
    for question in questions:
        inline_keyboard.append([
            InlineKeyboardButton(text=str(question.text), callback_data=f'question_menu_{question.id}'),
        ])
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=inline_keyboard
    )
    text = f'Вопросы для команты: {room.name}'


    await callback.message.answer(text=text, reply_markup=reply_markup)



@ROUTER.callback_query(F.data.startswith("room_info_"))
async def show_info_room(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    room: Room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.answer("Помещение не найдено")
        return
    
    text = f'Помещение: {room.name}'
    await callback.answer(text=text)


@ROUTER.callback_query(F.data.startswith("room_messages_"))
async def show_appeals(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.answer("Помещение не найдено")
        return
    
    appeals: List[Appeal] = (Appeal.select()
                .where(Appeal.room == room)
                .order_by(Appeal.created_at.desc())
                .limit(10))
    
    if len(appeals) == 0:
        await callback.answer("Нет обращений для этого помещения")
        return
    
    response = "Последние обращения:\n\n"
    for appeal in appeals:
        date_str = appeal.created_at.strftime("%d.%m.%Y %H:%M")
        response += f"📅 {date_str}\n{appeal.message}\n\n"
    
    await callback.message.answer(response)
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("room_qr_"))
async def send_qr_code(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    qr_image, url = generate(
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


@ROUTER.callback_query(F.data.startswith("room_delete_"))
async def delete_room_start(callback: CallbackQuery):
    """Удалить помещение"""
    room_id = int(callback.data.split("_")[-1])

    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    keyboard = get_delete_confirmation(room_id)
    await callback.message.edit_reply_markup(
        reply_markup=keyboard)
    
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])
    keyboard = get_room_actions(room_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@ROUTER.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[-1])    
    room = Room.get_or_none(id=room_id)
    if room is None:
        await callback.message.answer("Помещение не найдено")
        return

    room.is_archived = True
    room.save()
    
    await callback.message.edit_text(
        text=f"Помещение '{room.name}' удалено",
        reply_markup=None
    )


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

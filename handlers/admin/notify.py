from typing import List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.methods import SendMessage
from aiogram.types import CallbackQuery, Message

from filters import IsRole
from keyboards import room_notify
from models import Notify, Room, User
from states import AddNotify


router = Router()
router.message.filter(IsRole("Администратор"))
router.callback_query.filter(IsRole("Администратор"))


@router.message(F.text == "Назначить ответственных")
async def add_user_notify_handler(message: Message, state: FSMContext):
    """Выбрать комнаты для добалвения уведомлений по ним"""
    await state.set_state(state=AddNotify.waiting_room_and_user)
    active_rooms: List[Room] = Room.get_active_by_user(
        user_id=message.from_user.id)
    data = await state.get_data()
    data['rooms'] = data.get(
        'rooms',
        [(room.id, room.name, False) for room in active_rooms]
    )
    data['users'] = data.get('users', [])
    await state.update_data(data=data)

    m: SendMessage = await message.answer(
        text="Вы перешли в режим добавления сотрудников, которые будут "
        "получать сообщения о проблемах в определенных помещениях. \n\n"
        "Кнопками выберите аудитории, для которых нужно добавить уведомления."
        "\n\nОтправьте id пользователя. Пользователь его может получить при "
        "помощи команды /get_id \n\nЕсли передумали, нажмите кнопку Отменить."
        "\nДля завершения, нажмите кнопку Готово",
        reply_markup=room_notify(rooms=data['rooms'], users=data['users']),
    )
    await state.update_data(last_message=(m.chat.id, m.message_id))


@router.callback_query(AddNotify.waiting_room_and_user,
                       F.data.startswith("room_notify_"))
async def mark_room_notify_handler(callback: CallbackQuery, state: FSMContext):
    """Выбрать комнаты для добавления уведомлений по ним"""
    data = await state.get_data()
    rooms = data['rooms']
    room_id = int(callback.data.split("_")[-1])

    for i, _ in enumerate(rooms):
        if rooms[i][0] == room_id:
            rooms[i] = rooms[i][0], rooms[i][1], not rooms[i][2]
            break

    await callback.message.edit_reply_markup(
        reply_markup=room_notify(
            rooms=rooms,
            users=data['users'],
        )
    )


@router.message(AddNotify.waiting_room_and_user, F.text.isdigit())
async def get_user_id_handler(message: Message, state: FSMContext):
    """Добавление пользователей для уведомлений"""
    try:
        user_id = int(message.text)
        user = User.get_or_none(id=user_id)
        if user is None:
            await message.answer(
                text=f"Пользователя с ID={user_id} нет в БД. "
                "Попросите его запустить бота."
            )
            return
        data: dict = await state.get_data()
        users: list = data.get("users", [])
        if user_id in users:
            await message.reply('Такой пользователь уже добавлен')
            return
        users.append(user_id)
        await state.update_data(users=users)
        chat_id, message_id = data['last_message']
        await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await add_user_notify_handler(message, state)

    except ValueError as ex:
        await message.answer(f"Ошибка: {ex}")


@router.callback_query(
    F.data.startswith('del_user_by_room_notify_'),
    AddNotify.waiting_room_and_user,
)
async def del_user_handler(callback: CallbackQuery, state: FSMContext):
    """Удалить добавляемого пользователя"""
    data = await state.get_data()
    users: List[int] = data.get('users', [])
    user_id = int(callback.data.split('_')[-1])
    if user_id in users:
        users.remove(user_id)
        await callback.message.edit_reply_markup(
            reply_markup=room_notify(
                rooms=data.get('rooms', []),
                users=data.get('users', []),
            )
        )
        await callback.answer('Подписчик удален')
        await state.update_data(data=data)
    else:
        await callback.answer('Подписчик не найден')


@router.callback_query(
    F.data == 'add_notify_done',
    AddNotify.waiting_room_and_user)
async def next_handlers(cq: CallbackQuery, state: FSMContext):
    """Переход для назначения ответсвенных за аудитории"""

    data = await state.get_data()
    rooms = list(filter(lambda room: room[2], data['rooms']))
    if len(rooms) == 0:
        await cq.answer('Не выбраны помещения')
        return

    users = data['users']
    if len(users) == 0:
        await cq.answer('Не добавлены пользователи')

    text = []

    for room_id, _, _ in rooms:
        for user_id in users:
            notify, created = Notify.get_or_create(
                user_id=user_id,
                room_id=room_id
            )

            if created:
                text.append(f'{notify.room.name}->{notify.user.id}')

    if text:
        await cq.message.answer(
            text='Добавлены следующие подписчики на обращения по помещениям:\n' +
            ('\n'.join(map(str, text)))
        )
        await state.clear()
        await cq.message.delete()
    else:
        await cq.answer('Новых подписчиков на обращения по помещениям не обнаружено')

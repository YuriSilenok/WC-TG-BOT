from typing import List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.methods import SendMessage
from aiogram.types import CallbackQuery, Message

from filters import IsRole
from keyboards import room_answer
from models import Answer, Room
from states import AddAnswer


router = Router()
router.message.filter(IsRole("Администратор"))
router.callback_query.filter(IsRole("Администратор"))


@router.message(F.text == "Добавить ответы")
async def add_answer_handler(message: Message, state: FSMContext):
    """Добавление вариантов ответов при ображщении"""
    await state.set_state(state=AddAnswer.waiting_answer)
    active_rooms: List[Room] = Room.get_active_by_user(
        user_id=message.from_user.id)
    data = await state.get_data()
    data['rooms'] = data.get(
        'rooms',
        [(room.id, room.name, False) for room in active_rooms]
    )
    data['answers'] = data.get('answers', [])
    await state.update_data(data=data)

    m: SendMessage = await message.answer(
        text="Вы перешли в режим добавления отзывов, которые будут "
        "отображаться пользователям при выборе помещения. \n\n"
        "Если передумали, нажмите кнопку Отменить."
        "\nДля завершения, нажмите кнопку Готово",
        reply_markup=room_answer(rooms=data['rooms'], answers=data['answers']),
    )
    await state.update_data(last_message=(m.chat.id, m.message_id))


@router.callback_query(AddAnswer.waiting_answer,
                       F.data.startswith("room_answer_"))
async def mark_room_notify_handler(callback: CallbackQuery, state: FSMContext):
    """Выбрать комнаты для добавления отзывов по ним"""
    data = await state.get_data()
    rooms = data['rooms']
    room_id = int(callback.data.split("_")[-1])

    for i, _ in enumerate(rooms):
        if rooms[i][0] == room_id:
            rooms[i] = rooms[i][0], rooms[i][1], not rooms[i][2]
            break

    await callback.message.edit_reply_markup(
        reply_markup=room_answer(
            rooms=rooms,
            answers=data['answers'],
        )
    )


@router.message(AddAnswer.waiting_answer)
async def get_answer_id_handler(message: Message, state: FSMContext):
    """Добавление отзывов для помещений"""
    data: dict = await state.get_data()
    answers: list = data.get("answers", [])
    answer: str = message.text
    if answer in answers:
        await message.reply('Такой отзыв уже добавлен')
        return
    answers.append(answer)
    await state.update_data(answers=answers)
    chat_id, message_id = data['last_message']
    await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await add_answer_handler(message, state)


@router.callback_query(
    F.data.startswith('del_answer_by_room_notify_'),
    AddAnswer.waiting_answer,
)
async def del_answer_handler(callback: CallbackQuery, state: FSMContext):
    """Удалить отзыва для пользователя"""
    data = await state.get_data()
    answers: List[str] = data.get('answers', [])
    answer_ind = int(callback.data.split('_')[-1])

    if not (0 <= answer_ind < len(answers)):
        await callback.answer(text='Такой отзыв не найден. Обратитесь к администратору')
        return

    del answers[answer_ind]

    await callback.message.edit_reply_markup(
        reply_markup=room_answer(
            rooms=data.get('rooms', []),
            answers=answers,
        )
    )
    await callback.answer('Отзыв удален')
    await state.update_data(data=data)


@router.callback_query(
    F.data == 'add_answer_done',
    AddAnswer.waiting_answer)
async def next_handlers(cq: CallbackQuery, state: FSMContext):
    """Переход для назначения ответсвенных за аудитории"""

    data = await state.get_data()
    rooms = list(filter(lambda room: room[2], data['rooms']))
    if len(rooms) == 0:
        await cq.answer('Не выбраны помещения')
        return

    answers = data['answers']
    if len(answers) == 0:
        await cq.answer('Не добавлены отзывы')

    text = []

    for room_id, _, _ in rooms:
        for answer in answers:
            notify, created = Answer.get_or_create(
                text=answer,
                room_id=room_id
            )

            if created:
                text.append(f'{notify.room.name}->{answer}')

    if text:
        await cq.message.answer(
            text='Добавлены следующие отзывы на обращения по помещениям:\n' +
            ('\n'.join(map(str, text)))
        )
        await state.clear()
        await cq.message.delete()
    else:
        await cq.answer('Новых отизывов на обращения по можещениям не обнаружено')

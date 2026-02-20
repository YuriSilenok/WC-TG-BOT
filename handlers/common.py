from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from models import Room, User
from states import UserStates


async def start_room_handler(message: Message, state: FSMContext):
    await state.clear()
    User.get_or_none(tg_id=message.from_user.id)
    # Проверяем параметры команды
    if len(message.text.split()) > 1:
        # Пользователь перешел по QR-коду
        param = message.text.split()[1]
        if param.startswith('room_'):
            room_id = int(param.split('_')[1])
            room:Room = Room.get_or_none(id=room_id)
            if room is None:
                await message.answer("Помещение не найдено")
                return False
            
            await state.update_data(room_id=room_id)
            await state.set_state(state=UserStates.waiting_for_appeal)
            await message.answer(text=f"Оставьте обращение по помещению '{room.name}'")
            return False
    
    return True
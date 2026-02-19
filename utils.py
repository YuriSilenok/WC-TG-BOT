from typing import Tuple
import qrcode
from io import BytesIO

from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from models import Room, User
from states import UserStates


def generate_qr_code(room_id: int, bot_username: str) -> Tuple[BytesIO, str]:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    url = f"https://t.me/{bot_username}?start=room_{room_id}"
    
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем изображение в байтовый поток
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    return bio, url

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
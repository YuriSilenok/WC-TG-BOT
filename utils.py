from typing import Tuple
import qrcode
from io import BytesIO


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


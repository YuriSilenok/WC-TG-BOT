from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить помещение"), KeyboardButton(text="Список помещений")]
        ],
        resize_keyboard=True
    )

def get_room_actions(room_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обращения", callback_data=f"appeals_{room_id}")],
            [InlineKeyboardButton(text="QR-code", callback_data=f"qrcode_{room_id}")],
            [InlineKeyboardButton(text="Удалить", callback_data=f"delete_{room_id}")]
        ]
    )

def get_delete_confirmation(room_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_delete_{room_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data=f"cancel_delete_{room_id}")]
        ]
    )

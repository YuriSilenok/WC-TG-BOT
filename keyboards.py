from typing import List, Tuple
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Добавить помещение"),
                KeyboardButton(text="Список помещений"),
            ],[
                KeyboardButton(text="Назначить ответственных"),
            ],
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

def get_delete_confirmation(room_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Подтвердить",
                callback_data=f"confirm_delete_{room_id}")],
            [InlineKeyboardButton(
                text="Отмена",
                callback_data=f"cancel_delete_{room_id}")]
        ]
    )

def room_notify(rooms: List[Tuple[int, str, bool]]):
    inline_keyboard = []
    row = []
    for room_id, room_name, mark in rooms:
        if len(row) >= 6:
            inline_keyboard.append(row)
            row = []
        row.append(
            InlineKeyboardButton(
                text=f"{'✅' if mark else '❌'} {room_name}",
                callback_data=f"room_notify_{room_id}"
            )
        )

    if row:
        inline_keyboard.append(row)

    inline_keyboard.append([
        InlineKeyboardButton(
            text='Далее',
            callback_data='waiting_rooms_next'
        ),
        InlineKeyboardButton(
            text='Отменить',
            callback_data='cancel'
        ),
    ])
    return InlineKeyboardMarkup(
        inline_keyboard=inline_keyboard
    )

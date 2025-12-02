import os
import qrcode
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from peewee import *

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'database.db')
# Настройка базы данных
db = SqliteDatabase(DB_PATH)

# Модели базы данных
class BaseModel(Model):
    class Meta:
        database = db

class Room(BaseModel):
    name = CharField()
    admin_id = BigIntegerField()
    is_archived = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)

class Appeal(BaseModel):
    room = ForeignKeyField(Room, backref='appeals')
    user_id = BigIntegerField()
    message = TextField()
    created_at = DateTimeField(default=datetime.now)

class User(BaseModel):
    user_id = BigIntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField()
    is_admin = BooleanField(default=False)

# Создание таблиц
def create_tables():
    with db:
        db.create_tables([Room, Appeal, User])

# Состояния FSM
class AdminStates(StatesGroup):
    waiting_for_room_name = State()
    waiting_for_delete_confirmation = State()

class UserStates(StatesGroup):
    waiting_for_appeal = State()

# Настройка бота
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Клавиатуры
def get_admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить помещение"), KeyboardButton(text="Список помещений")]
        ],
        resize_keyboard=True
    )

def get_room_actions_keyboard(room_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обращения", callback_data=f"appeals_{room_id}")],
            [InlineKeyboardButton(text="QR-code", callback_data=f"qrcode_{room_id}")],
            [InlineKeyboardButton(text="Удалить", callback_data=f"delete_{room_id}")]
        ]
    )

def get_delete_confirmation_keyboard(room_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_delete_{room_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data=f"cancel_delete_{room_id}")]
        ]
    )

# Проверка администратора
async def is_admin(user_id):
    try:
        user = User.get(User.user_id == user_id)
        return user.is_admin
    except User.DoesNotExist:
        return False

# Генерация QR-кода
def generate_qr_code(room_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Создаем ссылку для запуска бота с параметром room_id
    bot_username = "news_tester_bot"  # Замените на username вашего бота
    url = f"https://t.me/{bot_username}?start=room_{room_id}"
    
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем изображение в байтовый поток
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    return bio, url

# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Регистрируем пользователя если его нет
    try:
        User.get(User.user_id == message.from_user.id)
    except User.DoesNotExist:
        User.create(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
    
    # Проверяем параметры команды
    if len(message.text.split()) > 1:
        # Пользователь перешел по QR-коду
        param = message.text.split()[1]
        if param.startswith('room_'):
            room_id = int(param.split('_')[1])
            await handle_qr_start(message, room_id, state)
            return
    
    # Проверяем является ли пользователь администратором
    if await is_admin(message.from_user.id):
        await message.answer(
            "Добро пожаловать, администратор!!!",
            reply_markup=get_admin_main_menu()
        )
    else:
        await message.answer("Добро пожаловать!!!")

async def handle_qr_start(message: Message, room_id: int, state: FSMContext):
    try:
        room = Room.get((Room.id == room_id) & (Room.is_archived == False))
        await state.update_data(room_id=room_id)
        await state.set_state(UserStates.waiting_for_appeal)
        await message.answer(f"Оставьте обращение по помещению '{room.name}'")
    except Room.DoesNotExist:
        await message.answer("Помещение не найдено")

# Обработчики для администратора
@router.message(F.text == "Добавить помещение")
async def add_room_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    await message.answer("Введите название помещения:")
    await state.set_state(AdminStates.waiting_for_room_name)

@router.message(AdminStates.waiting_for_room_name)
async def add_room_finish(message: Message, state: FSMContext):
    room_name = message.text.strip()
    
    # Создаем помещение
    room = Room.create(
        name=room_name,
        admin_id=message.from_user.id
    )
    
    await message.answer(f"Помещение '{room_name}' добавлено!")
    await state.clear()

@router.message(F.text == "Список помещений")
async def list_rooms(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    rooms = Room.select().where(Room.is_archived == False)
    
    if not rooms:
        await message.answer("Нет доступных помещений")
        return
    
    for room in rooms:
        keyboard = get_room_actions_keyboard(room.id)
        await message.answer(f"Помещение: {room.name}", reply_markup=keyboard)

# Обработчики callback-запросов
@router.callback_query(F.data.startswith("appeals_"))
async def show_appeals(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[1])
    
    try:
        room = Room.get(Room.id == room_id)
        appeals = (Appeal.select()
                  .where(Appeal.room == room)
                  .order_by(Appeal.created_at.desc())
                  .limit(10))
        
        if not appeals:
            await callback.message.answer("Нет обращений для этого помещения")
            return
        
        response = "Последние обращения:\n\n"
        for appeal in appeals:
            date_str = appeal.created_at.strftime("%d.%m.%Y %H:%M")
            response += f"📅 {date_str}\n{appeal.message}\n\n"
        
        await callback.message.answer(response)
    except Room.DoesNotExist:
        await callback.message.answer("Помещение не найдено")
    
    await callback.answer()

@router.callback_query(F.data.startswith("qrcode_"))
async def send_qr_code(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[1])
    
    try:
        room = Room.get(Room.id == room_id)
        qr_image, url = generate_qr_code(room_id)
        
        # Создаем временный файл
        with open(f"qr_{room_id}.png", "wb") as f:
            f.write(qr_image.getvalue())
        
        # Отправляем изображение
        photo = FSInputFile(f"qr_{room_id}.png")
        await callback.message.answer_photo(
            photo, 
            caption=f"QR-код для помещения: {room.name}\nURL: {url}"
        )
        
        # Удаляем временный файл
        os.remove(f"qr_{room_id}.png")
        
    except Room.DoesNotExist:
        await callback.message.answer("Помещение не найдено")
    
    await callback.answer()

@router.callback_query(F.data.startswith("delete_"))
async def delete_room_start(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[1])
    
    try:
        room = Room.get(Room.id == room_id)
        keyboard = get_delete_confirmation_keyboard(room_id)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Room.DoesNotExist:
        await callback.message.answer("Помещение не найдено")
    
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[2])
    keyboard = get_room_actions_keyboard(room_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    room_id = int(callback.data.split("_")[2])
    
    try:
        room = Room.get(Room.id == room_id)
        room.is_archived = True
        room.save()
        
        await callback.message.edit_text(f"Помещение '{room.name}' удалено")
        await callback.answer("Помещение удалено")
    except Room.DoesNotExist:
        await callback.message.answer("Помещение не найдено")
        await callback.answer()

# Обработчик обращений от пользователей
@router.message(UserStates.waiting_for_appeal)
async def handle_appeal(message: Message, state: FSMContext):
    data = await state.get_data()
    room_id = data.get('room_id')
    
    if not room_id:
        await message.answer("Произошла ошибка. Попробуйте снова.")
        await state.clear()
        return
    
    try:
        room = Room.get(Room.id == room_id)
        
        # Сохраняем обращение
        Appeal.create(
            room=room,
            user_id=message.from_user.id,
            message=message.text
        )
        
        # Отправляем подтверждение пользователю
        await message.answer("Спасибо за обращение, мы уже его передали администрации")
        
        # Пересылаем обращение администратору
        admin_user = User.get(User.user_id == room.admin_id)
        appeal_text = f"Новое обращение по помещению '{room.name}':\n\n{message.text}"
        await bot.send_message(room.admin_id, appeal_text)
        
        await state.clear()
        
    except Room.DoesNotExist:
        await message.answer("Помещение не найдено")
        await state.clear()
    except User.DoesNotExist:
        await message.answer("Администратор не найден")
        await state.clear()

# Инициализация базы данных и запуск бота
async def main():
    create_tables()
    
    # Создаем администратора (замените на ваш user_id)
    admin_user_ids = list(map(int, os.getenv('ADMIN_ID').split()))
    for admin_user_id in admin_user_ids:
        try:
            User.get(User.user_id == admin_user_id)
        except User.DoesNotExist:
            User.create(
                user_id=admin_user_id,
                username="admin",
                first_name="Admin",
                is_admin=True
            )
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

import os
from datetime import datetime
from dotenv import load_dotenv
from peewee import SqliteDatabase, Model, DateTimeField, TextField, CharField, IntegerField, BooleanField, ForeignKeyField

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'database.db')
# Настройка базы данных
db = SqliteDatabase(DB_PATH)


# Модели базы данных
class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    tg_id = IntegerField(unique=True, primary_key=True)


class Role(BaseModel):
    name = CharField()


class UserRole(BaseModel):
    user = ForeignKeyField(User)
    role = ForeignKeyField(Role)


class Room(BaseModel):
    name = CharField()
    creator = ForeignKeyField(User)
    is_archived = BooleanField(default=False)


class Notify(BaseModel):
    'Пользователи которых нужно уведомлять о новых сообщениях'
    user = ForeignKeyField(User)
    room = ForeignKeyField(Room)


class Question(BaseModel):
    room = ForeignKeyField(Room)
    text = CharField()


class Appeal(BaseModel):
    """Обращение"""

    room = ForeignKeyField(Room)
    author = ForeignKeyField(User)
    created_at = DateTimeField(default=datetime.now)
    message = CharField()


# Создание таблиц
def create_tables():

    with db:
        db.create_tables([Room, Appeal, User, Role, UserRole, Notify, Question])

    admin, _ = Role.get_or_create(name='Администратор')
    Role.get_or_create(name='Сотрудник')

    load_dotenv()
    admin_user_ids = list(map(int, os.getenv('ADMIN_ID').split()))
    for admin_user_id in admin_user_ids:
        user, _ = User.get_or_create(tg_id=admin_user_id)
        UserRole.get_or_create(user=user, role=admin)


if __name__ == "__main__":
    create_tables()
from aiogram.fsm.state import State, StatesGroup


# Состояния FSM
class AdminStates(StatesGroup):
    waiting_for_room_name = State()
    waiting_for_delete_confirmation = State()

class UserStates(StatesGroup):
    waiting_for_appeal = State()

class AddNotify(StatesGroup):
    waiting_user_id = State()
    waiting_rooms = State()

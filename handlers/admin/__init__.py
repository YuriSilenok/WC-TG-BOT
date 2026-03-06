from aiogram import Dispatcher

from . import command, notify, room

def add_routers(dp: Dispatcher):
    dp.include_routers(
        notify.router,
        command.ROUTER,
        room.ROUTER,
    )
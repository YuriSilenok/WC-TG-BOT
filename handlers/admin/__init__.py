from aiogram import Dispatcher

from . import command, notify, room, answer


def add_routers(dp: Dispatcher):
    dp.include_routers(
        notify.router,
        command.router,
        room.router,
        answer.router
    )

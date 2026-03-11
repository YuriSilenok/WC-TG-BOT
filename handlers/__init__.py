from aiogram import Dispatcher

from . import admin, employee, user


def add_routers(dp: Dispatcher):
    admin.add_routers(dp)
    dp.include_routers(
        employee.ROUTER,
        user.ROUTER,
    )

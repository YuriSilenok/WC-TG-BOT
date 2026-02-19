from aiogram import Dispatcher

from . import admin, employee, user

def add_routers(dp: Dispatcher):
    dp.include_routers(
        admin.ROUTER,
        employee.ROUTER,
        user.ROUTER,
    )
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from handlers import add_routers
from models import create_tables


load_dotenv()

# Настройка бота
BOT = Bot(token=os.getenv("BOT_TOKEN"))


async def main():
    create_tables()
    dp = Dispatcher()
    add_routers(dp=dp)
    await dp.start_polling(BOT)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database.orm_query import orm_get_reminds_all, orm_get_remind_doctor
from handlers.user_private import user_private_router  # роутер из юзер_приват
from common.bot_cmd_list import private  # список команд

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from middlewares.db import DataBaseSession
from database.engine import create_db, drop_db, session_maker

bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))  # токен ботика


dp = Dispatcher()  # диспатчер
dp.include_routers(user_private_router)  # включение роутера


async def on_startup(bot):
    run_param = False
    if run_param:
        await drop_db()

    await create_db()


async def on_shutdown(bot):
    print("бот прилег")


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)  # скипать сообщения полученные в оффлайне
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())  # кнопка меню
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())  # удалить кнопку меню
    await dp.start_polling(bot)  # полинг сообщений


asyncio.run(main())

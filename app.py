import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

from handlers.user_private import user_private_router  # роутер из юзер_приват
from common.bot_cmd_list import private  # список команд

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())


bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))  # токен ботика
dp = Dispatcher()  # диспатчер
dp.include_routers(user_private_router)  # включение роутера


async def main():
    await bot.delete_webhook(drop_pending_updates=True)  # скипать сообщения полученные в оффлайне
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())  # кнопка меню
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())  # удалить кнопку меню
    await dp.start_polling(bot, allowed_updates=["message, edited_message"])  # полинг сообщений


asyncio.run(main())

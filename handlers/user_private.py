from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, or_f
from aiogram.filters.callback_data import CallbackQuery


from keyboards import replies
from keyboards.replies import MyCallback
user_private_router = Router()


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message):
    name = message.from_user.full_name
    await message.answer(f"Привет, {name}, это заготовка бота напоминалки", reply_markup=replies.start_kb())


@user_private_router.callback_query(MyCallback.filter(F.name == "create"))
async def create_cmd(query: CallbackQuery):
    await query.message.answer("Какое напоминание Вы хотите создать?", reply_markup=replies.create_kb())


@user_private_router.callback_query(MyCallback.filter(F.name == "doctor"))
async def doctor_cmd(query: CallbackQuery):
    await query.message.answer("Запись ко врачу. Пока что здесь ничего нельзя сделать")


@user_private_router.callback_query(MyCallback.filter(F.name == "pills"))
async def doctor_cmd(query: CallbackQuery):
    await query.message.answer("Прием лекарств. Пока что здесь ничего нельзя сделать")

@user_private_router.message(F.text) # магический фильтр ловит текст
async def menu_cmd(message: types.Message):
    await message.answer("Мага фффффффффффф")


from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, or_f, StateFilter
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


from keyboards import replies
from keyboards.replies import MyCallback
user_private_router = Router()


class AddReminder_pills(StatesGroup):
    name = State()
    freq = State()
    extra_inf = State()

    texts = {
        'AddReminder_pills:name': '💊Введите название лекарства',
        'AddReminder_pills:freq': '🗓️Введите частоту приема',
        'AddReminder_pills:extra_inf': 'ℹ️Введите дополнительную информацию',
    }

@user_private_router.message(CommandStart())
async def start(message: types.Message):
    name = message.from_user.full_name
    await message.answer(f"Привет, {name}, это заготовка бота напоминалки", reply_markup=replies.start_kb())


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "cancel"))
@user_private_router.message(StateFilter('*'), F.text.casefold() == "отмена")
async def cancel(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    if cur_state is None:
        return
    await state.clear()
    await query.message.edit_text("❗️<b>Действия отменены</b>", reply_markup=replies.start_kb())
    await query.answer("❗️ Действия отменены ❗️")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "back"))
@user_private_router.message(StateFilter('*'), F.text.casefold() == "назад")
async def back(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()

    if cur_state == AddReminder_pills.name:
        await query.message.edit_text("❗️<b>Предыдущего шага нет</b>\n Введите название или нажмите \"Отмена\"")
        await query.answer("❗️Предыдущего шага нет.️\n Введите название или нажмите \"Отмена\"")
        return

    prev = None
    for step in AddReminder_pills.__all_states__:
        if step == cur_state:
            await state.set_state(prev)
            await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
            if step == AddReminder_pills.freq:
                await query.message.edit_text(
                    f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminder_pills.texts[prev.state]}", reply_markup=replies.cancel_kb()
                )
            else:
                await query.message.edit_text(
                    f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminder_pills.texts[prev.state]}", reply_markup=replies.back_cancel_kb()
                )
            return
        prev = step


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "create"))
async def create(query: CallbackQuery):
    await query.message.answer("Какое напоминание Вы хотите создать?", reply_markup=replies.create_kb())


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "doctor"))
async def doctor(query: CallbackQuery, state: FSMContext):
    await query.message.answer("Запись ко врачу. Пока что здесь ничего нельзя сделать")

''' 
 ХЭНДЛЕРЫ НА ЛЕКАРСТВА
'''
@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "pills"))
async def pills(query: CallbackQuery, state: FSMContext):
    await query.message.answer("💊Введите название лекарства", reply_markup=replies.cancel_kb())
    await state.set_state(AddReminder_pills.name)


@user_private_router.message(AddReminder_pills.name, F.text)
async def pill_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🗓️Введите частоту приема", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminder_pills.freq)


@user_private_router.message(AddReminder_pills.name)
async def pill_name(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите название <i>текстом</i>", reply_markup=replies.cancel_kb())



@user_private_router.message(AddReminder_pills.freq, F.text)
async def pill_freq(message: types.Message, state: FSMContext):
    await state.update_data(freq=message.text)
    await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminder_pills.extra_inf)


@user_private_router.message(AddReminder_pills.freq)
async def pill_name(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите текстом ", reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminder_pills.extra_inf, F.text)
async def pill_extra(message: types.Message, state: FSMContext):
    await state.update_data(extra_inf=message.text)
    await message.answer("✅Напоминание добавлено", reply_markup=replies.start_kb())
    data = await state.get_data()
    await message.answer(str(data))
    await state.clear()





@user_private_router.message(F.text)  # магический фильтр ловит текст
async def stuff(message: types.Message):
    await message.answer("Мага фффффффффффф")


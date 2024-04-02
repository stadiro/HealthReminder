from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, or_f, StateFilter
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


from keyboards import replies
from keyboards.replies import MyCallback
user_private_router = Router()


class AddReminderDoctor(StatesGroup):
    speciality = State()
    name_clinic = State()
    time = State()
    cabinet = State()
    extra_inf_doctor = State()

    texts = {
        'AddReminderDoctor:speciality': '🩺Введите специальность врача',
        'AddReminderDoctor:name_clinic': '🏥Введите название поликлиники',
        'AddReminderDoctor:time': '🕒Укажите день и время приёма',
        'AddReminderDoctor:cabinet': '🚪Укажите кабинет врача',
        'AddReminderDoctor:extra_inf_doctor': 'ℹ️Введите дополнительную информацию\nЗдесь вы можете указать ФИО врача,'
        'адрес поликлиники, и прочую информацию'
    }


class AddReminderPills(StatesGroup):
    name = State()
    freq = State()
    extra_inf = State()

    texts = {
        'AddReminderPills:name': '💊Введите название лекарства',
        'AddReminderPills:freq': '🗓️Введите частоту приема',
        'AddReminderPills:extra_inf': 'ℹ️Введите дополнительную информацию',
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

    if cur_state in AddReminderPills.__all_states__:
        if cur_state == AddReminderPills.name:
            await query.message.edit_text("❗️<b>Предыдущего шага нет</b>\n Введите название или нажмите \"Отмена\"")
            await query.answer("❗️Предыдущего шага нет.️\n Введите название или нажмите \"Отмена\"")
            return

        prev = None
        for step in AddReminderPills.__all_states__:
            if step == cur_state:
                await state.set_state(prev)
                await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                if step == AddReminderPills.freq:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderPills.texts[prev.state]}", reply_markup=replies.cancel_kb()
                    )
                else:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderPills.texts[prev.state]}", reply_markup=replies.back_cancel_kb()
                    )
                return
            prev = step
    else:
        if cur_state == AddReminderDoctor.speciality:
            await query.message.edit_text("❗️<b>Предыдущего шага нет</b>\n Введите название или нажмите \"Отмена\"")
            await query.answer("❗️Предыдущего шага нет.️\n Введите название или нажмите \"Отмена\"")
            return

        prev = None
        for step in AddReminderDoctor.__all_states__:
            if step == cur_state:
                await state.set_state(prev)
                await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                if step == AddReminderDoctor.name_clinic:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderDoctor.texts[prev.state]}",
                        reply_markup=replies.cancel_kb()
                    )
                else:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderDoctor.texts[prev.state]}",
                        reply_markup=replies.back_cancel_kb()
                    )
                return
            prev = step


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "create"))
async def create(query: CallbackQuery):
    await query.message.answer("Какое напоминание Вы хотите создать?", reply_markup=replies.create_kb())


''' 
 ХЭНДЛЕРЫ НА ПРИЁМ
'''


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "doctor"))
async def doctor(query: CallbackQuery, state: FSMContext):
    await query.message.answer("🖋️Запись ко врачу\n 🩺Введите специальность врача", reply_markup=replies.cancel_kb())
    await state.set_state(AddReminderDoctor.speciality)


@user_private_router.message(StateFilter(AddReminderDoctor.speciality), F.text)
async def doctor_spec(message: types.Message, state: FSMContext):
    await state.update_data(speciality=message.text)
    await message.answer("🏥Введите название поликлиники", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderDoctor.name_clinic)


@user_private_router.message(AddReminderDoctor.speciality)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.name_clinic), F.text)
async def doctor_clinic(message: types.Message, state: FSMContext):
    await state.update_data(name_clinic=message.text)
    await message.answer("🕒Укажите день и время приёма", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderDoctor.time)


@user_private_router.message(AddReminderDoctor.name_clinic)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.time), F.text)
async def doctor_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderDoctor.cabinet)


@user_private_router.message(AddReminderDoctor.time)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.cabinet), F.text)
async def doctor_cabinet(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer(
        "ℹ️Введите дополнительную информацию\nЗдесь вы можете указать ФИО врача, адрес поликлиники"
        ", и прочую информацию", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderDoctor.extra_inf_doctor)


@user_private_router.message(AddReminderDoctor.cabinet)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())

@user_private_router.message(StateFilter(AddReminderDoctor.extra_inf_doctor), F.text)
async def doctor_extra(message: types.Message, state: FSMContext):
    await state.update_data(extra_inf_doctor=message.text)
    await message.answer("✅Напоминание добавлено", reply_markup=replies.start_kb())
    data = await state.get_data()
    await message.answer(str(data))
    await state.clear()


@user_private_router.message(AddReminderDoctor.extra_inf_doctor)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


''' 
 ХЭНДЛЕРЫ НА ЛЕКАРСТВА
'''


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "pills"))
async def pills(query: CallbackQuery, state: FSMContext):
    await query.message.answer(
        "🖋️Прием лекарств\n💊Введите название лекарства", reply_markup=replies.cancel_kb())
    await state.set_state(AddReminderPills.name)


@user_private_router.message(AddReminderPills.name, F.text)
async def pill_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🗓️Введите частоту приема", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderPills.freq)


@user_private_router.message(AddReminderPills.name)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите название <i>текстом</i>", reply_markup=replies.cancel_kb())


@user_private_router.message(AddReminderPills.freq, F.text)
async def pill_freq(message: types.Message, state: FSMContext):
    await state.update_data(freq=message.text)
    await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderPills.extra_inf)


@user_private_router.message(AddReminderPills.freq)
async def pill_freq_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите текстом ", reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.extra_inf, F.text)
async def pill_extra(message: types.Message, state: FSMContext):
    await state.update_data(extra_inf=message.text)
    await message.answer("✅Напоминание добавлено", reply_markup=replies.start_kb())
    data = await state.get_data()
    await message.answer(str(data))
    await state.clear()


@user_private_router.message(AddReminderPills.extra_inf)
async def pill_freq_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите текстом ", reply_markup=replies.back_cancel_kb())


@user_private_router.message(F.text)  # магический фильтр ловит текст
async def stuff(message: types.Message):
    await message.answer("Мага фффффффффффф")


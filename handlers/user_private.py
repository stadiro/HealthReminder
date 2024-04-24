from aiogram import F, types, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, time
from inline_cal.common import get_user_locale
from inline_cal.simple_calendar import SimpleCalendar, SimpleCalAct
from inline_cal.schemas import SimpleCalendarCallback

import geopy
from timezonefinder import TimezoneFinder
import pytz


from keyboards import replies
from keyboards.replies import MyCallback
user_private_router = Router()


class AddReminderDoctor(StatesGroup):
    speciality = State()
    name_clinic = State()
    date = State()
    time = State()
    cabinet = State()
    extra_inf_doctor = State()

    texts = {
        'AddReminderDoctor:speciality': '🩺Введите специальность врача',
        'AddReminderDoctor:name_clinic': '🏥Введите название поликлиники',
        'AddReminderDoctor:date': '🗓Укажите день приёма',
        'AddReminderDoctor:time': '🕒Укажите время приёма',
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
async def start(message: types.Message, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state is None:
        name = message.from_user.full_name
        await message.answer(f"Привет, {name}, это заготовка бота напоминалки", reply_markup=replies.start_kb())
    else:
        await message.answer("❗️Вы <b>не можете</b> вернуться в главное меню пока заполняете данные❗️"
                             "\n Продолжите ввод или нажмите \"Отмена\"")


@user_private_router.message(F.text.casefold() == "часовой пояс")
async def get_timezone(message: types.Message):
    city = "Челябинск"
    geo = geopy.geocoders.Nominatim(user_agent="healthtest1bot")
    location = geo.geocode(city)  # преобразует
    if location is None:
        await message.answer("Не удалось найти такой город. "
                                     "Попробуйте написать его название латиницей или указать более крупный город поблизости.")
    else:
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)  # получаем название часового пояса
        tz = pytz.timezone(timezone_str)
        tz_info = datetime.now(tz=tz).strftime("%z")  # получаем смещение часового пояса
        tz_info = tz_info[0:3]+":"+tz_info[3:]  # приводим к формату ±ЧЧ:ММ
        await message.answer("Часовой пояс установлен в %s (%s от GMT)." % (timezone_str, tz_info))
    # здесь должно быть сохранение выбранной строки в БД
        return timezone_str


@user_private_router.callback_query(StateFilter(AddReminderDoctor.date), SimpleCalendarCallback.filter(F.act == SimpleCalAct.cancel))
async def process_selection(query: CallbackQuery, state: FSMContext) -> tuple:
    cur_state = await state.get_state()
    if cur_state is None:
        return
    await state.clear()
    await query.message.edit_text("❗️<b>Действия отменены</b>", reply_markup=replies.start_kb())
    await query.answer("❗️ Действия отменены ❗️")


@user_private_router.callback_query(StateFilter(AddReminderDoctor.date), SimpleCalendarCallback.filter(F.act == SimpleCalAct.back))
async def process_selection(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    prev = None
    for step in AddReminderDoctor.__all_states__:
        if step == cur_state:
            await state.set_state(prev)
            await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
            await query.message.edit_text(
                f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderDoctor.texts[prev.state]}",
                reply_markup=replies.back_cancel_kb()
            )
        prev = step

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
                elif step == AddReminderDoctor.time:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderDoctor.texts[prev.state]}",
                        reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar()
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
    await message.answer("🗓Укажите день приёма",
                         reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
    await state.set_state(AddReminderDoctor.date)


@user_private_router.message(AddReminderDoctor.name_clinic)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.callback_query(StateFilter(AddReminderDoctor.date), SimpleCalendarCallback.filter())
async def doctor_date(query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar(
        locale=await get_user_locale(query.from_user), show_alerts=True
    )
    today_date = datetime.now()
    cur_year = int(today_date.strftime("%Y"))
    cur_month = int(today_date.strftime("%m"))
    cur_day = int(today_date.strftime("%d"))
    calendar.set_dates_range(datetime(cur_year, cur_month, cur_day), datetime(2027, 12, 31))
    selected, chosen_date = await calendar.process_selection(query, callback_data)
    if selected:
        await query.message.edit_text(f'🗓Укажите день приёма\n❗<b>Вы указали {chosen_date.strftime(f"%d.%m.%Y")}</b>')
        await state.update_data(date=chosen_date.strftime(f"%d/%m/%Y"))
        await query.message.answer("🕒Введите время приема\n❗Вводить время нужно в формате ЧЧ:ММ"
                                   "\nНапример, 11:30, 7:30, 0:30")
        await state.set_state(AddReminderDoctor.time)
    return chosen_date


@user_private_router.message(AddReminderDoctor.date)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nВыберите дату <i>на календаре</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.time), F.text)
async def doctor_cabinet(message: types.Message, state: FSMContext):
    message_text = message.text
    if message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)
        else:
            await message.answer("❗<b>Указанное время некорректно</b>\n🕒Введите время заново <b>в формате ЧЧ:ММ</b>"
                                 "\nНапример, 11:30, 7:30, 0:30", reply_markup=replies.back_cancel_kb())

    if message_text[2] == ":":
        hours_minutes = message_text.split(":")
        chosen_hour = int(hours_minutes[0])
        chosen_minute = int(hours_minutes[1])
        state_date = await state.get_data()
        date = state_date['date']
        current_datetime = datetime.now()
        current_time = current_datetime.strftime(f"%H:%M")
        current_date = current_datetime.strftime(f"%d/%m/%Y")
        if (chosen_hour < 0) or (chosen_hour > 24):
            await message.answer("❗<b>Указанное время некорректно</b>"
                                 f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
        elif (chosen_minute < 0) or (chosen_minute > 60):
            await message.answer("❗<b>Указанное время некорректно</b>"
                                 f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
        else:
            pre_time = datetime.strptime(message_text, f"%H:%M")
            chosen_time = pre_time.strftime(f"%H:%M")
            if date == current_date:
                if pre_time.strftime(f"%H") < current_datetime.strftime(f"%H"):
                    await message.answer(
                        f"❗Вы указали <b>некорректное</b> время\n<b>Время должно быть позже {current_time}</b>"
                        f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
                elif pre_time.strftime(f"%H") == current_datetime.strftime(f"%H"):
                    if pre_time.strftime(f"%M") <= current_datetime.strftime(f"%M"):
                        await message.answer(
                            f"❗Вы указали <b>некорректное</b> время\n<b>Время должно быть позже {current_time}</b>"
                            f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
                    else:
                        await state.update_data(time=chosen_time)
                        await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderDoctor.cabinet)
                else:
                    await state.update_data(time=chosen_time)
                    await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
                    await state.set_state(AddReminderDoctor.cabinet)
            else:
                await state.update_data(time=chosen_time)
                await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
                await state.set_state(AddReminderDoctor.cabinet)


@user_private_router.message(AddReminderDoctor.time)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.cabinet), F.text)
async def doctor_cabinet(message: types.Message, state: FSMContext):
    await state.update_data(cabinet=message.text)
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


@user_private_router.message()  # магический фильтр ловит текст
async def stuff(message: types.Message):
    await message.answer("Мага фффффффффффффффф")


from aiogram import F, types, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_doctor_remind, orm_get_reminds, orm_delete_remind, orm_get_remind
from inline_cal.common import get_user_locale
from inline_cal.simple_calendar import SimpleCalendar, SimpleCalAct
from inline_cal.schemas import SimpleCalendarCallback

import geopy
from timezonefinder import TimezoneFinder
import pytz

from keyboards import replies
from keyboards.replies import MyCallback
user_private_router = Router()


class TimeZoneSet(StatesGroup):
    city = State()
    wait_for_remind = State()


class AddReminderDoctor(StatesGroup):
    speciality = State()
    name_clinic = State()
    date = State()
    time = State()
    cabinet = State()
    extra_inf_doctor = State()
    chat_id = State()
    sec_time = State()

    remind_for_change = None

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
    freq_days = State()
    day_start = State()
    freq_per_day = State()
    first_take = State()
    sec_take = State()
    third_take = State()
    four_take = State()
    five_take = State()
    six_take = State()
    extra_inf = State()

    texts = {
        'AddReminderPills:name': '💊Введите название лекарства',
        'AddReminderPills:freq_days': '🗓️Сколько дней нужно принимать лекарство',
        'AddReminderPills:day_start': '🗓️Укажите день начала приема',
        'AddReminderPills:freq_per_day': '🔢Сколько раз в день нужно принимать лекарство',
        'AddReminderPills:first_take': 'Укажите время 1 приема',
        'AddReminderPills:sec_take': 'Укажите время 2 приема',
        'AddReminderPills:third_take': 'Укажите время 3 приема',
        'AddReminderPills:four_take': 'Укажите время 4 приема',
        'AddReminderPills:five_take': 'Укажите время 5 приема',
        'AddReminderPills:six_take': 'Укажите время 6 приема',
        'AddReminderPills:extra_inf': 'ℹ️Введите дополнительную информацию',
    }


@user_private_router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state is None or cur_state == TimeZoneSet.wait_for_remind:
        name = message.from_user.full_name
        await message.answer(f"Привет, {name}, это заготовка бота напоминалки", reply_markup=replies.start_kb())
    else:
        await message.answer("❗️Вы <b>не можете</b> вернуться в главное меню пока заполняете данные❗️"
                             "\n Продолжите ввод или нажмите \"Отмена\"")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "start"))
async def back_to_start(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    await query.message.answer(f"Выберите действие:", reply_markup=replies.start_kb())


@user_private_router.callback_query(MyCallback.filter(F.name == "timezone"))
async def get_city_timezone(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text("Для задания часового пояса укажите ваш город", reply_markup=replies.cancel_kb())
    await state.set_state(TimeZoneSet.city)


@user_private_router.message(StateFilter(TimeZoneSet.city), F.text)
async def get_timezone(message: types.Message, state: FSMContext):
    text = message.text
    if text.isalpha():
        await state.update_data(city=message.text)
        city = message.text
        geo = geopy.geocoders.Nominatim(user_agent="healthtest1bot")
        location = geo.geocode(city)  # преобразует
        if location is None:
            await message.answer("Не удалось найти такой город. "
                                         "Попробуйте написать его название латиницей или указать более крупный город поблизости.",
                                 reply_markup=replies.cancel_kb())
        else:
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)  # получаем название часового пояса
            tz = pytz.timezone(timezone_str)
            tz_info = datetime.now(tz=tz).strftime("%z")  # получаем смещение часового пояса
            tz_info = tz_info[0:3]+":"+tz_info[3:]  # приводим к формату ±ЧЧ:ММ
            await message.answer(f"Часовой пояс установлен в {timezone_str} ({tz_info} от GMT)",
                                 reply_markup=replies.start_kb())
        # здесь должно быть сохранение выбранной строки в БД
            await state.clear()
            return timezone_str
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>")


@user_private_router.message(TimeZoneSet.city)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>")


@user_private_router.message(F.text.casefold() == "текущее время")
async def get_user_time(message: types.Message, state: FSMContext):
    # получаем данные из состояния
    user_data = await state.get_data()
    timezone_str = user_data.get("timezone")
    if timezone_str:
        tz = pytz.timezone(timezone_str)
        user_time = datetime.now(tz=tz)
        await message.answer("Текущее время в вашем часовом поясе: %s" % user_time.strftime("%H:%M:%S"))
    else:
        await message.answer("Часовой пояс не установлен.")


@user_private_router.callback_query(SimpleCalendarCallback.filter(F.act == SimpleCalAct.cancel))
async def process_selection(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    if cur_state is None:
        return
    await state.clear()
    await query.message.edit_text("❗️<b>Действия отменены</b>", reply_markup=replies.start_kb())
    await query.answer("❗️ Действия отменены ❗️")


@user_private_router.callback_query(SimpleCalendarCallback.filter(F.act == SimpleCalAct.back))
async def process_selection(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    if cur_state in AddReminderDoctor.__all_states__:
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
    elif cur_state in AddReminderPills.__all_states__:
        prev = None
        for step in AddReminderPills.__all_states__:
            if step == cur_state:
                await state.set_state(prev)
                await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                await query.message.edit_text(
                    f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderPills.texts[prev.state]}",
                    reply_markup=replies.back_cancel_kb()
                )
            prev = step

@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "cancel"))
async def cancel(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    if cur_state is None:
        return
    await state.clear()
    await query.message.edit_text("❗️<b>Действия отменены</b>", reply_markup=replies.start_kb())
    await query.answer("❗️ Действия отменены ❗️")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "back"))
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
                if cur_state == AddReminderPills.extra_inf:
                    data = await state.get_data()
                    count = data['freq_per_day']
                    takes_time = data['first_take']
                    takes_time.pop()
                    if count == 1:
                        await state.set_state(AddReminderPills.first_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n"
                            f"{AddReminderPills.texts[AddReminderPills.first_take]}", reply_markup=replies.cancel_kb())
                    elif count == 2:
                        await state.set_state(AddReminderPills.sec_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n"
                            f"{AddReminderPills.texts[AddReminderPills.sec_take]}", reply_markup=replies.cancel_kb())
                    elif count == 3:
                        await state.set_state(AddReminderPills.third_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n"
                            f"{AddReminderPills.texts[AddReminderPills.third_take]}", reply_markup=replies.cancel_kb())
                    elif count == 4:
                        await state.set_state(AddReminderPills.four_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n"
                            f"{AddReminderPills.texts[AddReminderPills.four_take]}", reply_markup=replies.cancel_kb())
                    elif count == 5:
                        await state.set_state(AddReminderPills.five_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n"
                            f"{AddReminderPills.texts[AddReminderPills.five_take]}", reply_markup=replies.cancel_kb())
                    elif count == 6:
                        await state.set_state(AddReminderPills.six_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n"
                            f"{AddReminderPills.texts[AddReminderPills.six_take]}", reply_markup=replies.cancel_kb())
                else:
                    await state.set_state(prev)
                    await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                    if step == AddReminderPills.freq_days:
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.cancel_kb())
                    elif step == AddReminderPills.freq_per_day:
                        await query.message.edit_text(f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderPills.texts[prev.state]}",
                                                      reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
                    else:
                        if (cur_state == AddReminderPills.sec_take or cur_state == AddReminderPills.third_take or
                                cur_state == AddReminderPills.four_take or cur_state == AddReminderPills.five_take or
                                cur_state == AddReminderPills.six_take):
                            data = await state.get_data()
                            takes_time = data['first_take']
                            takes_time.pop()
                            await state.update_data(first_take=takes_time)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.back_cancel_kb())
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


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "skip"))
async def cancel(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    cur_state = await state.get_state()
    if cur_state == AddReminderPills.extra_inf:
        await state.update_data(extra_inf=str("Дополнительной информации нет"))
        await query.message.edit_text("❗Ввод дополнительной информации пропущен\n✅Напоминание добавлено",
                                      reply_markup=replies.start_kb())
        data = await state.get_data()
        await query.message.answer(str(data))
        await state.clear()
    elif cur_state == AddReminderDoctor.extra_inf_doctor:
        await state.update_data(extra_inf_doctor=str("Дополнительной информации нет"))
        try:
            await state.update_data(chat_id=query.message.chat.id)
            data = await state.get_data()
            await orm_doctor_remind(session, data)
            await query.message.edit_text("❗Ввод дополнительной информации пропущен\n✅Напоминание добавлено",
                                          reply_markup=replies.start_kb())
            await state.clear()
        except Exception as e:
            await query.message.answer(f"Ошибка: \n{str(e)}\n Информация не может быть загружена в базу данных",
                                       reply_markup=replies.start_kb())
            await state.clear()
    else:
        await query.message.answer("Этого не должно было случиться, что-то пошло не так, укажите значение заново")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "look"))
async def reminds_list(query: CallbackQuery, session: AsyncSession):
    await query.message.delete()
    await query.message.answer("❗Список напоминаний\nДля изменения или удаления напоминания нажмите на кнопку",
                               reply_markup=replies.back_only_for_look_kb())
    await query.answer("❗Список напоминаний\nДля изменения или удаления напоминания нажмите на кнопку")
    for remind in await orm_get_reminds(session):
        if remind.chat_id == query.message.chat.id:
            date = remind.date.strftime(f"%d.%m.%Y")
            time = remind.date.strftime(f"%H:%M")
            await query.message.answer(f"<strong>{remind.speciality}</strong>\n{remind.name_clinic}\n<strong>{date} в "
                                       f"{time}</strong> в кабинете {remind.cabinet}\n{remind.extra_inf_doctor}",
                                       reply_markup=replies.get_btns(btns={
                                           'Изменить 🖋': f'change_{remind.id}',
                                           'Удалить 🚮': f'delete_{remind.id}'}))


@user_private_router.callback_query(F.data.startswith('delete_'))
async def delete_remind(query: types.CallbackQuery, session: AsyncSession):
    remind_id = query.data.split("_")[-1]
    await orm_delete_remind(session, int(remind_id))
    await query.message.answer("❗Напоминание удалено", reply_markup=replies.start_kb()  )
    await query.answer("❗Напоминание удалено")


@user_private_router.callback_query(StateFilter(None), F.data.startswith('change_'))
async def change_remind(query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    remind_id = query.data.split("_")[-1]
    remind_for_change = await orm_get_remind(session, int(remind_id))
    AddReminderDoctor.remind_for_change = remind_for_change
    await query.answer("❗Изменение напоминания")
    await query.message.answer("❗Изменение напоминания\nЧто вы хотите изменить?",
                               reply_markup=replies.get_btns(btns={
                                   '🩺Cпециальность врача': f'speciality_',
                                   '🏥Название поликлиники': f'name_clinic_',
                                   '🗓День приёма': f'date_',
                                   '🕒Время приёма': f'time_',
                                   '🚪Кабинет врача': f'cabinet_',
                                   'ℹ️Дополнительная информация': f'extra_inf_doctor_'})
                               )
    await state.set_state(AddReminderDoctor.sec_time)


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "create"))
async def create(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    await query.message.answer("Какое напоминание Вы хотите создать?", reply_markup=replies.create_kb())


''' 
 ХЭНДЛЕРЫ НА ПРИЁМ -----------------------------------------------------------------------------------------------------
'''


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "doctor"))
async def doctor(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text("🖋️Запись ко врачу\n 🩺Введите специальность врача", reply_markup=replies.cancel_kb())
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
    calendar.set_dates_range(datetime(cur_year, cur_month, cur_day), datetime(cur_year+1, 12, 31))
    selected, chosen_date = await calendar.process_selection(query, callback_data)
    if selected:
        await query.message.edit_text(f'🗓Укажите день приёма\n❗<b>Вы указали {chosen_date.strftime(f"%d.%m.%Y")}</b>')

        await state.update_data(date=chosen_date)  # .strftime(f"%d.%m.%Y")
        await query.message.answer("🕒Введите время приема\n❗Вводить время нужно в формате ЧЧ:ММ"
                                   "\nНапример, 11:30, 7:30, 0:30", reply_markup=replies.back_cancel_kb())
        await state.set_state(AddReminderDoctor.time)
    return chosen_date


@user_private_router.message(AddReminderDoctor.date)
async def doctor_date_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nВыберите дату <i>на календаре</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.time), F.text)
async def doctor_cabinet(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(4)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            state_date = await state.get_data()
            date = state_date['date']
            current_datetime = datetime.now()
            current_time = current_datetime.strftime(f"%H:%M")
            current_date = current_datetime.strftime(f"%d/%m/%Y")
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M').time()
                data = await state.get_data()
                date = data["date"]
                date_and_time = datetime.combine(date, chosen_time)
                first_remind = date_and_time - timedelta(hours=12)
                second_remind = date_and_time - timedelta(hours=2)
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
                            await state.update_data(date=date_and_time)
                            await state.update_data(time=first_remind)
                            await state.update_data(sec_time=second_remind)
                            await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
                            await state.set_state(AddReminderDoctor.cabinet)
                    else:
                        await state.update_data(date=date_and_time)
                        await state.update_data(time=first_remind)
                        await state.update_data(sec_time=second_remind)
                        await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderDoctor.cabinet)
                else:
                    await state.update_data(date=date_and_time)
                    await state.update_data(time=first_remind)
                    await state.update_data(sec_time=second_remind)
                    await message.answer("🚪Укажите кабинет врача", reply_markup=replies.back_cancel_kb())
                    await state.set_state(AddReminderDoctor.cabinet)
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderDoctor.time)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.cabinet), F.text)
async def doctor_cabinet(message: types.Message, state: FSMContext):
    await state.update_data(cabinet=message.text)
    await message.answer(
        "ℹ️Введите дополнительную информацию\nЗдесь вы можете указать ФИО врача, адрес поликлиники"
        ", и прочую информацию", reply_markup=replies.skip_bk_cl_kb())
    await state.set_state(AddReminderDoctor.extra_inf_doctor)


@user_private_router.message(AddReminderDoctor.cabinet)
async def doctor_cabinet_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.extra_inf_doctor), F.text)
async def doctor_extra(message: types.Message, state: FSMContext, session: AsyncSession):

    await state.update_data(extra_inf_doctor=message.text)
    try:
        await state.update_data(chat_id=message.chat.id)
        data = await state.get_data()
        await orm_doctor_remind(session, data)
        await message.answer("✅Напоминание добавлено", reply_markup=replies.start_kb())
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: \n{str(e)}\n Информация не может быть загружена в базу данных",
                             reply_markup=replies.start_kb())
        await state.clear()


@user_private_router.message(AddReminderDoctor.extra_inf_doctor)
async def doctor_extra_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


''' 
 ХЭНДЛЕРЫ НА ЛЕКАРСТВА--------------------------------------------------------------------------------------------------
'''


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "pills"))
async def pills(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "🖋️Прием лекарств\n💊Введите название лекарства", reply_markup=replies.cancel_kb())
    await state.set_state(AddReminderPills.name)


@user_private_router.message(AddReminderPills.name, F.text)
async def pill_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🗓️Сколько дней нужно принимать лекарство", reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderPills.freq_days)


@user_private_router.message(AddReminderPills.name)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите название <i>текстом</i>", reply_markup=replies.cancel_kb())


@user_private_router.message(AddReminderPills.freq_days, F.text)
async def pill_day_start(message: types.Message, state: FSMContext):
    mess = message.text
    if mess.isdigit():
        if 0 < int(mess) <= 7:
            await state.update_data(freq_days=int(mess))
            await message.answer("🗓️Укажите день начала приема",
                                 reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
            await state.set_state(AddReminderPills.day_start)
        if int(mess) > 7 or int(mess) <= 0:
            await message.answer("❗Количество дней <b>не может</b> быть больше 7 или меньше 1"
                                 "\nУкажите подходящее количество", reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите количество <b>целым положительным числом</b>",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.freq_days)
async def pill_day_start_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите количество <b>целым положительным числом",
                         reply_markup=replies.cancel_kb())


@user_private_router.callback_query(StateFilter(AddReminderPills.day_start), SimpleCalendarCallback.filter())
async def pill_day_start(query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar(
        locale=await get_user_locale(query.from_user), show_alerts=True
    )
    today_date = datetime.now()
    cur_year = int(today_date.strftime("%Y"))
    cur_month = int(today_date.strftime("%m"))
    cur_day = int(today_date.strftime("%d"))
    calendar.set_dates_range(datetime(cur_year, cur_month, cur_day), datetime(cur_year+1, 12, 31))
    selected, chosen_date = await calendar.process_selection(query, callback_data)
    if selected:
        await query.message.edit_text(f'🗓️Укажите день начала приема\n❗<b>Вы указали {chosen_date.strftime(f"%d.%m.%Y")}</b>')
        await state.update_data(day_start=chosen_date)
        await query.message.answer("🔢Сколько раз в день нужно принимать лекарство",
                                   reply_markup=replies.back_cancel_kb())
        await state.set_state(AddReminderPills.freq_per_day)
    return chosen_date


@user_private_router.message(AddReminderPills.day_start)
async def pill_day_start_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nВыберите дату <i>на календаре</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.freq_per_day, F.text)
async def pill_freq_per_day(message: types.Message, state: FSMContext):
    mess = message.text
    if mess.isdigit():
        if 6 >= int(mess) > 0:
            await state.update_data(freq_per_day=int(message.text))
            await message.answer("Укажите время 1 приема\n❗Вводить время нужно в формате ЧЧ:ММ"
                                 "\nНапример, 11:30, 7:30, 0:30", reply_markup=replies.back_cancel_kb())
            await state.set_state(AddReminderPills.first_take)
        if int(mess) > 6 or int(mess) <= 0:
            await message.answer("❗Количество приемов в день <b>не может</b> быть больше 6 или меньше 1"
                                 "\nУкажите подходящее количество", reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите количество <b>целым положительным числом</b>",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.freq_per_day)
async def pill_freq_per_day_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>целым положительным числом</b>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.first_take, F.text)
async def pill_first_take(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(4)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                takes_time = []
                takes_time.append(chosen_time)
                await state.update_data(first_take=takes_time)
                data = await state.get_data()
                count = data['freq_per_day']
                if count > 1:
                    await message.answer("Укажите время 2 приема", reply_markup=replies.back_cancel_kb())
                    await state.set_state(AddReminderPills.sec_take)
                else:
                    await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.skip_bk_cl_kb())
                    await state.set_state(AddReminderPills.extra_inf)
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.first_take)
async def pill_first_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ", reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.sec_take, F.text)
async def pill_sec_take(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(4)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                data = await state.get_data()
                count = data['freq_per_day']
                takes_time = data['first_take']
                hit_counter = 0
                for i in range(len(takes_time)):
                    if takes_time[i] == chosen_time:
                        hit_counter += 1
                if hit_counter == 0:
                    takes_time.append(chosen_time)
                    await message.answer(f"{takes_time}")
                    await state.update_data(first_take=takes_time)
                    if count > 2:
                        await message.answer("Укажите время 3 приема", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.third_take)
                    else:
                        await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приёма лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\nУкажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b>",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.sec_take)
async def pill_sec_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.third_take, F.text)
async def pill_sec_take(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(4)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                data = await state.get_data()
                count = data['freq_per_day']
                takes_time = data['first_take']
                hit_counter = 0
                for i in range(len(takes_time)):
                    if takes_time[i] == chosen_time:
                        hit_counter += 1
                if hit_counter == 0:
                    takes_time.append(chosen_time)
                    await message.answer(f"{takes_time}")
                    await state.update_data(first_take=takes_time)
                    if count > 3:
                        await message.answer("Укажите время 4 приема", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.four_take)
                    else:
                        await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приёма лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\nУкажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.third_take)
async def pill_sec_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.four_take, F.text)
async def pill_sec_take(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(4)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                data = await state.get_data()
                count = data['freq_per_day']
                takes_time = data['first_take']
                hit_counter = 0
                for i in range(len(takes_time)):
                    if takes_time[i] == chosen_time:
                        hit_counter += 1
                if hit_counter == 0:
                    takes_time.append(chosen_time)
                    await state.update_data(first_take=takes_time)
                    await message.answer(f"{takes_time}")
                    if count > 4:
                        await message.answer("Укажите время 5 приема", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.five_take)
                    else:
                        await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приёма лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\nУкажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.four_take)
async def pill_sec_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.five_take, F.text)
async def pill_sec_take(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(5)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                data = await state.get_data()
                count = data['freq_per_day']
                takes_time = data['first_take']
                hit_counter = 0
                for i in range(len(takes_time)):
                    if takes_time[i] == chosen_time:
                        hit_counter += 1
                if hit_counter == 0:
                    takes_time.append(chosen_time)
                    await state.update_data(first_take=takes_time)
                    await message.answer(f"{takes_time}")
                    if count > 5:
                        await message.answer("Укажите время 6 приема", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.six_take)
                    else:
                        await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приёма лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\nУкажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.five_take)
async def pill_sec_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.six_take, F.text)
async def pill_sec_take(message: types.Message, state: FSMContext):
    message_text = message.text
    if len(message_text) <= 2:
        message_text = message_text.zfill(5)
    elif message_text[2] != ":":
        if message_text[1] == ":":
            message_text = message_text.zfill(5)

    if message_text[:2].isdigit() and message_text[3:5].isdigit() and message_text[2] == ":":
        hours_minutes = message_text.split(":")
        if len(hours_minutes[1]) == 2:
            chosen_hour = int(hours_minutes[0])
            chosen_minute = int(hours_minutes[1])
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒Введите время заново", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                data = await state.get_data()
                takes_time = data['first_take']
                hit_counter = 0
                for i in range(len(takes_time)):
                    if takes_time[i] == chosen_time:
                        hit_counter += 1
                if hit_counter == 0:
                    takes_time.append(chosen_time)
                    await state.update_data(first_take=takes_time)
                    await message.answer(f"{takes_time}")
                    await message.answer("ℹ️Введите дополнительную информацию", reply_markup=replies.skip_bk_cl_kb())
                    await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приёма лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\nУкажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.six_take)
async def pill_sec_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.extra_inf, F.text)
async def pill_extra(message: types.Message, state: FSMContext):
    await state.update_data(extra_inf=message.text)
    await message.answer("✅Напоминание добавлено", reply_markup=replies.start_kb())
    data = await state.get_data()
    await message.answer(str(data))
    await state.clear()


@user_private_router.message(AddReminderPills.extra_inf)
async def pill_extra_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите текстом ", reply_markup=replies.back_cancel_kb())


@user_private_router.message()  # магический фильтр ловит текст
async def stuff(message: types.Message):
    await message.answer("Мага фффффффффффффффф")


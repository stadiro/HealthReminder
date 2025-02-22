import asyncio
import os

from aiogram import F, types, Router, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from dotenv import find_dotenv, load_dotenv
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserTimezone
from database.orm_query import (orm_doctor_remind, orm_get_reminds_doctor, orm_delete_remind,
                                orm_pills_remind, orm_get_reminds_pill, orm_get_reminds_all, orm_get_remind_doctor,
                                orm_get_remind_pill)
from inline_cal.common import get_user_locale
from inline_cal.simple_calendar import SimpleCalendar, SimpleCalAct
from inline_cal.schemas import SimpleCalendarCallback

from keyboards import replies
from keyboards.replies import MyCallback
load_dotenv(find_dotenv())
bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))  # токен ботика
user_private_router = Router()
executor = ThreadPoolExecutor()


class AddReminderDoctor(StatesGroup):
    speciality = State()
    name_clinic = State()
    date = State()
    time = State()
    cabinet = State()
    extra_inf_doctor = State()
    chat_id = State()
    sec_time = State()

    texts = {
        'AddReminderDoctor:speciality': '🩺<b>Введите специальность врача</b>',
        'AddReminderDoctor:name_clinic': '🏥<b>Введите название поликлиники</b>',
        'AddReminderDoctor:date': '🗓<b>Укажите день приема</b>',
        'AddReminderDoctor:time': '🕒<b>Укажите время приема</b>',
        'AddReminderDoctor:cabinet': '🚪<b>Укажите кабинет врача</b>',
        'AddReminderDoctor:extra_inf_doctor': 'ℹ️<b>Введите дополнительную информацию</b>\nЗдесь вы можете указать ФИО'
                                              ' врача, адрес поликлиники, и прочую информацию'
    }


class AddReminderPills(StatesGroup):
    name = State()
    freq_days = State()
    periodicity = State()
    interval = State()
    day_start = State()
    freq_per_day = State()
    first_take = State()
    sec_take = State()
    third_take = State()
    four_take = State()
    five_take = State()
    six_take = State()
    extra_inf = State()
    chat_id = State()

    texts = {
        'AddReminderPills:name': '💊<b>Введите название лекарства</b>',
        'AddReminderPills:freq_days': '🗓️<b>Сколько дней нужно принимать лекарство</b>',
        'AddReminderPills:periodicity': '📅<b>Как часто нужно принимать лекарство?</b>',
        'AddReminderPills:interval': '🗓️<b>Какой интервал в днях между днями приема лекарства?</b>',
        'AddReminderPills:day_start': '🗓️<b>Укажите день начала приема</b>',
        'AddReminderPills:freq_per_day': '🔢<b>Сколько раз в день нужно принимать лекарство</b>',
        'AddReminderPills:first_take': '<b>Укажите время 1 приема</b>',
        'AddReminderPills:sec_take': '<b>Укажите время 2 приема</b>',
        'AddReminderPills:third_take': '<b>Укажите время 3 приема</b>',
        'AddReminderPills:four_take': '<b>Укажите время 4 приема</b>',
        'AddReminderPills:five_take': '<b>Укажите время 5 приема</b>',
        'AddReminderPills:six_take': '<b>Укажите время 6 приема</b>',
        'AddReminderPills:extra_inf': 'ℹ️<b>Введите дополнительную информацию</b>\n\n'
                                         'Здесь вы можете указать дозировку препарата, то, как его принимать и прочую'
                                         ' информацию'
    }


async def convert_from_yekaterinburg(session, chat_id, dt):
    """Конвертирует datetime из Asia/Yekaterinburg в часовой пояс пользователя"""

    # Получаем часовой пояс пользователя
    result = await session.execute(select(UserTimezone).where(UserTimezone.chat_id == chat_id))
    user_timezone = result.scalars().first()

    # Если часовой пояс найден — используем его, иначе берём Europe/Moscow
    user_tz = user_timezone.timezone if user_timezone else "Europe/Moscow"

    # Если datetime наивный (без tzinfo) — добавляем часовой пояс Екатеринбурга
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Yekaterinburg"))

    # Конвертируем в часовой пояс пользователя
    return dt.astimezone(ZoneInfo(user_tz))



async def send_current(bot: Bot, session: AsyncSession):
    print('start stream....')

    while True:
        try:
            for remind in await orm_get_reminds_all(session):
                current_datetime = datetime.now().replace(second=0, microsecond=0)
                if remind.date_time == current_datetime:
                    if remind.pills_or_doctor == 0:
                        for dc_rm in await orm_get_remind_doctor(session, int(remind.id)):
                            ch_id = dc_rm.chat_id
                            dc_rm_time = await convert_from_yekaterinburg(session, ch_id, dc_rm.date)
                            date = dc_rm_time.strftime(f"%d.%m.%Y")
                            time = dc_rm_time.strftime(f"%H:%M")
                            if remind.date_time == dc_rm.first_remind:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Через 24 часа прием у врача"
                                       f"</strong>🔔\n\n🩺Врач:<b> {dc_rm.speciality}</b>\n🏥Поликлиника:"
                                       f" {dc_rm.name_clinic}\n<b>🗓{date} в {time}</b> в кабинете "
                                       f"<b>{dc_rm.cabinet}</b>\nℹ️Дополнительная информация: {dc_rm.extra_inf_doctor}")
                            elif remind.date_time == dc_rm.second_remind:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Через 1 час прием у врача"
                                       f"</strong>🔔\n\n🩺Врач:<b> {dc_rm.speciality}</b>\n🏥Поликлиника:"
                                       f" {dc_rm.name_clinic}\n<b>🗓{date} в {time}</b> в кабинете "
                                       f"<b>{dc_rm.cabinet}</b>\nℹ️Дополнительная информация: {dc_rm.extra_inf_doctor}")
                            elif remind.date_time == dc_rm.date:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Сейчас прием у врача"
                                       f"</strong>🔔\n\n🩺Врач:<b> {dc_rm.speciality}</b>\n🏥Поликлиника:"
                                       f" {dc_rm.name_clinic}\n<b>🗓{date} в {time}</b> в кабинете "
                                       f"<b>{dc_rm.cabinet}</b>\nℹ️Дополнительная информация: {dc_rm.extra_inf_doctor}")
                                await orm_delete_remind(session, int(dc_rm.id))
                    elif remind.pills_or_doctor == 1:
                        for pl_rm in await orm_get_remind_pill(session, int(remind.id)):
                            ch_id = pl_rm.chat_id
                            date = pl_rm.day_start.strftime(f"%d.%m.%Y")
                            if pl_rm.freq_per_day >= 1:
                                time1 = pl_rm.first_take.strftime(f"%H:%M")
                                if pl_rm.freq_per_day >= 2:
                                    time2 = pl_rm.sec_take.strftime(f"%H:%M")
                                    if pl_rm.freq_per_day >= 3:
                                        time3 = pl_rm.third_take.strftime(f"%H:%M")
                                        if pl_rm.freq_per_day >= 4:
                                            time4 = pl_rm.four_take.strftime(f"%H:%M")
                                            if pl_rm.freq_per_day >= 5:
                                                time5 = pl_rm.five_take.strftime(f"%H:%M")
                                                if pl_rm.freq_per_day >= 6:
                                                    time6 = pl_rm.six_take.strftime(f"%H:%M")
                            if pl_rm.freq_per_day == 1:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Пора принимать лекарство🔔\n\n"
                                           f"💊Препарат: {pl_rm.name}\n🗓Прием {pl_rm.freq_per_day} раз в день"
                                           f" на протяжении {pl_rm.freq_days} дней начиная с {date}</strong>"
                                           f"\n⏰Время приема:\n1. {time1}"
                                           f"\nℹ️Дополнительная информация: {pl_rm.extra_inf}")
                            elif pl_rm.freq_per_day == 2:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Пора принимать лекарство🔔\n\n"
                                           f"💊Препарат: {pl_rm.name}\n🗓Прием {pl_rm.freq_per_day} раз в день"
                                           f" на протяжении {pl_rm.freq_days} дней начиная с {date}</strong>"
                                           f"\n⏰Время приема:\n1. {time1}\n2. {time2}"
                                           f"\nℹ️Дополнительная информация: {pl_rm.extra_inf}")
                            elif pl_rm.freq_per_day == 3:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Пора принимать лекарство🔔\n\n"
                                           f"💊Препарат: {pl_rm.name}\n🗓Прием {pl_rm.freq_per_day} раз в день"
                                           f" на протяжении {pl_rm.freq_days} дней начиная с {date}</strong>"
                                           f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}"
                                           f"\nℹ️Дополнительная информация: {pl_rm.extra_inf}")
                            elif pl_rm.freq_per_day == 4:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Пора принимать лекарство🔔\n\n"
                                           f"💊Препарат: {pl_rm.name}\n🗓Прием {pl_rm.freq_per_day} раз в день"
                                           f" на протяжении {pl_rm.freq_days} дней начиная с {date}</strong>"
                                           f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}\n4. {time4}"
                                           f"\nℹ️Дополнительная информация: {pl_rm.extra_inf}")
                            elif pl_rm.freq_per_day == 5:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Пора принимать лекарство🔔\n\n"
                                           f"💊Препарат: {pl_rm.name}\n🗓Прием {pl_rm.freq_per_day} раз в день"
                                           f" на протяжении {pl_rm.freq_days} дней начиная с {date}</strong>"
                                           f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}\n4. {time4}\n5. {time5}"
                                           f"\nℹ️Дополнительная информация: {pl_rm.extra_inf}")
                            elif pl_rm.freq_per_day == 6:
                                await bot.send_message(chat_id=int(ch_id), text=f"🔔<strong>Пора принимать лекарство🔔\n\n"
                                           f"💊Препарат: {pl_rm.name}\n🗓Прием {pl_rm.freq_per_day} раз в день"
                                           f" на протяжении {pl_rm.freq_days} дней начиная с {date}</strong>"
                                           f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}\n4. {time4}\n5. {time5}\n6. {time6}"
                                           f"\nℹ️Дополнительная информация: {pl_rm.extra_inf}")
                            if remind.is_it_last == 1:
                                await orm_delete_remind(session, int(pl_rm.id))
            await asyncio.sleep(60)

        except Exception as e:
            print(e)
            continue


@user_private_router.message(Command("stream"))
async def start_stream(message: types.Message, session: AsyncSession):
    asyncio.create_task(send_current(bot, session))
    await message.answer("good.")


async def get_timezone(city_name: str) -> str:
    loop = asyncio.get_running_loop()
    try:
        geolocator = Nominatim(user_agent="timezone_bot")
        # Определяем координаты города (запускаем синхронный вызов в пуле потоков)
        location = await loop.run_in_executor(executor, lambda: geolocator.geocode(city_name))
        if not location:
            return None

        tf = TimezoneFinder()
        # Определяем часовой пояс по координатам
        tz = await loop.run_in_executor(
            executor, lambda: tf.timezone_at(lng=location.longitude, lat=location.latitude)
        )
        return tz
    except Exception as e:
        return None

# Хэндлер для команды /start
@user_private_router.message(CommandStart())
async def start(message: types.Message, state: FSMContext, session: AsyncSession):
    cur_state = await state.get_state()
    if cur_state is not None:
        await message.answer(
            "❗️Вы <b>не можете</b> вернуться в главное меню пока заполняете данные❗️\n"
            "Продолжите ввод или нажмите \"Отмена\""
        )
        return

    chat_id = str(message.chat.id)
    # Проверяем, задан ли часовой пояс для этого пользователя
    result = await session.execute(select(UserTimezone).where(UserTimezone.chat_id == chat_id))
    user_timezone = result.scalars().first()
    name = message.from_user.full_name

    if not user_timezone:
        await message.answer(
            f"👋Привет, {name}!\n\n❕Для начала работы введите название вашего города для определения часового пояса"
        )
        await state.set_state("waiting_for_timezone")
        return

    # Если часовой пояс уже задан – выводим стандартное приветствие
    await message.answer(
        f"👋Привет, {name}!\n\n🤖Это - бот, напоминающий о приеме лекарств или записи к врачу",
        reply_markup=replies.start_kb()
    )


# Хэндлер для обработки ввода города (определение часового пояса)
@user_private_router.message(StateFilter("waiting_for_timezone"))
async def process_timezone(message: types.Message, state: FSMContext, session: AsyncSession):
    city_name = message.text.strip()
    tz = await get_timezone(city_name)
    if not tz:
        await message.answer("Не удалось определить часовой пояс по введенному названию города. Пожалуйста, попробуйте еще раз:")
        return

    chat_id = str(message.chat.id)
    # Проверяем, существует ли уже запись для данного chat_id
    result = await session.execute(select(UserTimezone).where(UserTimezone.chat_id == chat_id))
    existing_record = result.scalars().first()
    if existing_record:
        # Удаляем существующую запись
        await session.delete(existing_record)
        await session.commit()

    # Сохраняем новый часовой пояс в базе данных
    new_user_tz = UserTimezone(chat_id=chat_id, timezone=tz)
    session.add(new_user_tz)
    await session.commit()

    # После определения часового пояса выводим стандартное приветствие
    name = message.from_user.full_name
    await message.answer(
        f"🕰Ваш часовой пояс установлен: {tz}\n\n🤖Это - бот, напоминающий о приеме лекарств или записи к врачу",
        reply_markup=replies.start_kb()
    )
    await state.clear()


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "timezone_new"))
async def change_timezone(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    chat_id = str(query.from_user.id)
    result = await session.execute(select(UserTimezone.timezone).where(UserTimezone.chat_id == chat_id))
    user_tz = result.scalar()
    await query.message.delete()
    await query.message.answer(f"🕰Ваш часовой пояс: {user_tz}\n\n❕Для изменения часового пояса введите ваш город",
                                   reply_markup=replies.back_only_for_look_kb())
    await state.set_state("waiting_for_timezone")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "start"))
async def back_to_start(query: CallbackQuery, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state == "waiting_for_timezone":
        await state.clear()
        cur_state = None
    if cur_state is None:
        await query.message.delete()
        await query.message.answer(f"❕Выберите действие:", reply_markup=replies.start_kb())
    else:
        await query.answer("❗️Вы не можете выполнить действие пока заполняете данные❗️")


@user_private_router.callback_query(SimpleCalendarCallback.filter(F.act == SimpleCalAct.cancel))
async def calendar_cancel(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    if cur_state is None:
        return
    await state.clear()
    await query.message.edit_text("❗️<b>Действия отменены</b>", reply_markup=replies.start_kb())
    await query.answer("❗️ Действия отменены ❗️")


@user_private_router.callback_query(SimpleCalendarCallback.filter(F.act == SimpleCalAct.back))
async def calendar_back(query: CallbackQuery, state: FSMContext) -> None:
    cur_state = await state.get_state()
    if cur_state in AddReminderDoctor.__all_states__:
        prev = None
        for step in AddReminderDoctor.__all_states__:
            if step == cur_state:
                await state.set_state(prev)
                await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                await query.message.edit_text(
                    f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderDoctor.texts[prev.state]}",
                    reply_markup=replies.back_cancel_kb()
                )
            prev = step
    elif cur_state in AddReminderPills.__all_states__:
        data = await state.get_data()
        periodicity = data.get("periodicity")
        freq_days = int(data.get("freq_days", 0))  # Если данных нет, то по умолчанию будет 0

        # Логика определения предыдущего шага
        if periodicity == 2:
            prev_state = AddReminderPills.interval
            await state.set_state(prev_state)
            await query.message.edit_text(
                f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev_state.state]}",
                reply_markup=replies.back_cancel_kb()
            )
        elif freq_days == 1:
            prev_state = AddReminderPills.freq_days
            await state.set_state(prev_state)
            await query.message.edit_text(
                f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev_state.state]}",
                reply_markup=replies.back_cancel_kb()
            )
        elif periodicity == 0 or periodicity == 1:
            prev_state = AddReminderPills.periodicity
            await state.set_state(prev_state)
            await query.message.edit_text(
                f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev_state.state]}",
                reply_markup=replies.repeatability_kb()
            )
        '''else:
            prev_state = None
            for step in AddReminderPills.__all_states__:
                if step == cur_state:
                    break
                prev_state = step

        # Если найден предыдущий шаг, устанавливаем его
        if prev_state:
            await state.set_state(prev_state)
            await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
            await query.message.edit_text(
                f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev_state.state]}",
                reply_markup=replies.repeatability_kb()
            )'''


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
    '''if cur_state in AddReminderPills.__all_states__:
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
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.first_take]}", reply_markup=replies.cancel_kb())
                    elif count == 2:
                        await state.set_state(AddReminderPills.sec_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.sec_take]}", reply_markup=replies.cancel_kb())
                    elif count == 3:
                        await state.set_state(AddReminderPills.third_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.third_take]}", reply_markup=replies.cancel_kb())
                    elif count == 4:
                        await state.set_state(AddReminderPills.four_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.four_take]}", reply_markup=replies.cancel_kb())
                    elif count == 5:
                        await state.set_state(AddReminderPills.five_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.five_take]}", reply_markup=replies.cancel_kb())
                    elif count == 6:
                        await state.set_state(AddReminderPills.six_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.six_take]}", reply_markup=replies.cancel_kb())
                else:
                    await state.set_state(prev)
                    await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                    if step == AddReminderPills.freq_days:
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.cancel_kb())
                    elif step == AddReminderPills.freq_per_day:
                        await query.message.edit_text(f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
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
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.back_cancel_kb())
                    return
            prev = step'''
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
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.first_take]}", reply_markup=replies.cancel_kb())
                    elif count == 2:
                        await state.set_state(AddReminderPills.sec_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.sec_take]}", reply_markup=replies.cancel_kb())
                    elif count == 3:
                        await state.set_state(AddReminderPills.third_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.third_take]}", reply_markup=replies.cancel_kb())
                    elif count == 4:
                        await state.set_state(AddReminderPills.four_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.four_take]}", reply_markup=replies.cancel_kb())
                    elif count == 5:
                        await state.set_state(AddReminderPills.five_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.five_take]}", reply_markup=replies.cancel_kb())
                    elif count == 6:
                        await state.set_state(AddReminderPills.six_take)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n"
                            f"{AddReminderPills.texts[AddReminderPills.six_take]}", reply_markup=replies.cancel_kb())
                else:
                    await state.set_state(prev)
                    await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                    if step == AddReminderPills.freq_days:
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.cancel_kb())
                    elif step == AddReminderPills.freq_per_day:
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
                    elif step == AddReminderPills.interval:
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.repeatability_kb())
                    elif step == AddReminderPills.day_start:
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.repeatability_kb())
                    else:
                        if (cur_state == AddReminderPills.sec_take or cur_state == AddReminderPills.third_take or
                                cur_state == AddReminderPills.four_take or cur_state == AddReminderPills.five_take or
                                cur_state == AddReminderPills.six_take):
                            data = await state.get_data()
                            takes_time = data['first_take']
                            takes_time.pop()
                            await state.update_data(first_take=takes_time)
                        await query.message.edit_text(
                            f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderPills.texts[prev.state]}",
                            reply_markup=replies.back_cancel_kb())
                    return
            prev = step
    else:
        if cur_state == AddReminderDoctor.speciality:
            await query.message.edit_text("❗️<b>Предыдущего шага нет</b>\n Введите специальность или нажмите \"Отмена\"")
            await query.answer("❗️Предыдущего шага нет.️\n Введите специальность или нажмите \"Отмена\"")
            return

        prev = None
        for step in AddReminderDoctor.__all_states__:
            if step == cur_state:
                await state.set_state(prev)
                await query.answer("❗️ Вы вернулись к прошлому шагу ❗️")
                if step == AddReminderDoctor.name_clinic:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderDoctor.texts[prev.state]}",
                        reply_markup=replies.cancel_kb()
                    )
                elif step == AddReminderDoctor.time:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderDoctor.texts[prev.state]}",
                        reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar()
                    )
                else:
                    await query.message.edit_text(
                        f"❗️<b>Вы вернулись к прошлому шагу</b>\n\n{AddReminderDoctor.texts[prev.state]}",
                        reply_markup=replies.back_cancel_kb()
                    )
                return
            prev = step


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "skip"))
async def skip(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    cur_state = await state.get_state()
    if cur_state == AddReminderPills.extra_inf:
        await state.update_data(extra_inf=str("Дополнительной информации нет"))
        try:
            await state.update_data(chat_id=str(query.message.chat.id))
            data = await state.get_data()
            takes_time = data["first_take"]
            takes_time = [dt + timedelta(days=2) for dt in takes_time]
            if data["freq_per_day"] >= 1:
                await state.update_data(first_take=takes_time[0])
                if data["freq_per_day"] >= 2:
                    await state.update_data(sec_take=takes_time[1])
                    if data["freq_per_day"] >= 3:
                        await state.update_data(third_take=takes_time[2])
                        if data["freq_per_day"] >= 4:
                            await state.update_data(four_take=takes_time[3])
                            if data["freq_per_day"] >= 5:
                                await state.update_data(five_take=takes_time[4])
                                if data["freq_per_day"] == 6:
                                    await state.update_data(six_take=takes_time[5])
                                else:
                                    await state.update_data(six_take=None)
                            else:
                                await state.update_data(five_take=None)
                                await state.update_data(six_take=None)
                        else:
                            await state.update_data(four_take=None)
                            await state.update_data(five_take=None)
                            await state.update_data(six_take=None)
                    else:
                        await state.update_data(third_take=None)
                        await state.update_data(four_take=None)
                        await state.update_data(five_take=None)
                        await state.update_data(six_take=None)
                else:
                    await state.update_data(sec_take=None)
                    await state.update_data(third_take=None)
                    await state.update_data(four_take=None)
                    await state.update_data(five_take=None)
                    await state.update_data(six_take=None)
            data1 = await state.get_data()
            await orm_pills_remind(session, data1)
            await query.message.answer("✅Напоминание добавлено\n\n🔔Напоминания будут приходить в указанное время\n\n"
                             "❕Уведомления приходят по (UTC/GMT +05:00) Asia/Yekaterinburg",
                                 reply_markup=replies.start_kb())
            await state.clear()
        except Exception as e:
            await query.message.answer(f"Ошибка: \n{str(e)}\n Информация не может быть загружена в базу данных",
                                 reply_markup=replies.start_kb())
            await state.clear()
    elif cur_state == AddReminderDoctor.extra_inf_doctor:
        await state.update_data(extra_inf_doctor=str("Дополнительной информации нет"))
        try:
            await state.update_data(chat_id=str(query.message.chat.id))
            data = await state.get_data()
            await orm_doctor_remind(session, data)
            await query.message.edit_text("❗Ввод дополнительной информации пропущен\n\n✅<b>Напоминание добавлено"
                                          "</b>\n\n🔔Вам придет уведомление за 24 часа, за 1 час и в момент"
                                          " приема",
                                          reply_markup=replies.start_kb())
            await state.clear()
        except Exception as e:
            await query.message.answer(f"Ошибка: \n{str(e)}\n Информация не может быть загружена в базу данных",
                                       reply_markup=replies.start_kb())
            await state.clear()
    else:
        await query.message.answer("❗Вы не находитесь в стадии указания дополнительной информации")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "look"))
async def reminds_list(query: CallbackQuery, session: AsyncSession):
    await query.message.delete()
    await query.answer("📋Список напоминаний⬆\n\n❕Для изменения или удаления напоминания нажмите на кнопку")

    doctor_reminds = await orm_get_reminds_doctor(session)
    pill_reminds = await orm_get_reminds_pill(session)

    if not doctor_reminds and not pill_reminds:
        await query.message.answer("❗У Вас нет напоминаний", reply_markup=replies.no_reminders_kb())
        await query.answer("❗У Вас нет напоминаний")
        return
    else:
        for remind in await orm_get_reminds_doctor(session):
            if int(remind.chat_id) == query.message.chat.id:
                dt_user = await convert_from_yekaterinburg(session, remind.chat_id, remind.date)
                date = dt_user.strftime(f"%d.%m.%Y")
                time = dt_user.strftime(f"%H:%M")
                await query.message.answer(f"🩺Врач:<b> {remind.speciality}</b>\n🏥Поликлиника:"
                                           f" {remind.name_clinic}\n<b>🗓{date} в {time}</b> в кабинете "
                                           f"<b>{remind.cabinet}</b>\nℹ️Дополнительная информация: {remind.extra_inf_doctor}",
                                           reply_markup=replies.get_btns(btns={
                                               'Удалить 🚮': f'delete_{remind.id}'}))
        for remind in await orm_get_reminds_pill(session):
            if int(remind.chat_id) == query.message.chat.id:
                date = remind.day_start.strftime(f"%d.%m.%Y")
                if remind.freq_per_day >= 1:
                    time1 = remind.first_take.strftime(f"%H:%M")
                    if remind.freq_per_day >= 2:
                        time2 = remind.sec_take.strftime(f"%H:%M")
                        if remind.freq_per_day >= 3:
                            time3 = remind.third_take.strftime(f"%H:%M")
                            if remind.freq_per_day >= 4:
                                time4 = remind.four_take.strftime(f"%H:%M")
                                if remind.freq_per_day >= 5:
                                    time5 = remind.five_take.strftime(f"%H:%M")
                                    if remind.freq_per_day >= 6:
                                        time6 = remind.six_take.strftime(f"%H:%M")
                if remind.freq_per_day == 1:
                    await query.message.answer(f"<strong>💊Препарат: {remind.name}\n📋Прием {remind.freq_per_day} раз в день"
                                               f" на протяжении {remind.freq_days} дней начиная с {date}</strong>"
                                               f"\n⏰Время приема:\n1. {time1}\nℹ️Дополнительная информация: {remind.extra_inf}",
                                               reply_markup=replies.get_btns(btns={
                                                   'Удалить 🚮': f'delete_{remind.id}'}))
                elif remind.freq_per_day == 2:
                    await query.message.answer(f"<strong>💊Препарат: {remind.name}\n🗓Прием {remind.freq_per_day} раз в день"
                                               f" на протяжении {remind.freq_days} дней начиная с {date}</strong>"
                                               f"\n⏰Время приема:\n1. {time1}\n2. {time2}"
                                               f"\nℹ️Дополнительная информация: {remind.extra_inf}",
                                               reply_markup=replies.get_btns(btns={
                                                   'Удалить 🚮': f'delete_{remind.id}'}))
                elif remind.freq_per_day == 3:
                    await query.message.answer(f"<strong>💊Препарат: {remind.name}\n🗓Прием {remind.freq_per_day} раз в день"
                                               f" на протяжении {remind.freq_days} дней начиная с {date}</strong>"
                                               f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}"
                                               f"\nℹ️Дополнительная информация: {remind.extra_inf}",
                                               reply_markup=replies.get_btns(btns={
                                                   'Удалить 🚮': f'delete_{remind.id}'}))
                elif remind.freq_per_day == 4:
                    await query.message.answer(f"<strong>💊Препарат: {remind.name}\n🗓Прием {remind.freq_per_day} раз в день"
                                               f" на протяжении {remind.freq_days} дней начиная с {date}</strong>"
                                               f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}\n4. {time4}"
                                               f"\nℹ️Дополнительная информация: {remind.extra_inf}",
                                               reply_markup=replies.get_btns(btns={
                                                   'Удалить 🚮': f'delete_{remind.id}'}))
                elif remind.freq_per_day == 5:
                    await query.message.answer(f"<strong>💊Препарат: {remind.name}\n🗓Прием {remind.freq_per_day} раз в день"
                                               f" на протяжении {remind.freq_days} дней начиная с {date}</strong>"
                                               f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}\n4. {time4}\n5. {time5}"
                                               f"\nℹ️Дополнительная информация: {remind.extra_inf}",
                                               reply_markup=replies.get_btns(btns={
                                                   'Удалить 🚮': f'delete_{remind.id}'}))
                elif remind.freq_per_day == 6:
                    await query.message.answer(f"<strong>💊Препарат: {remind.name}\n🗓Прием {remind.freq_per_day} раз в день"
                                               f" на протяжении {remind.freq_days} дней начиная с {date}</strong>"
                                               f"\n⏰Время приема:\n1. {time1}\n2. {time2}\n3. {time3}\n4. {time4}\n5. {time5}\n6. {time6}"
                                               f"\nℹ️Дополнительная информация: {remind.extra_inf}",
                                               reply_markup=replies.get_btns(btns={
                                                   'Удалить 🚮': f'delete_{remind.id}'}))
        await query.message.answer("❗Список напоминаний представлен выше ⬆️"
                                   "\n\n📝Для удаления напоминания нажмите на кнопку"
                                   "\n\n❕Уведомления приходят по (UTC/GMT +05:00) Asia/Yekaterinburg, "
                                   "но только для лекарств!",
                                   reply_markup=replies.back_only_for_look_kb())


@user_private_router.callback_query(F.data.startswith('delete_'))
async def delete_remind(query: types.CallbackQuery, session: AsyncSession):
    remind_id = query.data.split("_")[-1]
    await orm_delete_remind(session, int(remind_id))
    await query.message.edit_text("❗Напоминание удалено")
    await query.answer("❗Напоминание удалено")


@user_private_router.callback_query(StateFilter('*'), MyCallback.filter(F.name == "create"))
async def create(query: CallbackQuery):
    await query.message.delete()
    await query.message.answer("❔Какое напоминание Вы хотите создать?", reply_markup=replies.create_kb())


''' 
 ХЭНДЛЕРЫ НА ПРИЁМ -----------------------------------------------------------------------------------------------------
'''


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "doctor"))
async def doctor(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text("🖋️Запись к врачу\n\n🩺<b>Введите специальность врача</b>", reply_markup=replies.cancel_kb())
    await state.set_state(AddReminderDoctor.speciality)


@user_private_router.message(StateFilter(AddReminderDoctor.speciality), F.text)
async def doctor_spec(message: types.Message, state: FSMContext):
    if len(message.text) <= 100:
        await state.update_data(speciality=message.text)
        await message.answer("🏥<b>Введите название поликлиники</b>", reply_markup=replies.back_cancel_kb())
        await state.set_state(AddReminderDoctor.name_clinic)
    else:
        await message.answer("❗Длина сообщения не может быть больше 100 символов"
                             "\n\n Введите текст заново")


@user_private_router.message(AddReminderDoctor.speciality)
async def doctor_spec_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.name_clinic), F.text)
async def doctor_clinic(message: types.Message, state: FSMContext):
    if len(message.text) <= 100:
        await state.update_data(name_clinic=message.text)
        await message.answer("🗓<b>Укажите день приема</b>",
                             reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
        await state.set_state(AddReminderDoctor.date)
    else:
        await message.answer("❗Длина сообщения не может быть больше 100 символов"
                             "\n\n Введите текст заново")


@user_private_router.message(AddReminderDoctor.name_clinic)
async def doctor_clinic_err(message: types.Message):
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
    calendar.set_dates_range(datetime(cur_year, cur_month, cur_day), datetime(cur_year+2, 12, 31))
    selected, chosen_date = await calendar.process_selection(query, callback_data)
    if selected:
        await query.message.edit_text(f'🗓<b>Укажите день приема</b>\n\n❗<b>Вы указали {chosen_date.strftime(f"%d.%m.%Y")}</b>')

        await state.update_data(date=chosen_date)  # .strftime(f"%d.%m.%Y")
        await query.message.answer("🕒<b>Введите время приема</b>\n\n❗Вводить время нужно в формате ЧЧ:ММ"
                                   "\nНапример, 11:30, 7:30, 0:30", reply_markup=replies.back_cancel_kb())
        await state.set_state(AddReminderDoctor.time)
    return chosen_date


@user_private_router.message(AddReminderDoctor.date)
async def doctor_date_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nВыберите дату <i>на календаре</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.time), F.text)
async def doctor_time(message: types.Message, state: FSMContext):
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
            current_datetime = datetime.now()
            current_time = current_datetime.strftime(f"%H:%M")
            current_date = current_datetime.strftime(f"%d/%m/%Y")
            if (chosen_hour < 0) or (chosen_hour >= 24):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M').time()
                data = await state.get_data()
                date = data["date"]
                date_and_time = datetime.combine(date, chosen_time)
                first_remind = date_and_time - timedelta(hours=24)
                second_remind = date_and_time - timedelta(hours=1)
                if date.strftime(f"%d/%m/%Y") == current_date:
                    if pre_time.strftime(f"%H") < current_datetime.strftime(f"%H"):
                        await message.answer(
                            f"❗Вы указали <b>некорректное</b> время\n<b>Время должно быть позже {current_time}</b>"
                            f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
                    elif pre_time.strftime(f"%H") == current_datetime.strftime(f"%H"):
                        if pre_time.strftime(f"%M") <= current_datetime.strftime(f"%M"):
                            await message.answer(
                                f"❗Вы указали <b>некорректное</b> время\n<b>Время должно быть позже {current_time}</b>"
                                f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
                        else:
                            await state.update_data(date=date_and_time)
                            await state.update_data(time=first_remind)
                            await state.update_data(sec_time=second_remind)
                            await message.answer("🚪<b>Укажите кабинет врача</b>", reply_markup=replies.back_cancel_kb())
                            await state.set_state(AddReminderDoctor.cabinet)
                    else:
                        await state.update_data(date=date_and_time)
                        await state.update_data(time=first_remind)
                        await state.update_data(sec_time=second_remind)
                        await message.answer("🚪<b>Укажите кабинет врача</b>", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderDoctor.cabinet)
                else:
                    await state.update_data(date=date_and_time)
                    await state.update_data(time=first_remind)
                    await state.update_data(sec_time=second_remind)
                    await message.answer("🚪<b>Укажите кабинет врача</b>", reply_markup=replies.back_cancel_kb())
                    await state.set_state(AddReminderDoctor.cabinet)
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderDoctor.time)
async def doctor_time_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <b>в необходимом формате</b>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.cabinet), F.text)
async def doctor_cabinet(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        if len(message.text) <= 100:
            await state.update_data(cabinet=message.text)
            await message.answer(
                "ℹ️<b>Введите дополнительную информацию</b>\n\nЗдесь вы можете указать ФИО врача, адрес поликлиники"
                ", и прочую информацию", reply_markup=replies.skip_bk_cl_kb())
            await state.set_state(AddReminderDoctor.extra_inf_doctor)
        else:
            await message.answer("❗Длина сообщения не может быть больше 100 символов"
                                 "\n\n Введите текст заново")
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>неотрицательным числом</i>",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderDoctor.cabinet)
async def doctor_cabinet_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>неотрицательным числом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message(StateFilter(AddReminderDoctor.extra_inf_doctor), F.text)
async def doctor_extra(message: types.Message, state: FSMContext, session: AsyncSession):
    if len(message.text) <= 250:
        await state.update_data(extra_inf_doctor=message.text)
        try:
            await state.update_data(chat_id=str(message.chat.id))
            data = await state.get_data()
            await orm_doctor_remind(session, data)
            await message.answer("✅<b>Напоминание добавлено</b>\n\n🔔Вам придет уведомление за 24 часа, за 1 час и в "
                                 "момент приема", reply_markup=replies.start_kb())
            await state.clear()
        except Exception as e:
            await message.answer(f"Ошибка: \n{str(e)}\n Информация не может быть загружена в базу данных",
                                 reply_markup=replies.start_kb())
            await state.clear()
    else:
        await message.answer("❗Длина сообщения не может быть больше 250 символов"
                             "\n\n Введите текст заново")


@user_private_router.message(AddReminderDoctor.extra_inf_doctor)
async def doctor_extra_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


''' 
 ХЭНДЛЕРЫ НА ЛЕКАРСТВА--------------------------------------------------------------------------------------------------
'''


@user_private_router.callback_query(StateFilter(None), MyCallback.filter(F.name == "pills"))
async def pills(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "🖋️Прием лекарств\n\n<b>💊Введите название лекарства</b>", reply_markup=replies.cancel_kb())
    await state.set_state(AddReminderPills.name)


@user_private_router.message(AddReminderPills.name, F.text)
async def pill_name(message: types.Message, state: FSMContext):
    if len(message.text) <= 100:
        await state.update_data(name=message.text)
        await message.answer("🗓️<b>Сколько дней нужно принимать лекарство</b>", reply_markup=replies.back_cancel_kb())
        await state.set_state(AddReminderPills.freq_days)
    else:
        await message.answer("❗Длина сообщения не может быть больше 100 символов"
                             "\n\n Введите текст заново")


@user_private_router.message(AddReminderPills.name)
async def pill_name_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите название <i>текстом</i>", reply_markup=replies.cancel_kb())


@user_private_router.message(AddReminderPills.freq_days, F.text)
async def pill_periodicity(message: types.Message, state: FSMContext):#
    mess = message.text
    if mess.isdigit():
        if int(mess) == 1:
            await state.update_data(freq_days=int(mess))
            await message.answer("🗓️<b>Укажите день начала приема</b>",
                                       reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
            await state.set_state(AddReminderPills.day_start)
        elif 1 < int(mess) <= 30:
            await state.update_data(freq_days=int(mess))
            await message.answer("📅<b>Как часто нужно принимать лекарство?</b>",
            reply_markup=replies.repeatability_kb())
            await state.set_state(AddReminderPills.periodicity)
        if int(mess) > 30 or int(mess) <= 0:
            await message.answer("❗Количество дней <b>не может</b> быть больше 30 или меньше 1"
                                 "\nУкажите подходящее количество", reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите количество <i>целым положительным числом</i>",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.freq_days)
async def pill_periodicity_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите количество <i>целым положительным числом</i>",
                         reply_markup=replies.cancel_kb())


@user_private_router.callback_query(AddReminderPills.periodicity, MyCallback.filter(F.name == "every_few_days"))
async def pill_every_few_days(query: CallbackQuery, callback_data: MyCallback, state: FSMContext):
    periodicity = callback_data.name
    if periodicity == "every_few_days":
        await state.update_data(periodicity=2)
    await query.message.delete()
    await query.message.answer("🗓️<b>Какой интервал в днях между днями приема лекарства?</b>",
                               reply_markup=replies.back_cancel_kb())
    await state.set_state(AddReminderPills.interval)


@user_private_router.callback_query(AddReminderPills.periodicity, MyCallback.filter(F.name.in_(["every_day", "every_other_day"])))
async def pill_freq_days(query: CallbackQuery, callback_data: MyCallback, state: FSMContext):
    periodicity = callback_data.name
    if periodicity == "every_day":
        await state.update_data(periodicity=0)
    elif periodicity == "every_other_day":
        await state.update_data(periodicity=1)

    await query.message.delete()
    await query.message.answer("🗓️<b>Укажите день начала приема</b>",
                         reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
    await state.set_state(AddReminderPills.day_start)


@user_private_router.message(AddReminderPills.periodicity)
async def pill_freq_days_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите количество <i>целым положительным числом</i>",
                         reply_markup=replies.cancel_kb())


@user_private_router.message(AddReminderPills.interval)
async def pill_freq_days(message: types.Message, state: FSMContext):
    mess = message.text
    if mess.isdigit():
        interval = int(mess)
        if 1 < interval <= 7:
            await state.update_data(interval=interval)
            await message.answer("🗓️<b>Укажите день начала приема</b>",
                                       reply_markup=await SimpleCalendar(locale='ru_Ru').start_calendar())
            await state.set_state(AddReminderPills.day_start)
        else:
            await message.answer("❗Некорректный ввод данных\n Введите число <i>от 2 до 7</i>")
    else:
        await message.answer("❗Некорректный ввод данных\n Введите число <i>от 2 до 7</i>")


@user_private_router.callback_query(StateFilter(AddReminderPills.day_start), SimpleCalendarCallback.filter())
async def pill_day_start(query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar(
        locale=await get_user_locale(query.from_user), show_alerts=True
    )
    today_date = datetime.now()
    cur_year = int(today_date.strftime("%Y"))
    cur_month = int(today_date.strftime("%m"))
    cur_day = int(today_date.strftime("%d"))
    calendar.set_dates_range(datetime(cur_year, cur_month, cur_day), datetime(cur_year+2, 12, 31))
    selected, chosen_date = await calendar.process_selection(query, callback_data)
    chosen_date = chosen_date
    if selected:
        await query.message.edit_text(f'🗓️<b>Укажите день начала приема</b>\n\n❗<b>Вы указали '
                                      f'{chosen_date.strftime(f"%d.%m.%Y")}</b>')
        await state.update_data(day_start=chosen_date)
        await query.message.answer("🔢<b>Сколько раз в день нужно принимать лекарство</b>",
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
            await message.answer("1️⃣<b>Укажите время 1 приема</b>\n\n❗Вводить время нужно в формате ЧЧ:ММ"
                                 "\nНапример, 11:30, 7:30, 0:30\n\n❕Время следует указывать в часовом поясе"
                                 " (UTC/GMT +05:00) Asia/Yekaterinburg", reply_markup=replies.back_cancel_kb())
            await state.set_state(AddReminderPills.first_take)
        if int(mess) > 6 or int(mess) <= 0:
            await message.answer("❗Количество приемов в день <b>не может</b> быть больше 6 или меньше 1"
                                 "\nУкажите подходящее количество", reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите количество <i>целым положительным числом</i>",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.freq_per_day)
async def pill_freq_per_day_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>целым положительным числом</i>",
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
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            else:
                pre_time = datetime.strptime(message_text, f"%H:%M")
                last_pre_time = pre_time.strftime(f"%H:%M")
                chosen_time = datetime.strptime(last_pre_time, '%H:%M')
                takes_time = [chosen_time]
                await state.update_data(first_take=takes_time)
                data = await state.get_data()
                count = data['freq_per_day']
                if count > 1:
                    await message.answer("2️⃣<b>Укажите время 2 приема</b>", reply_markup=replies.back_cancel_kb())
                    await state.set_state(AddReminderPills.sec_take)
                else:
                    await message.answer("ℹ️<b>Введите дополнительную информацию</b>\n\n"
                                         "Здесь вы можете указать дозировку препарата, то, как его принимать и прочую"
                                         " информацию", reply_markup=replies.skip_bk_cl_kb())
                    await state.set_state(AddReminderPills.extra_inf)
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.first_take)
async def pill_first_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ", reply_markup=replies.back_cancel_kb())


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
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
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
                    if count > 2:
                        await message.answer("3️⃣<b>Укажите время 3 приема</b>", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.third_take)
                    else:
                        await message.answer("ℹ️<b>Введите дополнительную информацию</b>\n\n"
                                         "Здесь вы можете указать дозировку препарата, то, как его принимать и прочую"
                                         " информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приема лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\n🕒Укажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i>",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.sec_take)
async def pill_sec_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.third_take, F.text)
async def pill_third_take(message: types.Message, state: FSMContext):
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
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
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
                    if count > 3:
                        await message.answer("4️⃣<b>Укажите время 4 приема</b>", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.four_take)
                    else:
                        await message.answer("ℹ️<b>Введите дополнительную информацию</b>\n\n"
                                         "Здесь вы можете указать дозировку препарата, то, как его принимать и прочую"
                                         " информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приема лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\n🕒Укажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.third_take)
async def pill_third_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.four_take, F.text)
async def pill_four_take(message: types.Message, state: FSMContext):
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
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
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
                    if count > 4:
                        await message.answer("5️⃣<b>Укажите время 5 приема</b>", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.five_take)
                    else:
                        await message.answer("ℹ️<b>Введите дополнительную информацию</b>\n\n"
                                         "Здесь вы можете указать дозировку препарата, то, как его принимать и прочую"
                                         " информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приема лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\n🕒Укажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.four_take)
async def pill_four_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i>",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.five_take, F.text)
async def pill_five_take(message: types.Message, state: FSMContext):
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
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
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
                    if count > 5:
                        await message.answer("6️⃣<b>Укажите время 6 приема</b>", reply_markup=replies.back_cancel_kb())
                        await state.set_state(AddReminderPills.six_take)
                    else:
                        await message.answer("ℹ️<b>Введите дополнительную информацию</b>\n\n"
                                         "Здесь вы можете указать дозировку препарата, то, как его принимать и прочую"
                                         " информацию", reply_markup=replies.skip_bk_cl_kb())
                        await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приема лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\n🕒Укажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.five_take)
async def pill_five_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.six_take, F.text)
async def pill_six_take(message: types.Message, state: FSMContext):
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
                                     f"\n🕒</b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
            elif (chosen_minute < 0) or (chosen_minute >= 60):
                await message.answer("❗<b>Указанное время некорректно</b>"
                                     f"\n🕒<b>Введите время заново</b>", reply_markup=replies.back_cancel_kb())
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
                    await message.answer("ℹ️<b>Введите дополнительную информацию</b>\n\n"
                                         "Здесь вы можете указать дозировку препарата, то, как его принимать и прочую"
                                         " информацию", reply_markup=replies.skip_bk_cl_kb())
                    await state.set_state(AddReminderPills.extra_inf)
                else:
                    await message.answer("❗Время приема лекарств <b>не должно совпадать</b> со временем,"
                                         " введенным ранее\n🕒Укажите другое время", reply_markup=replies.back_cancel_kb())
        else:
            await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                                 reply_markup=replies.back_cancel_kb())
    else:
        await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                             reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.six_take)
async def pill_six_take_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>в необходимом формате</i> ",
                         reply_markup=replies.back_cancel_kb())


@user_private_router.message(AddReminderPills.extra_inf, F.text)
async def pill_extra(message: types.Message, state: FSMContext, session: AsyncSession):
    if len(message.text) <= 250:
        await state.update_data(extra_inf=message.text)
        try:
            await state.update_data(chat_id=str(message.chat.id))
            data = await state.get_data()
            takes_time = data["first_take"]
            takes_time = [dt + timedelta(days=45656) for dt in takes_time]
            await message.answer(f"{takes_time}")
            if data["freq_per_day"] >= 1:
                await state.update_data(first_take=takes_time[0])
                if data["freq_per_day"] >= 2:
                    await state.update_data(sec_take=takes_time[1])
                    if data["freq_per_day"] >= 3:
                        await state.update_data(third_take=takes_time[2])
                        if data["freq_per_day"] >= 4:
                            await state.update_data(four_take=takes_time[3])
                            if data["freq_per_day"] >= 5:
                                await state.update_data(five_take=takes_time[4])
                                if data["freq_per_day"] == 6:
                                    await state.update_data(six_take=takes_time[5])
                                else:
                                    await state.update_data(six_take=None)
                            else:
                                await state.update_data(five_take=None)
                                await state.update_data(six_take=None)
                        else:
                            await state.update_data(four_take=None)
                            await state.update_data(five_take=None)
                            await state.update_data(six_take=None)
                    else:
                        await state.update_data(third_take=None)
                        await state.update_data(four_take=None)
                        await state.update_data(five_take=None)
                        await state.update_data(six_take=None)
                else:
                    await state.update_data(sec_take=None)
                    await state.update_data(third_take=None)
                    await state.update_data(four_take=None)
                    await state.update_data(five_take=None)
                    await state.update_data(six_take=None)
            data1 = await state.get_data()
            await orm_pills_remind(session, data1)
            await message.answer("✅Напоминание добавлено\n\n🔔Напоминания будут приходить в указанное время\n\n"
                                 "❕Уведомления приходят по (UTC/GMT +05:00) Asia/Yekaterinburg",
                                 reply_markup=replies.start_kb())
            await state.clear()
        except Exception as e:
            await message.answer(f"Ошибка: \n{str(e)}\n Информация не может быть загружена в базу данных",
                                 reply_markup=replies.start_kb())
            await state.clear()
    else:
        await message.answer("❗Длина сообщения не может быть больше 250 символов"
                             "\n\n Введите текст заново")


@user_private_router.message(AddReminderPills.extra_inf)
async def pill_extra_err(message: types.Message):
    await message.answer("❗Некорректный ввод данных\nУкажите <i>текстом</i>", reply_markup=replies.back_cancel_kb())


@user_private_router.message()  # магический фильтр ловит текст
async def stuff(message: types.Message):
    await message.answer("❗Некорректный ввод. Воспользуйтесь одной из кнопок")

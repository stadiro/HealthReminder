from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database.models import DoctorRemind, PillsRemind, AllRemind, PKTable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import UserTimezone

from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


async def convert_to_yekaterinburg(session, chat_id, dt):
    """Конвертирует datetime из часового пояса пользователя в Asia/Yekaterinburg"""
    from zoneinfo import ZoneInfo

    # Получаем часовой пояс пользователя
    result = await session.execute(select(UserTimezone).where(UserTimezone.chat_id == chat_id))
    user_timezone = result.scalars().first()

    # Если часовой пояс найден — используем его, иначе берём Europe/Moscow
    user_tz = user_timezone.timezone if user_timezone else "Europe/Moscow"

    # Добавляем временную зону пользователя (если нет tzinfo)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(user_tz))

    # Конвертируем в Asia/Yekaterinburg
    dt_yek = dt.astimezone(ZoneInfo("Asia/Yekaterinburg"))
    return dt_yek


async def orm_doctor_remind(session: AsyncSession, data: dict):
    chat_id = str(data["chat_id"])

    # Конвертируем все временные значения
    date_yekaterinburg = await convert_to_yekaterinburg(session, chat_id, data["date"])
    time_yekaterinburg = await convert_to_yekaterinburg(session, chat_id, data["time"])
    sec_time_yekaterinburg = await convert_to_yekaterinburg(session, chat_id, data["sec_time"])

    date_yekaterinburg = date_yekaterinburg.replace(tzinfo=None)
    time_yekaterinburg = time_yekaterinburg.replace(tzinfo=None)
    sec_time_yekaterinburg = sec_time_yekaterinburg.replace(tzinfo=None)


    pk = PKTable(
        name=data["speciality"]
    )
    session.add(pk)
    await session.commit()
    obj = DoctorRemind(
        id=pk.id,
        chat_id=data["chat_id"],
        speciality=data["speciality"],
        name_clinic=data["name_clinic"],
        date=date_yekaterinburg,
        first_remind=time_yekaterinburg,
        second_remind=sec_time_yekaterinburg,
        cabinet=data["cabinet"],
        extra_inf_doctor=data["extra_inf_doctor"]
    )
    session.add(obj)
    all_remind1 = AllRemind(
        id=pk.id,
        date_time=time_yekaterinburg,
        is_it_last=0,
        pills_or_doctor=0
    )
    session.add(all_remind1)
    all_remind2 = AllRemind(
        id=pk.id,
        date_time=sec_time_yekaterinburg,
        is_it_last=0,
        pills_or_doctor=0
    )
    session.add(all_remind2)
    all_remind3 = AllRemind(
        id=pk.id,
        date_time=date_yekaterinburg,
        is_it_last=1,
        pills_or_doctor=0
    )
    session.add(all_remind3)
    await session.commit()


async def orm_pills_remind( session: AsyncSession, data: dict):
    pk = PKTable(
        name=data["name"]
    )
    session.add(pk)
    await session.commit()

    chat_id = str(data["chat_id"])
    first_take1 = await convert_to_yekaterinburg(session, chat_id, data["first_take"]) if data["first_take"] is not None else None
    sec_take1 = await convert_to_yekaterinburg(session, chat_id, data["sec_take"]) if data["sec_take"] is not None else None
    third_take1 = await convert_to_yekaterinburg(session, chat_id, data["third_take"]) if data["third_take"] is not None else None
    four_take1 = await convert_to_yekaterinburg(session, chat_id, data["four_take"]) if data["four_take"] is not None else None
    five_take1 = await convert_to_yekaterinburg(session, chat_id, data["five_take"]) if data["five_take"] is not None else None
    six_take1 = await convert_to_yekaterinburg(session, chat_id, data["six_take"]) if data["six_take"] is not None else None

    first_take1 = first_take1.replace(tzinfo=None) if first_take1 is not None else None
    sec_take1 = sec_take1.replace(tzinfo=None) if sec_take1 is not None else None
    third_take1 = third_take1.replace(tzinfo=None) if third_take1 is not None else None
    four_take1 = four_take1.replace(tzinfo=None) if four_take1 is not None else None
    five_take1 = five_take1.replace(tzinfo=None) if five_take1 is not None else None
    six_take1 = six_take1.replace(tzinfo=None) if six_take1 is not None else None

    obj = PillsRemind(
        chat_id=data["chat_id"],
        name=data["name"],
        freq_days=data["freq_days"],
        periodicity=data["periodicity"],
        interval=data["interval"],
        day_start=data["day_start"],
        freq_per_day=data["freq_per_day"],
        first_take=first_take1,
        sec_take=sec_take1,
        third_take=third_take1,
        four_take=four_take1,
        five_take=five_take1,
        six_take=six_take1,
        extra_inf=data["extra_inf"]
    )
    obj.id = pk.id
    session.add(obj)
    await session.commit()

    periodicity = data.get("periodicity")
    interval = data.get("interval")
    # Формируем список приёмов (предполагается, что obj.first_take всегда задан)
    takes = []
    if obj.first_take is not None:
        takes.append(obj.first_take)
    if obj.sec_take is not None:
        takes.append(obj.sec_take)
    if obj.third_take is not None:
        takes.append(obj.third_take)
    if obj.four_take is not None:
        takes.append(obj.four_take)
    if obj.five_take is not None:
        takes.append(obj.five_take)
    if obj.six_take is not None:
        takes.append(obj.six_take)

    # Проходим по каждому дню приема
    for i in range(data["freq_days"]):
        # Для каждого времени приема из списка создаём напоминание
        for j, take in enumerate(takes):
            all_remind = AllRemind(
                date_time=datetime.combine(data["day_start"].date(), take.time()),
                pills_or_doctor=1
            )
            all_remind.id = pk.id
            # Если это последний день и последний прием – флаг is_it_last = 1
            if i == data["freq_days"] - 1 and j == len(takes) - 1:
                all_remind.is_it_last = 1
            else:
                all_remind.is_it_last = 0
            session.add(all_remind)

        # Переходим к следующему дню с учётом periodicity
        if periodicity == 0:
            data["day_start"] += timedelta(days=1)
        elif periodicity == 1:
            data["day_start"] += timedelta(days=2)
        elif periodicity == 2:
            data["day_start"] += timedelta(days=interval+1)

    await session.commit()


async def orm_get_reminds_doctor(session: AsyncSession):
    query = select(DoctorRemind)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_reminds_pill(session: AsyncSession):
    query = select(PillsRemind)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_reminds_all(session: AsyncSession):
    now = datetime.now().replace(second=0, microsecond=0)
    next_minute = now + timedelta(minutes=1)

    query = (
        select(AllRemind)
        .where(AllRemind.date_time.between(now, next_minute))  # Берем напоминания за ближайшую минуту
        .order_by(AllRemind.date_time.asc())  # Сортируем по времени
    )

    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_remind_doctor(session: AsyncSession, remind_id: int):
    query = select(DoctorRemind).where(DoctorRemind.id == remind_id)
    result = await session.execute(query)
    return result.scalars()


async def orm_get_remind_pill(session: AsyncSession, remind_id: int):
    query = select(PillsRemind).where(PillsRemind.id == remind_id)
    result = await session.execute(query)
    return result.scalars()


async def orm_delete_remind(session: AsyncSession, remind_id: int):
    query = delete(PKTable).where(PKTable.id == remind_id)
    await session.execute(query)
    await session.commit()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database.models import DoctorRemind, PillsRemind, AllRemind, PKTable
from datetime import datetime, timedelta


async def orm_doctor_remind(session: AsyncSession, data: dict):
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
        date=data["date"],
        first_remind=data["time"],
        second_remind=data["sec_time"],
        cabinet=data["cabinet"],
        extra_inf_doctor=data["extra_inf_doctor"]
    )
    session.add(obj)
    all_remind1 = AllRemind(
        id=pk.id,
        date_time=data["time"],
        is_it_last=0,
        pills_or_doctor=0
    )
    session.add(all_remind1)
    all_remind2 = AllRemind(
        id=pk.id,
        date_time=data["sec_time"],
        is_it_last=0,
        pills_or_doctor=0
    )
    session.add(all_remind2)
    all_remind3 = AllRemind(
        id=pk.id,
        date_time=data["date"],
        is_it_last=1,
        pills_or_doctor=0
    )
    session.add(all_remind3)
    await session.commit()


async def orm_pills_remind(session: AsyncSession, data: dict):
    pk = PKTable(
        name=data["name"]
    )
    session.add(pk)
    await session.commit()
    obj = PillsRemind(
        chat_id=data["chat_id"],
        name=data["name"],
        freq_days=data["freq_days"],
        day_start=data["day_start"],
        freq_per_day=data["freq_per_day"],
        first_take=data["first_take"],
        sec_take=data["sec_take"],
        third_take=data["third_take"],
        four_take=data["four_take"],
        five_take=data["five_take"],
        six_take=data["six_take"],
        extra_inf=data["extra_inf"]
    )
    obj.id = pk.id
    session.add(obj)
    await session.commit()

    for i in range(data["freq_days"]):
        if obj.first_take is not None:
            all_remind = AllRemind(
                date_time=datetime.combine(data["day_start"].date(), data["first_take"].time()),
                pills_or_doctor=1
            )
            all_remind.id = pk.id
            if i == int(data["freq_days"]-1) and obj.sec_take is None:
                all_remind.is_it_last = 1
            else:
                all_remind.is_it_last = 0
            session.add(all_remind)
            if obj.sec_take is not None:
                all_remind1 = AllRemind(
                    date_time=datetime.combine(data["day_start"].date(), data["sec_take"].time()),
                    pills_or_doctor=1
                )
                all_remind1.id = pk.id
                if i == int(data["freq_days"] - 1) and obj.third_take is None:
                    all_remind1.is_it_last = 1
                else:
                    all_remind1.is_it_last = 0
                session.add(all_remind1)
                if obj.third_take is not None:
                    all_remind2 = AllRemind(
                        date_time=datetime.combine(data["day_start"].date(), data["third_take"].time()),
                        pills_or_doctor=1
                    )
                    all_remind2.id = pk.id
                    if i == int(data["freq_days"] - 1) and obj.four_take is None:
                        all_remind2.is_it_last = 1
                    else:
                        all_remind2.is_it_last = 0
                    session.add(all_remind2)
                    if obj.four_take is not None:
                        all_remind3 = AllRemind(
                            date_time=datetime.combine(data["day_start"].date(), data["four_take"].time()),
                            pills_or_doctor=1
                        )
                        all_remind3.id = pk.id
                        if i == int(data["freq_days"] - 1) and obj.five_take is None:
                            all_remind3.is_it_last = 1
                        else:
                            all_remind3.is_it_last = 0
                        session.add(all_remind3)
                        if obj.five_take is not None:
                            all_remind4 = AllRemind(
                                date_time=datetime.combine(data["day_start"].date(), data["five_take"].time()),
                                pills_or_doctor=1
                            )
                            all_remind4.id = pk.id  # Set the foreign key in PillsRemind
                            if i == int(data["freq_days"] - 1) and obj.six_take is None:
                                all_remind4.is_it_last = 1
                            else:
                                all_remind4.is_it_last = 0
                            session.add(all_remind4)
                            if obj.six_take is not None:
                                all_remind5 = AllRemind(
                                    date_time=datetime.combine(data["day_start"].date(), data["six_take"].time()),
                                    pills_or_doctor=1
                                )
                                all_remind5.id = pk.id
                                if i == int(data["freq_days"] - 1):
                                    all_remind5.is_it_last = 1
                                else:
                                    all_remind5.is_it_last = 0
                                session.add(all_remind5)
        data["day_start"] += timedelta(days=1)
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
    query = select(AllRemind)
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

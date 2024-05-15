from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from database.models import DoctorRemind


async def orm_doctor_remind(session: AsyncSession, data: dict):
    obj = DoctorRemind(
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
    await session.commit()


async def orm_get_reminds(session: AsyncSession):
    query = select(DoctorRemind)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_remind(session: AsyncSession, remind_id: int):
    query = select(DoctorRemind).where(DoctorRemind.id == remind_id)
    result = await session.execute(query)
    return result.scalars()


async def orm_update_doctor_remind(session: AsyncSession, remind_id: int, data):
    query = update(DoctorRemind).where(DoctorRemind.id == remind_id).values(
        speciality=data["speciality"],
        name_clinic=data["name_clinic"],
        date=data["date"],
        time=data["time"],
        cabinet=data["cabinet"],
        extra_inf_doctor=data["extra_inf_doctor"],)
    await session.execute(query)
    await session.commit()


async def orm_delete_remind(session: AsyncSession, remind_id: int):
    query = delete(DoctorRemind).where(DoctorRemind.id == remind_id)
    await session.execute(query)
    await session.commit()

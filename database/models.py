from sqlalchemy import DateTime, Text, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    ...


class DoctorRemind(Base):
    __tablename__ = 'doctor_remind'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    speciality: Mapped[str] = mapped_column(Text, nullable=False)
    name_clinic: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    first_remind: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    second_remind: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    cabinet: Mapped[str] = mapped_column(Text, nullable=False)
    extra_inf_doctor: Mapped[str] = mapped_column(Text, nullable=False)

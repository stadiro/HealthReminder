from sqlalchemy import DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    ...


class PKTable(Base):
    __tablename__ = 'pk_table'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    all_reminds = relationship("AllRemind", cascade="all, delete", back_populates="pk_table")
    doctor_reminds = relationship("DoctorRemind", cascade="all, delete", back_populates="pk_table")
    pills_reminds = relationship("PillsRemind", cascade="all, delete", back_populates="pk_table")


class AllRemind(Base):
    __tablename__ = 'all_remind'

    id: Mapped[int] = mapped_column(ForeignKey("pk_table.id", ondelete="CASCADE"))
    all_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    is_it_last: Mapped[int] = mapped_column(Integer, nullable=False)
    pills_or_doctor: Mapped[int] = mapped_column(Integer, nullable=False)

    pk_table = relationship("PKTable", back_populates="all_reminds")


class DoctorRemind(Base):
    __tablename__ = 'doctor_remind'

    id: Mapped[int] = mapped_column(ForeignKey("pk_table.id", ondelete="CASCADE"))
    doct_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    chat_id: Mapped[str] = mapped_column(Text, nullable=False)
    speciality: Mapped[str] = mapped_column(Text, nullable=False)
    name_clinic: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    first_remind: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    second_remind: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    cabinet: Mapped[str] = mapped_column(Text, nullable=False)
    extra_inf_doctor: Mapped[str] = mapped_column(Text, nullable=False)

    pk_table = relationship("PKTable", back_populates="doctor_reminds")


class PillsRemind(Base):
    __tablename__ = 'pills_remind'

    id: Mapped[int] = mapped_column(ForeignKey("pk_table.id", ondelete="CASCADE"))
    pill_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    chat_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    freq_days: Mapped[int] = mapped_column(Integer, nullable=False)
    day_start: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    freq_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    first_take: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    sec_take: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    third_take: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    four_take: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    five_take: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    six_take: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    extra_inf: Mapped[str] = mapped_column(Text, nullable=False)

    pk_table = relationship("PKTable", back_populates="pills_reminds")

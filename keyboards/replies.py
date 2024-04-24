from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class MyCallback(CallbackData, prefix="my"):
    name: str


def start_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Создать напоминание ⏰", callback_data=MyCallback(name="create").pack())
    )
    return builder.as_markup()


def create_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Запись ко врачу 🏥", callback_data=MyCallback(name="doctor").pack()),
        InlineKeyboardButton(text="Прием лекарств 💊", callback_data=MyCallback(name="pills").pack()),
    )
    return builder.adjust(1).as_markup()


def back_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Назад ⬅️", callback_data=MyCallback(name="back").pack()),
        InlineKeyboardButton(text="Отмена ↩️", callback_data=MyCallback(name="cancel").pack()),
    )
    return builder.as_markup()


def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отмена ↩️", callback_data=MyCallback(name="cancel").pack()),
    )
    return builder.as_markup()


class TimeCallback(CallbackData, prefix="my"):
    name: str
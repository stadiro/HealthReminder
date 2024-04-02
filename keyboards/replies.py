from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class MyCallback(CallbackData, prefix="my"):
    name: str


def start_kb():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Создать напоминание",
        callback_data=MyCallback(name="create")
    )
    return builder.as_markup()


def create_kb():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Запись ко врачу",
        callback_data=MyCallback(name="doctor")
    )
    builder.button(
        text="Прием лекарств",
        callback_data=MyCallback(name="pills")
    )
    return builder.as_markup()


del_kb = ReplyKeyboardRemove()
start_kb1 = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Меню"),
        ],
        {
            KeyboardButton(text="Пока бесполезная кнопка")
        }
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите нужный вариант"
)

del_kb = ReplyKeyboardRemove()

start_kb2 = ReplyKeyboardBuilder()
start_kb2.add(
    KeyboardButton(text="Меню"),
    KeyboardButton(text="Бесполезная кнопка"),
)
start_kb2.adjust(1, 1)

start_kb3 = ReplyKeyboardBuilder()
start_kb3.attach(start_kb2)
start_kb3.row(KeyboardButton(text="прикона!1!!"))


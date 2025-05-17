from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class MyCallback(CallbackData, prefix="my"):
    name: str


def start_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Создать напоминание ⏰", callback_data=MyCallback(name="create").pack()),
        InlineKeyboardButton(text="Просмотр напоминаний 📚", callback_data=MyCallback(name="look").pack()),
        InlineKeyboardButton(text="Изменить часовой пояс 🕰", callback_data=MyCallback(name="timezone_new").pack()),
    )
    return builder.adjust(1).as_markup()


def repeatability_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Каждый день 🔁", callback_data=MyCallback(name="every_day").pack()),)
    builder.row(InlineKeyboardButton(text="День через день 🔂", callback_data=MyCallback(name="every_other_day").pack()),)
    builder.row(InlineKeyboardButton(text="Раз в несколько дней ⤴️", callback_data=MyCallback(name="every_few_days").pack()),)
    builder.row(
        InlineKeyboardButton(text="Назад ⬅️", callback_data=MyCallback(name="back").pack()),
        InlineKeyboardButton(text="Отмена ↩️", callback_data=MyCallback(name="cancel").pack()),
    )
    return builder.as_markup()


def no_reminders_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Создать напоминание ⏰", callback_data=MyCallback(name="create").pack()),
    )
    return builder.as_markup()


def create_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Запись к врачу 🏥", callback_data=MyCallback(name="doctor").pack()),
        InlineKeyboardButton(text="Прием лекарств 💊", callback_data=MyCallback(name="pills").pack()),
        InlineKeyboardButton(text="Назад ⬅️", callback_data=MyCallback(name="start").pack()),
    )
    return builder.adjust(1).as_markup()


def back_only_for_look_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Назад ⬅️", callback_data=MyCallback(name="start").pack()),
    )
    return builder.as_markup()


def back_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Назад ⬅️", callback_data=MyCallback(name="back").pack()),
        InlineKeyboardButton(text="Отмена ↩️", callback_data=MyCallback(name="cancel").pack()),
    )
    return builder.as_markup()


def skip_bk_cl_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Назад ⬅️", callback_data=MyCallback(name="back").pack()),
        InlineKeyboardButton(text="Отмена ↩️", callback_data=MyCallback(name="cancel").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="Без доп. информации ➡️", callback_data=MyCallback(name="skip").pack()),
    )
    return builder.as_markup()


def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отмена ↩️", callback_data=MyCallback(name="cancel").pack()),
    )
    return builder.as_markup()


def get_btns(
    *,
    btns: dict[str, str],
    sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    return keyboard.adjust(*sizes).as_markup()

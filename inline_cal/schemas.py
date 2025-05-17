# Copyright (c) 2023 o-murphy
# Copyright (c) 2025 Беляков Олег Игоревич
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Optional
from enum import Enum

from pydantic import BaseModel, conlist, Field

from aiogram.filters.callback_data import CallbackData


class SimpleCalAct(str, Enum):
    ignore = 'IGNORE'
    prev_y = 'PREV-YEAR'
    next_y = 'NEXT-YEAR'
    prev_m = 'PREV-MONTH'
    next_m = 'NEXT-MONTH'
    cancel = 'CANCEL'
    back = 'BACK'
    today = 'TODAY'
    day = 'DAY'


class DialogCalAct(str, Enum):
    ignore = 'IGNORE'
    set_y = 'SET-YEAR'
    set_m = 'SET-MONTH'
    prev_y = 'PREV-YEAR'
    next_y = 'NEXT-YEAR'
    cancel = 'CANCEL'
    start = 'START'
    day = 'SET-DAY'


class CalendarCallback(CallbackData, prefix="calendar"):
    act: str
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None


class SimpleCalendarCallback(CalendarCallback, prefix="simple_calendar"):
    act: SimpleCalAct


class DialogCalendarCallback(CalendarCallback, prefix="dialog_calendar"):
    act: DialogCalAct


class CalendarLabels(BaseModel):
    "Schema to pass labels for calendar. Can be used to put in different languages"
    days_of_week: conlist(str, max_length=7, min_length=7) = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    months: conlist(str, max_length=12, min_length=12) = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    cancel_caption: str = Field(default='Отмена', description='Caprion for Cancel button')
    today_caption: str = Field(default='Сегодня', description='Caprion for Cancel button')
    back_caption: str = Field(default='Назад', description='Caprion for Cancel button')


HIGHLIGHT_FORMAT = "[{}]"


def highlight(text):
    return HIGHLIGHT_FORMAT.format(text)


def superscript(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-=()"
    super_s = "ᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾQᴿˢᵀᵁⱽᵂˣʸᶻᵃᵇᶜᵈᵉᶠᵍʰᶦʲᵏˡᵐⁿᵒᵖ۹ʳˢᵗᵘᵛʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾"
    output = ''
    for i in text:
        output += (super_s[normal.index(i)] if i in normal else i)
    return output


def subscript(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-=()"
    sub_s = "ₐ₈CDₑբGₕᵢⱼₖₗₘₙₒₚQᵣₛₜᵤᵥwₓᵧZₐ♭꜀ᑯₑբ₉ₕᵢⱼₖₗₘₙₒₚ૧ᵣₛₜᵤᵥwₓᵧ₂₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎"
    output = ''
    for i in text:
        output += (sub_s[normal.index(i)] if i in normal else i)
    return output

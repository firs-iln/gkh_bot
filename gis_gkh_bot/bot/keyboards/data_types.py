from enum import StrEnum
from typing import Literal

from aiogram.filters.callback_data import CallbackData


class Action(StrEnum):
    ACCEPT = 'accept'
    DECLINE = 'decline'
    REQUEST = 'request'


class MenuAction(StrEnum):
    FIND_MKD = 'Найти дом'
    MY_MKDS = 'Мои дома'


class Button(StrEnum):
    CONTROL_INFO = 'Отчет об управлении'
    PASSPORT = 'Эл. паспорт'
    ROOMS = 'Найти помещения'
    TABLE = 'Таблица МКД'



class BoolCallbackData(CallbackData, prefix='download'):
    action: Action
    id: str


class FoundRightMKDData(CallbackData, prefix='found'):
    action: Action


class ContinueParsingData(CallbackData, prefix='continue_parsing'):
    action: Action
    id: str
    rm_rooms: bool


class CancelParsingData(CallbackData, prefix='cancel_parsing'):
    action: Action
    task_name: str
    mkd_id: str


class MKDData(CallbackData, prefix='address'):
    id: str


class CollectPDFData(CallbackData, prefix='pdf'):
    mkd_id: str
    action: Literal['control_info', 'passport']
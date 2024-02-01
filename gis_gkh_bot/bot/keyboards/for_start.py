from asyncio import Task

from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder
from loguru import logger

from bot.keyboards.data_types import Button, MenuAction, FoundRightMKDData, BoolCallbackData, Action, MKDData, \
    CollectPDFData, \
    ContinueParsingData, CancelParsingData
from parser.mkd import MKD
from parser.organization import Organization


def get_start_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=MenuAction.FIND_MKD))
    builder.add(KeyboardButton(text=MenuAction.MY_MKDS))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_found_right_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='да', callback_data=FoundRightMKDData(action=Action.ACCEPT).pack()),
                InlineKeyboardButton(text='нет',
                                     callback_data=FoundRightMKDData(action=Action.DECLINE).pack()))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


async def get_mkds_keyboard(mkds: list[MKD]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mkd in mkds:
        builder.add(
            InlineKeyboardButton(text=f"{mkd.address} ({mkd.cad_num})", callback_data=MKDData(id=mkd.id).pack()))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


async def get_mkd_card_keyboard(mkd: MKD, rm_rooms: bool = True, btn_pressed: Button = None) -> InlineKeyboardMarkup:
    buttons = {
        Button.CONTROL_INFO: InlineKeyboardButton(
            text='Отчет об управлении',
            callback_data=CollectPDFData(mkd_id=mkd.id, action='control_info').pack()
        ),
        Button.PASSPORT: InlineKeyboardButton(
            text='Эл. паспорт',
            callback_data=CollectPDFData(mkd_id=mkd.id, action='passport').pack()
        ),
        Button.ROOMS: InlineKeyboardButton(
            text='Найти помещения',
            callback_data=ContinueParsingData(action=Action.ACCEPT, id=mkd.id, rm_rooms=rm_rooms).pack()),
        Button.TABLE: InlineKeyboardButton(
            text='Таблица МКД',
            callback_data=BoolCallbackData(action=Action.ACCEPT, id=mkd.id).pack())
    }
    if btn_pressed:
        buttons.pop(btn_pressed)
    if await mkd.has_rooms and btn_pressed != Button.ROOMS:
        buttons.pop(Button.ROOMS)
    builder = InlineKeyboardBuilder()
    for btn in buttons.values():
        builder.add(btn)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_organizations_keyboard(organizations: list[Organization]) -> ReplyKeyboardMarkup:
    logger.debug(organizations)
    builder = ReplyKeyboardBuilder()
    for organisation in organizations:
        builder.add(KeyboardButton(text=organisation.name))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_download_bool_keyboard(mkd: MKD) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='да', callback_data=BoolCallbackData(action=Action.ACCEPT, id=mkd.id).pack()),
                InlineKeyboardButton(text='нет',
                                     callback_data=BoolCallbackData(action=Action.DECLINE, id=mkd.id).pack()))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_continue_parsing_keyboard(mkd: MKD, rm_rooms: bool = False,
                                  include_cancel: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='запустить',
                                     callback_data=ContinueParsingData(action=Action.ACCEPT, id=mkd.id,
                                                                       rm_rooms=rm_rooms).pack()))
    if include_cancel:
        builder.add(InlineKeyboardButton(text='отмена',
                                         callback_data=ContinueParsingData(action=Action.DECLINE, id=mkd.id,
                                                                           rm_rooms=rm_rooms).pack()))
        builder.adjust(2)
    else:
        builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_cancel_rooms_parsing_keyboard(task: Task, mkd_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text='Отменить',
        callback_data=CancelParsingData(task_name=task.get_name(), mkd_id=mkd_id, action=Action.REQUEST).pack()))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_confirm_rooms_parsing_cancel_keyboard(task: Task, mkd_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text='Продолжить',
        callback_data=CancelParsingData(task_name=task.get_name(), mkd_id=mkd_id, action=Action.DECLINE).pack()
    ))
    builder.add(InlineKeyboardButton(
        text='Удалить',
        callback_data=CancelParsingData(task_name=task.get_name(), mkd_id=mkd_id, action=Action.ACCEPT).pack()
    ))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_collect_pdf_keyboard(mkd: MKD) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text='Отчет об управлении',
        callback_data=CollectPDFData(mkd_id=mkd.id, action='control_info').pack()
    ))
    builder.add(InlineKeyboardButton(
        text='Эл. паспорт',
        callback_data=CollectPDFData(mkd_id=mkd.id, action='passport').pack()
    ))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

import asyncio
from asyncio import Task
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InputMediaPhoto, FSInputFile, CallbackQuery
from httpx import HTTPStatusError
from loguru import logger

from bot.config.bot import bot
from bot.keyboards.data_types import MenuAction, BoolCallbackData, Action, ContinueParsingData, CancelParsingData, \
    CollectPDFData, FoundRightMKDData, Button
from bot.keyboards.for_start import get_continue_parsing_keyboard, \
    get_cancel_rooms_parsing_keyboard, get_confirm_rooms_parsing_cancel_keyboard, \
    get_mkd_card_keyboard, get_start_keyboard, get_found_right_keyboard
from dadata_wrapper.dadataapi import get_address_data
from parser.mkd import MKDParser, MKD
from parser.organization import Organization
from parser.saver import MKDDataSaver
from parser.utils import BASE_DIR
from pdf_collector.api import PDFCollector

router = Router()
parser = MKDParser()
lock = asyncio.Lock()

IMG_DIR = Path(__file__).parent / 'img'
IS_DELETING_BUTTON = False


class MKDState(StatesGroup):
    entering_house_link = State()
    entering_house_cad_num = State()
    entering_house_addr = State()


@router.message(F.text == MenuAction.FIND_MKD)
async def cmd_addr(message: Message, state: FSMContext) -> None:
    await message.delete()
    msg = await message.answer('Пожалуйста, введите адрес')
    await state.update_data(addr_msg_id=msg.message_id)
    await state.set_state(MKDState.entering_house_addr)


@router.message(Command(commands=['start']))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    data = await state.get_data()
    if not data.get('mkds'):
        await state.set_data({'mkds': []})
    await message.answer(
        "Это бот извлекает нужную информацию из ГИС ЖКХ.\nОн может:\n🚀 найти любой многоквартирный дом на ГИС ЖКХ\n🤳 выводить информацию для удобного использования\n🤖 распарсить эл.паспорт МКД и другие разделы сайта\n✅ а также сверить помещения дома с данными из ФИАС\n📕 создать отчеты в формате pdf с эл.подписью ГИС ЖКХ\nНаслаждайтесь! 🎁",
        reply_markup=get_start_keyboard())
    await parser.write_user_data(message.from_user, datetime.now().strftime('%d.%m.%Y %H:%M'))


@router.message(Command(commands=['cancel']))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    await state.update_data({'mkds': []})
    await message.answer('Действие успешно отменено', )


@router.message(Command(commands=['gisgkh']))
async def cmd_infogis(message: Message, state: FSMContext) -> None:
    houses = InputMediaPhoto(
        media=FSInputFile(IMG_DIR / 'houses.jpeg'),
        caption='Перейдите по ссылке "Сведения об объекте жилищного фонда" и скопируйте сюда ссылку на карточку дома в браузере, строка начинается с https://dom.gosuslugi.ru/#!/house-view',
    )
    house_view = InputMediaPhoto(media=FSInputFile(IMG_DIR / 'house_view.jpeg'))
    msg_1 = await message.answer('Зайдите по ссылке https://dom.gosuslugi.ru/#!/houses найдите ваш дом', )
    msg_2 = await message.answer_media_group([house_view, houses])
    await state.set_state(MKDState.entering_house_link)
    await state.update_data(
        {'msgs_to_delete_part': [message.message_id, msg_1.message_id, *[msg.message_id for msg in msg_2]]})


@router.message(
    F.text.startswith('https://'),
    MKDState.entering_house_link
)
async def on_entering_house_link(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if not message.text.startswith('https://dom.gosuslugi.ru/#!/house-view'):
        await message.answer('Кажется, вы ввели некорректную ссылку. Попробуйте, пожалуйста, снова')
    else:
        msg = await message.answer('Начинаю сбор информации из ГИС ЖКХ...\nПожалуйста, ожидайте сообщения')
        mkd: MKD = await parser.run(message.text)
        orgs = await mkd.orgs
        if not mkd.id:
            cad_msg = await message.answer(
                '<b>Внимание! По данному дому не указан кадастровый номер МКД. Найдите дом в <a href="https://lk.rosreestr.ru/eservices/real-estate-objects-online">ЕГРН Росреестра</a> и скопируйте сюда кадастровый номер здания</b>'
            )
            for msg_id in [message.message_id, msg.message_id, *data['msgs_to_delete_part']]:
                await bot.delete_message(message.chat.id, msg_id)

            logger.debug(mkd.address)
            await state.update_data({'mkd_no_cad_num': asdict(mkd), 'cad_num_msg_id': cad_msg.message_id,
                                     'mkd_orgs': [tuple(asdict(org).values()) for org in orgs]})
            await state.set_state(MKDState.entering_house_cad_num)
            return
        if await parser.rooms_parser.mkd_has_rooms(mkd.id):
            for msg_id in [message.message_id, msg.message_id, *data['msgs_to_delete_part']]:
                await bot.delete_message(message.chat.id, msg_id)
            await message.answer(
                f'Такой <a href="{mkd.card_link}">МКД</a>: <b>{mkd.address} ({mkd.cad_num})</b> уже есть в нашей базе данных.\nХотите запустить повторный сбор информации о помещениях из ГИС ЖКХ?',
                reply_markup=get_continue_parsing_keyboard(mkd, rm_rooms=True, include_cancel=True)
            )
            return
        text = f'Получены данные по <a href="{mkd.card_link}">МКД</a>:\n<b>{mkd.address} ({mkd.cad_num or ""})</b>\n\n'
        if 'непосредственное' in mkd.control_method.lower():
            text += 'Непосредственное управление\n'
        text += get_orgs_string(mkd, orgs)
        saver = MKDDataSaver(mkd, orgs)
        await saver.save_mkd_to_excel()
        await message.answer(text, reply_markup=await get_mkd_card_keyboard(mkd))
        for msg_id in [message.message_id, msg.message_id, *data['msgs_to_delete_part']]:
            await bot.delete_message(message.chat.id, msg_id)
        await state.set_state(None)


@router.message(MKDState.entering_house_cad_num)
async def on_entering_house_cad_num(message: Message, state: FSMContext) -> None:
    cad_num = message.text
    data = await state.get_data()
    cad_msg_id = data.get('cad_num_msg_id')
    mkd: MKD = MKD(*list(data.get('mkd_no_cad_num').values()))
    orgs = [Organization(*org) for org in data.get('mkd_orgs')]
    mkd.cad_num = cad_num
    mkd.id = cad_num.replace(':', '')
    await parser.save_mkd_data(mkd)
    await state.set_state(None)
    await state.update_data({'mkd_no_cad_num': None, 'cad_num_msg_id': None})
    await message.answer(f'Кадастровый номер <a href="{mkd.card_link}">МКД</a> успешно добавлен')
    text = f'<a href="{mkd.card_link}">МКД</a>:\n<b>{mkd.address} ({mkd.cad_num or ""})</b>\n\n'
    if 'непосредственное' in mkd.control_method.lower():
        text += 'Непосредственное управление\n'
    text += get_orgs_string(mkd, orgs)
    saver = MKDDataSaver(mkd, orgs)
    await saver.save_mkd_to_excel()
    await message.answer(text, reply_markup=await get_mkd_card_keyboard(mkd))
    await bot.delete_message(message.chat.id, cad_msg_id)
    await message.delete()


@router.message(MKDState.entering_house_addr)
async def on_entering_house_addr(message: Message, state: FSMContext) -> None:
    await message.delete()
    data = await state.get_data()
    msg = await message.answer('Начинаю сбор информации\nПожалуйста, ожидайте сообщения')
    address = message.text
    try:
        result = get_address_data(address)
        if 'Санкт-Петербург' in result.result and not result.house_cadnum:
            result = get_address_data(f"{address} литера А")
    except HTTPStatusError:
        addr_msg = await message.answer(
            'Произошла ошибка. Пожалуйста, нажмите /gisgkh, чтобы найти нужный дом в ГИС ЖКХ')
        await state.update_data(addr_msg_id=addr_msg.message_id)
        return
    await msg.delete()
    with suppress(TelegramBadRequest):
        await bot.delete_message(message.chat.id, data['addr_msg_id'])
    if result.house_cadnum:
        await message.answer(f"<b>{result.result} ({result.house_cadnum})</b>\nЭто нужный адрес?",
                             reply_markup=get_found_right_keyboard())
        await state.update_data(addr=result.result)
    else:
        addr_msg = await message.answer(
            'Пожалуйста, введите адрес дома еще раз или нажмите /gisgkh, чтобы найти нужный дом в ГИС ЖКХ')
        await state.update_data(addr_msg_id=addr_msg.message_id)


@router.callback_query(FoundRightMKDData.filter(F.action == Action.ACCEPT))
async def on_found_right_mkd_data(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    data = await state.get_data()
    await query.message.delete()
    msg = await query.message.answer('Продолжаю сбор информации...\nПожалуйста, ожидайте сообщения')
    mkd: MKD = await parser.run(address=data['addr'])
    orgs = await mkd.orgs
    if await parser.rooms_parser.mkd_has_rooms(mkd.id):
        await msg.delete()
        await query.message.answer(
            f'<a href="{mkd.card_link}">МКД</a>: <b>{mkd.address} ({mkd.cad_num})</b> уже есть в нашей базе данных.\nХотите запустить повторный сбор информации о помещениях из ГИС ЖКХ?',
            reply_markup=get_continue_parsing_keyboard(mkd, rm_rooms=True, include_cancel=True)
        )
        return
    text = f'Получены данные по <a href="{mkd.card_link}">МКД</a>:\n<b>{mkd.address} ({mkd.cad_num or ""})</b>\n\n'
    if 'непосредственное' in mkd.control_method.lower():
        text += 'Непосредственное управление\n'
    text += get_orgs_string(mkd, orgs)
    saver = MKDDataSaver(mkd, orgs)
    await saver.save_mkd_to_excel()
    await query.message.answer(text, reply_markup=await get_mkd_card_keyboard(mkd), disable_webpage_preview=True)
    await msg.delete()


@router.callback_query(FoundRightMKDData.filter(F.action == Action.DECLINE))
async def on_found_right_mkd_data_decline(query: CallbackQuery, state: FSMContext) -> None:
    await query.message.delete()
    addr_msg = await query.message.answer(
        'Пожалуйста, введите адрес дома еще раз или нажмите /gisgkh, чтобы найти нужный дом в ГИС ЖКХ')
    await state.update_data(addr_msg_id=addr_msg.message_id)


@router.callback_query(BoolCallbackData.filter(F.action == Action.ACCEPT))
async def on_accept_download(query: CallbackQuery, callback_data: BoolCallbackData, state: FSMContext) -> None:
    mkd = await parser.find_mkd_by_id(callback_data.id)
    while IS_DELETING_BUTTON:
        await asyncio.sleep(2.5)
    async with lock:
        await _delete_button_from_message_markup(Button.TABLE, query.message)
    file = FSInputFile(BASE_DIR / 'reports' / f'МКД_{mkd.cad_num}_{mkd.address.replace("/", "_")}.xlsx')
    await query.message.answer_document(file, )
    with suppress(TelegramBadRequest):
        await query.answer()
    await state.set_state(None)


@router.callback_query(ContinueParsingData.filter(F.action == Action.ACCEPT))
async def on_continue_parsing_accept(query: CallbackQuery, callback_data: ContinueParsingData,
                                     state: FSMContext) -> None:
    chat_id = query.message.chat.id
    mkd = await parser.find_mkd_by_id(callback_data.id)
    if callback_data.rm_rooms and ('МКД' not in query.message.text or 'повторный сбор' in query.message.text):
        await query.message.delete()
    elif 'МКД' in query.message.text:
        while IS_DELETING_BUTTON:
            await asyncio.sleep(2.5)
        async with lock:
            await _delete_button_from_message_markup(Button.ROOMS, query.message)
    with suppress(TelegramBadRequest):
        await query.answer()
    orgs = await mkd.orgs
    while parser.rooms_parser.is_running:
        logger.debug(parser.rooms_parser.is_running)
        await asyncio.sleep(10)
    task = asyncio.create_task(
        parser.rooms_parser.parse_mkd_rooms_by_guid(parser.parse_guid_from_card_link(mkd.card_link), mkd))
    msg = await bot.send_message(
        chat_id,
        f'Cобираю данные о помещениях из <a href="{mkd.passport_link}">эл.паспорта дома</a> по адресу <b>{mkd.address}</b>. Пожалуйста, ожидайте сообщения',
        reply_markup=get_cancel_rooms_parsing_keyboard(task, mkd.id)
    )
    if callback_data.rm_rooms:
        await parser.rooms_parser.delete_rooms_by_mkd_id(callback_data.id)
    await task
    if task.result():
        saver = MKDDataSaver(mkd, orgs, task.result())
        await saver.save_mkd_to_excel()
        data = await state.get_data()
        await query.message.delete()
        with suppress(TelegramBadRequest, Exception):
            await msg.delete()
            await bot.delete_message(query.message.chat.id, data.get('continue_msg_id'))
        text = f'<a href="{mkd.card_link}">МКД</a>: <b>{mkd.address} ({mkd.cad_num})\n\n{parser.get_rooms_report_string(mkd, task.result())}</b>\n\n'
        if 'непосредственное' in mkd.control_method.lower():
            text += 'Непосредственное управление\n'
        text += get_orgs_string(mkd, orgs)
        logger.debug('text formed')
        saver = MKDDataSaver(mkd, orgs, task.result())
        await saver.save_mkd_to_excel()
        await query.message.answer(text, reply_markup=await get_mkd_card_keyboard(mkd))


@router.callback_query(ContinueParsingData.filter(F.action == Action.DECLINE))
async def on_continue_parsing_decline(query: CallbackQuery, callback_data: ContinueParsingData) -> None:
    await query.message.delete()
    mkd = await parser.find_mkd_by_id(callback_data.id)
    orgs = await mkd.orgs
    rooms = await mkd.rooms
    text = f'<a href="{mkd.card_link}">МКД</a>: <b>{mkd.address} ({mkd.cad_num})</b>\n\n{parser.get_rooms_report_string(mkd, rooms)}'
    if 'непосредственное' in mkd.control_method.lower():
        text += 'Непосредственное управление\n'
    text += get_orgs_string(mkd, orgs)
    saver = MKDDataSaver(mkd, orgs, rooms)
    await saver.save_mkd_to_excel()
    await query.message.answer(text, reply_markup=await get_mkd_card_keyboard(mkd))
    with suppress(TelegramBadRequest):
        await query.answer()


@router.callback_query(CancelParsingData.filter(F.action == Action.REQUEST))
async def on_cancel_parsing(query: CallbackQuery, callback_data: CancelParsingData) -> None:
    await query.message.delete()
    parser.rooms_parser.stopped = True
    mkd = await parser.find_mkd_by_id(callback_data.mkd_id)
    task = await _get_task_by_name(callback_data.task_name)
    await query.message.answer(f'Парсинг помещений МКД <b>{mkd.address} ({mkd.cad_num})</b> приостановлен',
                               reply_markup=get_confirm_rooms_parsing_cancel_keyboard(task, callback_data.mkd_id))
    await query.answer()


@router.callback_query(CancelParsingData.filter(F.action == Action.ACCEPT))
async def on_cancel_parsing_accept(query: CallbackQuery, callback_data: CancelParsingData) -> None:
    logger.debug('cancel parsing')
    await query.answer()
    task = await _get_task_by_name(callback_data.task_name)
    task.cancel()
    parser.rooms_parser.stopped = False
    parser.rooms_parser.is_running = False
    await parser.rooms_parser.delete_rooms_by_mkd_id(callback_data.mkd_id)
    mkd = await parser.find_mkd_by_id(callback_data.mkd_id)
    await query.message.answer(
        f'Сбор данных о <a href="{mkd.passport_link}">помещениях</a> МКД <b>{mkd.address} ({mkd.cad_num})</b> успешно отменен')
    await query.message.delete()


@router.callback_query(CancelParsingData.filter(F.action == Action.DECLINE))
async def on_cancel_parsing_decline(query: CallbackQuery, callback_data: CancelParsingData,
                                    state: FSMContext) -> None:
    await query.message.delete()
    parser.rooms_parser.stopped = False
    mkd = await parser.find_mkd_by_id(callback_data.mkd_id)
    task = await _get_task_by_name(callback_data.task_name)
    msg = await query.message.answer(
        f'Сбор данных о <a href="{mkd.passport_link}">помещениях</a> МКД <b>{mkd.address} ({mkd.cad_num})</b> успешно продолжен',
        reply_markup=get_cancel_rooms_parsing_keyboard(task, callback_data.mkd_id)
    )
    await query.answer()
    await state.update_data({'continue_msg_id': msg.message_id})


@router.callback_query(CollectPDFData.filter())
async def on_collect_pdf(query: CallbackQuery, callback_data: CollectPDFData) -> None:
    mkd = await parser.find_mkd_by_id(callback_data.mkd_id)
    msg = await query.message.answer(
        f'Создаю {"паспорт Паспорт_МКД_" if callback_data.action == "passport" else "отчет ОУ_"}{mkd.address}.pdf')
    with suppress(TelegramBadRequest):
        await query.answer()
    btn_pressed = Button.PASSPORT if callback_data.action == 'passport' else Button.CONTROL_INFO
    logger.debug(btn_pressed)
    while IS_DELETING_BUTTON:
        await asyncio.sleep(2.5)
    async with lock:
        await _delete_button_from_message_markup(btn_pressed, query.message)
    files = await get_mkd_pdf_files_by_address(mkd.address)
    if not files[callback_data.action]:
        collector = PDFCollector()
        while collector.is_running:
            await asyncio.sleep(10)
        task = asyncio.create_task(collector.run(callback_data.action, mkd.passport_link, mkd.orgs_link, mkd.address))
        await task
        files[callback_data.action] = task.result()
    doc = FSInputFile(files[callback_data.action])
    await msg.delete()
    await query.message.answer_document(doc)


def get_orgs_string(mkd: MKD, orgs: list[Organization]):
    text = ''
    for org in orgs:
        text += f'<a href="{org.link}">{org.status}: {org.name} ({org.inn})</a>\n'
    text += f'\n<a href="{mkd.orgs_link}">Информация об управлении МКД</a>'
    text += f'\n<a href="{mkd.passport_link}">Электронный паспорт МКД</a>'
    return text


async def _get_task_by_name(task_name: str) -> Task:
    loop = asyncio.get_running_loop()
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        if task.get_name() == task_name:
            return task


async def get_mkd_pdf_files_by_address(address: str) -> dict[Literal['control_info', 'passport'], Path | None]:
    logger.debug(address)
    files: dict[Literal['control_info', 'passport'], Path | None] = {'passport': None, 'control_info': None}
    passport = list(Path(BASE_DIR / 'test_responses').glob(f'Паспорт_МКД_{address.replace("/", "_")}.pdf'))
    if passport:
        files['passport'] = passport[0]
    control_info = list(Path(BASE_DIR / 'test_responses').glob(f'ОУ_{address.replace("/", "_")}.pdf'))
    if control_info:
        files['control_info'] = control_info[0]
    return files


async def _delete_button_from_message_markup(btn: Button, message: Message) -> None:
    # async with lock:
    global IS_DELETING_BUTTON
    logger.debug(IS_DELETING_BUTTON)
    IS_DELETING_BUTTON = True
    try:
        markup = message.reply_markup.model_dump()
        logger.debug(f"del btn call with markup: {markup['inline_keyboard']}")
        _delete_btn_from_markup_dict(markup, btn)
        await message.edit_reply_markup(
            reply_markup=markup
        )
        await asyncio.sleep(2)
    finally:
        IS_DELETING_BUTTON = False


def _delete_btn_from_markup_dict(d: dict[str, list[list[dict[str, str | None]]]], btn: Button) -> None:
    btns = d.get('inline_keyboard')
    for btn_ in btns:
        if btn_[0]['text'] == btn.value:
            btns.remove(btn_)
            return

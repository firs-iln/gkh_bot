import asyncio
from dataclasses import asdict

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from bot.handlers.start import get_orgs_string, MKDState
from bot.keyboards.for_start import get_mkds_keyboard, MKDData, get_mkd_card_keyboard, MenuAction
from parser.mkd import MKDParser
from parser.saver import MKDDataSaver

router = Router()
parser = MKDParser()


@router.message(Command(commands=['infogis']))
@router.message(F.text == MenuAction.MY_MKDS)
async def cmd_infogis(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    logger.info('handle infogis command')
    mkds = await MKDParser.get_all_mkds()
    if len(mkds) == 0:
        await message.answer('Вы еще не собирали информацию ни по одному дому. Для этого нажмите /gisgkh')
    else:
        await message.answer('Пожалуйста, выберите дом из списка', reply_markup=await get_mkds_keyboard(mkds))
    await state.set_state(None)


@router.callback_query(MKDData.filter())
async def on_entering_house_address(query: CallbackQuery, callback_data: MKDData, state: FSMContext) -> None:
    logger.debug('handle infogis')
    msg = await query.message.answer('Обрабатываю запрос...')
    await query.answer()
    coro = await asyncio.to_thread(parser.find_mkd_by_id, callback_data.id)
    mkd = await coro
    orgs = await mkd.orgs
    rooms = await mkd.rooms
    logger.info('mkd data collected')
    text = f'<a href="{mkd.card_link}">МКД</a>: <b>{mkd.address} ({mkd.cad_num})\n\n{parser.get_rooms_report_string(mkd, rooms)}</b>\n\n'
    if 'непосредственное' in mkd.control_method.lower():
        text += 'Непосредственное управление\n'
    text += get_orgs_string(mkd, orgs)
    logger.debug('text formed')
    saver = MKDDataSaver(mkd, orgs, rooms)
    await saver.save_mkd_to_excel()
    await query.message.answer(text, reply_markup=await get_mkd_card_keyboard(mkd))
    await query.message.delete()
    await msg.delete()
    await state.update_data({'mkd': asdict(mkd)})

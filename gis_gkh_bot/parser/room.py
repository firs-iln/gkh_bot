import asyncio
from dataclasses import dataclass, field, asdict
from typing import NoReturn, Literal

import ujson
from aiohttp import ClientSession
from httpx import HTTPStatusError
from jmespath import search
from loguru import logger

from dadata_wrapper.dadataapi import get_address_data, get_address_data_by_id
from .utils import Singleton, extract_digits_from_string, agcm

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/114.0',
    'Accept': 'application/json; charset=utf-8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    # 'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/json;charset=utf-8',
    'Session-GUID': 'd07f811f-d71f-4012-b1ae-70423a292620',
    'State-GUID': '/passport/show',
    'Request-GUID': 'd4d2d381-25ae-4f03-8516-f2bd80d6fcf9',
    'Origin': 'https://dom.gosuslugi.ru',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://dom.gosuslugi.ru/',
    'Cookie': 'JSESSIONID=sPbIrwYqoBL1CROGMyAGG6Cg; __zzatgib-w-gosuslugi=MDA0dC0cTApcfEJcdGswPi17CT4VHThHKHIzd2VrTXdcdF52NmNUbEdIPzs/NSYcQRwaSk5fbxt7Il8qCCRjNV8ZQ2pODWk3XBQ8dWU+R3N0LEBoJmZMYh9JUT9IXl1JEjJiEkBATUcNN0BeN1dhMA8WEU1HFT1WUk9DKGsbcVgwMYTgmw==; cfidsgib-w-gosuslugi=tLBgS2RaNFvkP9IEAMPQM5P1TssZeD0or/Yo7tHb5x4yJ16NunadrJVTQ5BgVYxL81TxDjNx9Upzm18fSJ1iv4tExEQPtra8blpDGAvva7a3SQQSJa4BQIFraGlTqmZjBpfLWP8wu/wWGI4bT+s8MTm6kciMiOwv1GLy; gsscgib-w-gosuslugi=mxF5WK0dh3mUvXOSrzhHqujRfAvrPn3KltDMbF9oGSmVr4ahVcVioH2sBuzevyDWZSQxafw3ie1vf/M8i7u8vynFDR21HrPhUqKNKD63pstJqMRNzGzrkb6h+TtUYD3bdAxnQxfxHysGiU0DobfIp7vl+8ovZO2zAr+XlnyYB9DU0ywKbLrhT9Rq5JUKnIzFd8b2enzeOW0MUkQorq2EuFRnCbsV+ugVNoaCbhgmSyYIpz/5+UA3TzQIyKkSkw==; fgsscgib-w-gosuslugi=lxSlac633bf79820829e366178ca3e64395c0ca0; route_pafo-saiku=d1a877d2a03a4caf638b7c2e185fd06e; suimSessionGuid=d07f811f-d71f-4012-b1ae-70423a292620; route_rest=3b9d5a0fd338a362ba21c7cc70ee9d53; route_pafo-reports=4786a755f3f26ebf8b9f0a573dfcf8d1; route_suim=9cec376355a82e1c2092d0f01142afd1; route_for-robots=43265413dc50268319b9d96a5eec0d80; route_rest-disclosures=cf8db17adc5a09338426cc25326ec16a',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

cookies = {
    'JSESSIONID': 'sPbIrwYqoBL1CROGMyAGG6Cg',
    '__zzatgib-w-gosuslugi': 'MDA0dC0cTApcfEJcdGswPi17CT4VHThHKHIzd2VrTXdcdF52NmNUbEdIPzs/NSYcQRwaSk5fbxt7Il8qCCRjNV8ZQ2pODWk3XBQ8dWU+R3N0LEBoJmZMYh9JUT9IXl1JEjJiEkBATUcNN0BeN1dhMA8WEU1HFT1WUk9DKGsbcVgwMYTgmw==',
    'cfidsgib-w-gosuslugi': 'tLBgS2RaNFvkP9IEAMPQM5P1TssZeD0or/Yo7tHb5x4yJ16NunadrJVTQ5BgVYxL81TxDjNx9Upzm18fSJ1iv4tExEQPtra8blpDGAvva7a3SQQSJa4BQIFraGlTqmZjBpfLWP8wu/wWGI4bT+s8MTm6kciMiOwv1GLy',
    'gsscgib-w-gosuslugi': 'mxF5WK0dh3mUvXOSrzhHqujRfAvrPn3KltDMbF9oGSmVr4ahVcVioH2sBuzevyDWZSQxafw3ie1vf/M8i7u8vynFDR21HrPhUqKNKD63pstJqMRNzGzrkb6h+TtUYD3bdAxnQxfxHysGiU0DobfIp7vl+8ovZO2zAr+XlnyYB9DU0ywKbLrhT9Rq5JUKnIzFd8b2enzeOW0MUkQorq2EuFRnCbsV+ugVNoaCbhgmSyYIpz/5+UA3TzQIyKkSkw==',
    'fgsscgib-w-gosuslugi': 'lxSlac633bf79820829e366178ca3e64395c0ca0',
    'route_pafo-saiku': 'd1a877d2a03a4caf638b7c2e185fd06e',
    'suimSessionGuid': 'd07f811f-d71f-4012-b1ae-70423a292620',
    'route_rest': '3b9d5a0fd338a362ba21c7cc70ee9d53',
    'route_pafo-reports': '4786a755f3f26ebf8b9f0a573dfcf8d1',
    'route_suim': '9cec376355a82e1c2092d0f01142afd1',
    'route_for-robots': '43265413dc50268319b9d96a5eec0d80',
    'route_rest-disclosures': 'cf8db17adc5a09338426cc25326ec16a',
}


@dataclass
class Room:
    id: str = field(default='')
    mkd_id: str = field(default='')
    number: str = field(default='')
    cad_num: str = field(default='')
    ust_num: str = field(default='')
    total_area: float | str = field(default=0.0)
    status: Literal['КВ', 'НЖ', 'ОИ'] = field(default='')
    residential_square: float | str = field(default='')
    rooms_count: int | str = field(default='')
    entrance_number: int | str = field(default='')
    is_emergency: str = field(default='')
    from_rr: str = field(default='')
    address: str = field(default='')
    dadata_number: str = field(default='')
    dadata_cad_num: str = field(default='')
    fias_gar_code: str = field(default='')
    dadata_area: str | float = field(default='')
    floor: str | float = field(default='')
    dadata_mkd_id: str = field(default='')



class RoomsParser(metaclass=Singleton):
    def __init__(self, session: ClientSession):
        self.__session = session
        self.__endpoint_url = 'https://dom.gosuslugi.ru/homemanagement/api/rest/services/passports/search'
        self.__endpoint_data = {"page": 1, "itemsPerPage": 500}
        self.is_running = False
        self.stopped = False

    async def parse_mkd_rooms_by_guid(self, guid: str, mkd):
        self.is_running = True
        if not self.__session:
            self.__session = ClientSession()
        data = await self.__get_rooms_data_by_guid(guid)
        rooms = await self.__collect_rooms(data, mkd, guid)
        self.is_running = False
        return rooms

    async def __collect_rooms(self, data: dict[str, list[dict]], mkd, guid: str) -> list[Room]:
        logger.debug('parse rooms')
        rooms_ = []
        rooms = await self.find_rooms_by_mkd_id(mkd.id)
        if rooms:
            rooms_.extend(rooms)
            res_rooms = [room.number for room in rooms if room.status == 'КВ']
            non_res_rooms = [room.number for room in rooms if room.status != 'КВ']
        else:
            res_rooms, non_res_rooms = [], []
        for item in data.get('residential'):
            while self.stopped:
                await asyncio.sleep(5)
            number = item.get('value')
            if number not in res_rooms:
                room = await self.__parse_room(item, mkd, 'КВ', guid)
                rooms_.append(room)
                logger.debug('Sleep')
                await asyncio.sleep(10)
        for item in data.get('non_residential'):
            while self.stopped:
                await asyncio.sleep(5)
            number = item.get('value')
            if number not in non_res_rooms:
                room = await self.__parse_room(item, mkd, 'НЖ', guid)
                rooms_.append(room)
                logger.debug('Sleep')
                await asyncio.sleep(10)

        return rooms_

    async def __get_rooms_data_by_guid(self, guid: str) -> dict[str, list[dict]]:
        data = {}
        async with self.__session.post(self.__endpoint_url, headers=HEADERS,
                                       json={"houseGuid": guid, 'passportParameterCode': "17",
                                             **self.__endpoint_data}) as response:
            res_data = await response.json(loads=ujson.loads)
            res_data_params = res_data.get('parameters')
            data['residential'] = res_data_params
        async with self.__session.post(self.__endpoint_url, headers=HEADERS,
                                       json={"houseGuid": guid, 'passportParameterCode': "18",
                                             **self.__endpoint_data}) as response:
            non_res_data = await response.json(loads=ujson.loads)
            non_res_data_params = non_res_data.get('parameters')
            data['non_residential'] = non_res_data_params
        return data

    async def __parse_room(self, item: dict, mkd, status: Literal['КВ', 'НЖ'], guid: str) -> Room:
        from_rr = 'Да' if item.get('valueFromRR') else ''
        room = Room(mkd_id=mkd.id, status=status, number=item.get('value'), from_rr=from_rr)
        await self.__get_room_params(room, item.get('paramCode'), guid, mkd.address)
        return room

    async def __get_room_params(self, room: Room, param_code: str, house_guid: str, mkd_addr: str) -> NoReturn:
        async with self.__session.post(self.__endpoint_url, headers=HEADERS, cookies=cookies,
                                       json={"houseGuid": house_guid, 'passportParameterCode': param_code,
                                             **self.__endpoint_data}) as response:
            logger.debug(response.status)
            data = await response.json(loads=ujson.loads)
            if room.status == 'КВ':
                await self.__parse_residential_room(mkd_addr, room, data)
            else:
                await self.__parse_non_residential_room(mkd_addr, room, data)
            await self.__save_room(room)

    async def __parse_residential_room(self, mkd_addr: str, room: Room, data: list[dict]) -> NoReturn:
        room.cad_num = self.__parse_cad_num(data)
        room.ust_num = self.__parse_ust_num(data)
        if room.cad_num:
            room.id = self.__parse_id_by_cad_num(room.cad_num)
        room.is_emergency = self.__parse_is_emergency(data)
        room.rooms_count = self.__parse_rooms_count(data)
        room.residential_square = self.__parse_residential_square(data)
        room.total_area = self.__parse_total_square(data)
        room.entrance_number = self.__parse_entrance_number(data)
        room.address = self.__parse_address(mkd_addr, room)
        self.__parse_dadata_fields(room)
        logger.debug(room.dadata_cad_num)

    async def __parse_non_residential_room(self, mkd_addr: str, room: Room, data: list[dict]) -> NoReturn:
        room.cad_num = self.__parse_cad_num(data)
        room.ust_num = self.__parse_ust_num(data)
        if room.cad_num:
            room.id = self.__parse_id_by_cad_num(room.cad_num)
        room.total_area = self.__parse_total_square(data)
        room.status = self.__parse_status(data)
        room.address = self.__parse_address(mkd_addr, room)
        self.__parse_dadata_fields(room)
        logger.debug(room.dadata_cad_num)

    @staticmethod
    def __parse_cad_num(data: list[dict]) -> str:
        return search('parameters[0].value', data)

    @staticmethod
    def __parse_ust_num(data: list[dict]) -> str:
        return search('parameters[1].value', data)

    @staticmethod
    def __parse_id_by_cad_num(cad_num: str) -> str:
        return cad_num.replace(':', '')

    @staticmethod
    def __parse_entrance_number(data: list[dict]) -> int:
        entrance_num = search('parameters[5].value', data)
        return int(entrance_num) if entrance_num else ''

    @staticmethod
    def __parse_is_emergency(data: list[dict]) -> str:
        is_emergency = bool(search('parameters[6].value', data))
        return 'Да' if is_emergency else ''

    @staticmethod
    def __parse_rooms_count(data: list[dict]) -> int | str:
        rooms_count_str = search('parameters[4].value', data)
        if rooms_count_str:
            return int(extract_digits_from_string(rooms_count_str))
        else:
            return ''

    @staticmethod
    def __parse_residential_square(data: list[dict]) -> float | str:
        residential_square_str = search('parameters[3].value', data)
        if residential_square_str:
            return float(residential_square_str) if residential_square_str.replace('.', '',
                                                                                   1).isdigit() else residential_square_str
        else:
            return ''

    @staticmethod
    def __parse_total_square(data: list[dict]) -> float | str:
        total_square = search('parameters[2].value', data)
        return float(total_square) if total_square else ''

    @staticmethod
    def __parse_status(data: list[dict]) -> Literal['НЖ', 'ОИ']:
        is_public_str = search('parameters[3].value', data)
        if not is_public_str or is_public_str.lower() == 'нет':
            return 'НЖ'
        else:
            return 'ОИ'

    @staticmethod
    def __parse_address(mkd_addr: str, room: Room) -> str:
        if not room.status == 'КВ':
            return f"{mkd_addr}, пом. {room.number}"
        else:
            return f"{mkd_addr}, кв.{room.number}"

    @staticmethod
    def __parse_dadata_fields(room: Room) -> NoReturn:
        try:
            if room.cad_num:
                result = get_address_data_by_id(room.cad_num)
                if result is None:
                    result = get_address_data(room.address)
                    room.fias_gar_code = result.fias_id
                else:
                    room.fias_gar_code = result.flat_fias_id
            else:
                result = get_address_data(room.address)
                room.fias_gar_code = result.fias_id
            room.dadata_area = float(result.flat_area) if result.flat_area else None
            room.floor = result.fias_level
            room.dadata_number = result.flat
            room.dadata_cad_num = result.flat_cadnum
            if result.house_cadnum:
                room.dadata_mkd_id = result.house_cadnum.replace(':', '')
        except HTTPStatusError:
            room.fias_gar_code = 'ОШИБКА'
            room.dadata_area = 'ОШИБКА'
            room.floor = 'ОШИБКА'
            room.dadata_number = 'ОШИБКА'
            room.dadata_cad_num = 'ОШИБКА'
            room.dadata_mkd_id = 'ОШИБКА'

    @staticmethod
    async def find_rooms_by_mkd_id(mkd_id: str) -> list[Room]:
        rooms = []
        rooms_sheet = await RoomsParser.__get_rooms_sheet()
        cells = await rooms_sheet.findall(mkd_id)
        for cell in cells:
            row = await rooms_sheet.row_values(cell.row)
            room = Room(*row)
            rooms.append(room)
        return rooms

    @staticmethod
    async def mkd_has_rooms(mkd_id: str) -> bool:
        rooms_sheet = await RoomsParser.__get_rooms_sheet()
        cells = await rooms_sheet.findall(mkd_id)
        return bool(cells)

    @staticmethod
    async def delete_rooms_by_mkd_id(mkd_id: str) -> None:
        rooms_sheet = await RoomsParser.__get_rooms_sheet()
        cells = await rooms_sheet.findall(mkd_id)
        if cells:
            logger.info(f'Delete {cells[0].row} - {cells[-1].row} rows')
            await rooms_sheet.delete_rows(cells[0].row, cells[-1].row)

    async def __save_room(self, room: Room) -> NoReturn:
        data = asdict(room)
        rooms_sheet = await self.__get_rooms_sheet()
        await rooms_sheet.append_row(values=list(data.values()))
        logger.info(f'Saved {room.cad_num} room')

    @staticmethod
    async def __get_rooms_sheet():
        agc = await agcm.authorize()
        sh = await agc.open_by_url('https://docs.google.com/spreadsheets/d/1kGCdugwpVwuDO5LRC7tOxIkvMt_5iFQlGphLMAL107A/edit#gid=0')
        rooms_sheet = await sh.worksheet('Помещения')
        return rooms_sheet

import math
from dataclasses import dataclass, field, fields, asdict
from typing import NoReturn, Any
from urllib.parse import urlparse, parse_qs

import ujson
from aiogram.types import User
from aiohttp import ClientSession
from async_property import async_property
from httpx import HTTPStatusError
from jmespath import search
from loguru import logger

from dadata_wrapper.dadataapi import get_address_data, get_address_data_by_id, AddressData
from .organization import OrganizationsParser, Organization
from .room import RoomsParser, Room
from .utils import Singleton, agcm


@dataclass
class MKD:
    id: str = field(default='')
    address: str = field(default='')
    cad_num: str = field(default='')
    address_id: str = field(default='')
    total_area: float = field(default=0.0)
    residential_square: float = field(default=0.0)
    built_year: int = field(default=0)
    control_method: str = field(default='')
    inn_uo: str = field(default='')
    inn_rso: str = field(default='')
    card_link: str = field(default='')
    orgs_link: str = field(default='')
    passport_link: str = field(default='')
    subject_code: str = field(default='')
    index: str = field(default='')
    settlement: str = field(default='')
    street: str = field(default='')
    house_num: str = field(default='')
    cad_num_mkd: str = field(default='')
    coords: str = field(default='')

    def __str__(self):
        return f"<b>{self.address}</b>\n\nID: <b>{self.id}</b>\nКадастровый номер: <b>{self.cad_num}</b>\nID адреса: <b>{self.address_id}</b>\nОбщая площадь, кв.м: <b>{self.total_area}</b>\nЖилая площадь: <b>{self.residential_square}</b>\nГод постройки: <b>{self.built_year}</b>\nСпособ управления: <b>{self.control_method}</b>\nИНН УО: <b>{self.inn_uo}</b>\nИНН РСО: <b>{self.inn_rso}</b>\nСсылка на карточку дома: <b>{self.card_link}</b>\nСсылка на паспорт дома: <b>{self.passport_link}</b>\n"

    @async_property
    async def orgs(self) -> list[Organization]:
        orgs = []
        orgs_sheet = await OrganizationsParser.get_orgs_sheet()
        for inn in f"{self.inn_uo};{self.inn_rso}".split(';'):
            cell = await orgs_sheet.find(inn)
            row = await orgs_sheet.row_values(cell.row)
            org = Organization(*row)
            orgs.append(org)
        return orgs

    @async_property
    async def rooms(self) -> list[Room]:
        rooms = await RoomsParser.find_rooms_by_mkd_id(self.id)
        return rooms

    @async_property
    async def has_rooms(self) -> bool:
        return await RoomsParser.mkd_has_rooms(self.id)


class MKDParser(metaclass=Singleton):
    def __init__(self):
        self.__session: ClientSession = None
        self.orgs_parser = None
        self.rooms_parser = None
        self.orgs = []
        self.mkd = MKD()
        self.__base_mkd_endpoint_url = 'https://dom.gosuslugi.ru/homemanagement/api/rest/services/houses/public/1'
        self.__headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0',
            'Accept': 'application/json; charset=utf-8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Content-Type': 'application/json;charset=utf-8',
            'Session-GUID': 'c760b337-cc1e-45a5-b02e-d3a2a05bc31a',
            'State-GUID': '/houses',
            'Request-GUID': 'd8158b4c-71cf-4c6d-a3b6-59d14d8ffcd8',
            'Origin': 'https://dom.gosuslugi.ru',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://dom.gosuslugi.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }

    async def run(self, link: str = None, address: str = None) -> MKD:
        # tasks = []
        if not self.__session:
            self.__session = ClientSession(trust_env=True)
            self.orgs_parser = OrganizationsParser(self.__session)
            self.rooms_parser = RoomsParser(self.__session)
        mkd = await self.__find_mkd_by_link(link)
        if not mkd:
            mkd = MKD()
            mkd.card_link = link
            mkd.address = address
        data = await self.__get_mkd_card_data(mkd)
        if data is None:
            for field_ in fields(mkd):
                setattr(mkd, field_.name, 'ОШИБКА') if field_.name != 'address' else None
        else:
            await self.__parse_characteristics(data, mkd)
        logger.info(asdict(mkd))
        return mkd

    async def __find_mkd_by_link(self, link: str) -> MKD | None:
        if not link:
            return None
        mkd_sheet = await self.__get_mkd_sheet()
        cell = await mkd_sheet.find(link)
        if not cell:
            return None
        else:
            row = await mkd_sheet.row_values(cell.row)
            mkd = MKD(*row)
            return mkd

    async def __get_mkd_card_data(self, mkd: MKD) -> dict | None:
        if not mkd.card_link and mkd.address:
            try:
                result = get_address_data(mkd.address)
                if 'Санкт-Петербург' in result.result and 'литер' not in result.result:
                    result = get_address_data(f"{result.result} литер А")
                region_id = result.region_fias_id
                house_cad_num = result.house_cadnum
            except HTTPStatusError:
                return None
            mkd.card_link = await self.__find_house_link_by_region_and_cad_num(region_id, house_cad_num)
        guid = self.parse_guid_from_card_link(mkd.card_link)
        async with self.__session.get(f"{self.__base_mkd_endpoint_url}/{guid}") as response:
            data = await response.json(loads=ujson.loads)
            return data

    async def __find_house_link_by_region_and_cad_num(self, region_id: str, house_cad_num: str) -> str:
        url = f'https://dom.gosuslugi.ru/homemanagement/api/rest/services/houses/public/searchByAddress?pageIndex=1&elementsPerPage=10'
        data = {"regionCode": region_id, "fiasHouseCodeList": None, "estStatus": None,
                "strStatus": None, "calcCount": True, "houseConditionRefList": None, "houseTypeRefList": None,
                "houseManagementTypeRefList": None, "cadastreNumber": house_cad_num, "oktmo": None,
                "statuses": ["APPROVED"], "regionProperty": None, "municipalProperty": None, "hostelTypeCodes": None}
        async with self.__session.post(url, json=data, headers=self.__headers) as response:
            res = await response.json(loads=ujson.loads)
            item = res['items'][0]
            link = f'https://dom.gosuslugi.ru/#!/house-view?guid={item.get("guid")}&typeCode=1'
            return link


    @staticmethod
    def parse_guid_from_card_link(link: str) -> str:
        parsed_url = urlparse(link)
        queries = parse_qs(parsed_url.fragment.split('?')[1])
        return queries.get('guid')[0]

    async def __parse_characteristics(self, data: dict[str, Any], mkd: MKD) -> NoReturn:
        logger.info('parse characteristics')
        orgs: list[Organization] = []
        mkd.address = self.__parse_address(data)
        mkd.address_id = self.__parse_address_id(data)
        mkd.control_method = self.__parse_control_method(data)
        mkd.cad_num = self.__parse_cad_num(data)
        if mkd.cad_num:
            mkd.id = mkd.cad_num.replace(':', '')
        mkd.orgs_link = self.__parse_orgs_link(data)
        mkd.passport_link = self.__parse_passport_link(mkd)
        mkd.total_area = self.__parse_total_square(data)
        mkd.residential_square = self.__parse_residential_square(data)
        mkd.built_year = self.__parse_built_year(data)
        mkd.inn_uo = await self.__parse_inn_uo(data, orgs)
        mkd.inn_rso = await self.__parse_inn_rso(data, orgs)
        self.__parse_dadata_fields(mkd)
        await self.save_mkd_data(mkd)
        await self.orgs_parser.save_orgs_data(orgs)

    @staticmethod
    def __parse_address(data: dict) -> str:
        return search('address.formattedAddress', data)

    @staticmethod
    def __parse_address_id(data: dict) -> str:
        return search('address.house.guid', data)

    @staticmethod
    def __parse_control_method(data: dict) -> str:
        return search('houseManagementType.houseManagementTypeName', data)

    @staticmethod
    def __parse_cad_num(data: dict) -> str:
        return search('cadastreNumber', data)

    @staticmethod
    def __parse_orgs_link(data: dict) -> str:
        fias_house_code = search('address.house.guid', data)
        house_giud = search('guid', data)
        org_root_guid = search('managementOrganization.registryOrganizationRootEntityGuid', data)
        url = f"https://dom.gosuslugi.ru/#!/mkd?fiasHouseCode={fias_house_code}&houseGuid={house_giud}&orgRootGuid={org_root_guid}"
        return url

    @staticmethod
    def __parse_total_square(data: dict) -> float | str:
        total_square = search('totalSquare', data)
        return float(total_square) if total_square else ''

    @staticmethod
    def __parse_residential_square(data: dict) -> float | str:
        res_square = search('residentialSquare', data)
        return float(res_square) if res_square else ''

    @staticmethod
    def __parse_built_year(data: dict) -> int:
        built_year = search('buildingYear', data)
        if not built_year:
            built_year = search('operationYear', data)
        return int(built_year)

    async def __get_orgs_by_inns(self, mkd: MKD) -> NoReturn:
        inns = [mkd.inn_uo]
        inns.extend(mkd.inn_rso.split(';'))
        self.orgs = await self.orgs_parser.find_orgs_by_inns(inns)

    async def __parse_inn_uo(self, data: dict, orgs: list[Organization]) -> str:
        guid = search('managementOrganization.guid', data)
        if not guid:
            return ''
        org = await self.orgs_parser.parse_org_by_guid('УО', guid)
        orgs.append(org)
        return org.inn

    async def __parse_inn_rso(self, data: dict, orgs: list[Organization]) -> str:
        inn_rso_str = ';'
        inns = []
        orgs_ = search('resourceProvisionOrganizationList', data)
        if not orgs_:
            return ''
        for organization in orgs_:
            guid = search('guid', organization)
            org = await self.orgs_parser.parse_org_by_guid('РСО', guid)
            orgs.append(org)
            inns.append(org.inn)
        return inn_rso_str.join(inns)

    def __parse_passport_link(self, mkd: MKD) -> str:
        return f"https://dom.gosuslugi.ru/#!/passport/show?houseGuid={self.parse_guid_from_card_link(mkd.card_link)}"

    @classmethod
    def __parse_dadata_fields(cls, mkd: MKD) -> str:
        try:
            result = get_address_data_by_id(mkd.cad_num)
        except HTTPStatusError:
            cls.__set_mkd_dadata_error_fields(mkd)
        else:
            if result:
                cls.__set_mkd_dadata_fields(result, mkd)
            else:
                cls.__set_mkd_dadata_error_fields(mkd)

    @staticmethod
    def __set_mkd_dadata_error_fields(mkd: MKD) -> NoReturn:
        mkd.subject_code = 'ОШИБКА'
        mkd.index = 'ОШИБКА'
        mkd.settlement = 'ОШИБКА'
        mkd.street = 'ОШИБКА'
        mkd.house_num = 'ОШИБКА'
        mkd.cad_num_mkd = 'ОШИБКА'
        mkd.coords = 'ОШИБКА'

    @staticmethod
    def __set_mkd_dadata_fields(result: AddressData, mkd: MKD) -> NoReturn:
        mkd.subject_code = result.region_kladr_id.replace('0', '')
        mkd.index = result.postal_code
        mkd.settlement = result.city_with_type
        mkd.street = result.street_with_type
        mkd.house_num = result.house
        mkd.cad_num_mkd = result.house_cadnum
        mkd.coords = f"https://maps.yandex.ru/?text={result.geo_lat},{result.geo_lon}"

    async def save_mkd_data(self, mkd: MKD) -> NoReturn:
        logger.debug('Save mkd to gsheets')
        data = asdict(mkd)
        mkd_sheet = await self.__get_mkd_sheet()
        cell = await mkd_sheet.find(mkd.card_link)
        if cell:
            row = await mkd_sheet.row_values(cell.row)
            if row[0] == '':
                await mkd_sheet.delete_row(cell.row)
                await mkd_sheet.append_row(values=list(data.values()))
        else:
            await mkd_sheet.append_row(values=list(data.values()))

    def get_rooms_report_string(self, mkd: MKD, rooms: list[Room]) -> str:
        if rooms:
            text = f'Помещения из <a href="{mkd.passport_link}">эл.паспорта МКД</a> (пп.17;18):\nСтатус - Росреестр / УО = всего\n'
            rooms_pairs = self.__get_rooms_pairs(rooms)
            for rooms_pair, status in zip(
                    rooms_pairs,
                    ['КВ', 'НЖ', 'ОИ']):
                text += f"{status} -  "
                rr_square = self.__get_rooms_square(rooms_pair[0])
                square = self.__get_rooms_square(rooms_pair[1])
                text += self.__get_rooms_pair_report_string(rr_square, square, rooms_pair)
        else:
            text = '<b>Данные о помещениях еще не собирались</b>'
        return text

    @staticmethod
    def __get_rooms_pairs(rooms: list[Room]) -> list[list[list[Room]]]:
        rr_res_rooms = [room for room in rooms if room.status == 'КВ' and room.from_rr.lower() == 'да']
        res_rooms = [room for room in rooms if room.status == 'КВ' and room.from_rr.lower() != 'да']
        rr_non_res_rooms = [room for room in rooms if room.status == 'НЖ' and room.from_rr.lower() == 'да']
        non_res_rooms = [room for room in rooms if room.status == 'НЖ' and room.from_rr.lower() != 'да']
        rr_public_rooms = [room for room in rooms if room.status == 'ОИ' and room.from_rr.lower() == 'да']
        public_rooms = [room for room in rooms if room.status == 'ОИ' and room.from_rr.lower() != 'да']
        return [[rr_res_rooms, res_rooms], [rr_non_res_rooms, non_res_rooms], [rr_public_rooms, public_rooms]]

    @staticmethod
    def __get_rooms_square(rooms: list[Room]) -> float:
        rooms_square = 0
        for room in rooms:
            rooms_square += float(
                str(room.total_area).replace(',', '.')) if room.total_area != '' else 0
        return math.floor(rooms_square * 100) / 100.0

    @staticmethod
    def __get_rooms_pair_report_string(rr_square: float, square: float, rooms_pair: list[list[Room]]):
        logger.debug(len(rooms_pair[0]))
        logger.debug(len(rooms_pair[1]))
        return f"{f'{len(rooms_pair[0])} ({rr_square} м2)' if rooms_pair[0] else 'нет'} / {f'{len(rooms_pair[1])} ({square} м2)' if rooms_pair[1] else 'нет'} = {len(rooms_pair[0]) + len(rooms_pair[1])} ({rr_square + square} м2)\n"

    @staticmethod
    async def get_all_mkds() -> list[MKD]:
        mkds = []
        mkds_sheet = await MKDParser.__get_mkd_sheet()
        rows_count = mkds_sheet.row_count
        logger.debug(rows_count)
        for row_num in range(2, rows_count + 1):
            row = await mkds_sheet.row_values(row_num)
            if not row:
                break
            logger.info(row)
            mkds.append(MKD(*row))
        return mkds

    async def find_mkd_by_id(self, id_: str) -> MKD:
        if not self.__session:
            self.__session = ClientSession()
            self.orgs_parser = OrganizationsParser(self.__session)
            self.rooms_parser = RoomsParser(self.__session)
        mkds_sheet = await MKDParser.__get_mkd_sheet()
        for row_num in range(2, mkds_sheet.row_count + 1):
            row = await mkds_sheet.row_values(row_num)
            if id_ in row:
                return MKD(*row)

    @staticmethod
    async def __get_mkd_sheet():
        agc = await agcm.authorize()
        sh = await agc.open_by_url(
            'https://docs.google.com/spreadsheets/d/1kGCdugwpVwuDO5LRC7tOxIkvMt_5iFQlGphLMAL107A/edit#gid=0')
        mkd_sheet = await sh.worksheet('МКД')
        return mkd_sheet

    @staticmethod
    async def write_user_data(user: User, entry_datetime: str) -> NoReturn:
        agc = await agcm.authorize()
        sh = await agc.open_by_url(
            'https://docs.google.com/spreadsheets/d/1kGCdugwpVwuDO5LRC7tOxIkvMt_5iFQlGphLMAL107A/edit#gid=0')
        users_sheet = await sh.worksheet('Журнал')
        row = [entry_datetime, user.username, user.first_name]
        await users_sheet.append_row(row)

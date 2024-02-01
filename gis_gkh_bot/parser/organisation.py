import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import NoReturn, Literal

import ujson
from aiohttp import ClientSession
from async_lru import alru_cache
from jmespath import search
from loguru import logger

from .utils import Singleton, extract_digits_from_string, agcm


@dataclass
class Organization:
    inn: str = field(default='')
    status: Literal['УО', 'РСО'] = field(default='')
    name: str = field(default='')
    region: str = field(default='')
    ogrn: str = field(default='')
    reg_date: str = field(default='')
    kpp: str = field(default='')
    email: str = field(default='')
    phone: str = field(default='')
    dp_phone: str = field(default='')
    chief_name: str = field(default='')
    chief_position: str = field(default='')
    all_funcs: str = field(default='')
    link: str = field(default='')

    def __str__(self):
        return f"<b>{self.name}</b>\n\nИНН: <b>{self.inn}</b>\nСтатус: <b>{self.status}</b>\nСубъект РФ: <b>{self.region}</b>\nОГРН: <b>{self.ogrn}</b>\nДата гос. регистрации: <b>{self.reg_date}</b>\nКПП: <b>{self.kpp}</b>\nE-mail: <b>{self.email}</b>\nТелефон: <b>+{self.phone}</b>\nТелефоны диспетчерской: <b>{';'.join(f'+{phone}' for phone in self.dp_phone.split(';'))}</b>\nФИО руководителя: <b>{self.chief_name}</b>\nДолжность руководителя: <b>{self.chief_position}</b>\nСсылка: <b>{self.link}</b>\n"


class OrganizationsParser(metaclass=Singleton):
    def __init__(self, session: ClientSession):
        self.__session = session
        self.__base_org_endpoint_url = 'https://dom.gosuslugi.ru/ppa/api/rest/services/ppa/public/organizations'

    @alru_cache(128)
    async def parse_org_by_guid(self, status: Literal['УО', 'РСО'], guid: str) -> NoReturn:
        org = await self.__find_org_by_link(f"https://dom.gosuslugi.ru/#!/organizationView/{guid}")
        if not org:
            org = Organization()
            org.status = status
            org.link = f"https://dom.gosuslugi.ru/#!/organizationView/{guid}"
            data = await self.__get_org_data_by_guid(guid)
            await self.__parse_org_data(org, data)
            await asyncio.sleep(15)
        logger.debug(org.chief_name)
        return org

    @staticmethod
    @alru_cache(128)
    async def find_orgs_by_inns(inns: list[str]) -> list[Organization]:
        orgs = []
        orgs_sheet = await OrganizationsParser.get_orgs_sheet()
        logger.debug(await orgs_sheet.col_values(1))
        for inn in inns:
            cell = await orgs_sheet.find(inn)
            row = await orgs_sheet.row_values(cell.row)
            org = Organization(*row)
            orgs.append(org)
        logger.info(f"{len(orgs)}/{len(inns)} orgs found")
        return orgs

    @staticmethod
    @alru_cache(128)
    async def __find_org_by_link(link: str) -> Organization | None:
        orgs_sheet = await OrganizationsParser.get_orgs_sheet()
        cell = await orgs_sheet.find(link)
        if not cell:
            return None
        else:
            row = await orgs_sheet.row_values(cell.row)
            org = Organization(*row)
            return org

    @alru_cache(128)
    async def __get_org_data_by_guid(self, guid: str) -> dict:
        async with self.__session.get(f"{self.__base_org_endpoint_url}/orgByGuid?organizationGuid={guid}") as response:
            data = await response.json(loads=ujson.loads)
        async with self.__session.post(f"{self.__base_org_endpoint_url}/additionalinfo",
                                       json={'organizationGuids': [guid]}) as response:
            additional_info = await response.json(loads=ujson.loads)
            data['additional_info'] = additional_info['additionalInfos'][0]
        return data

    async def __parse_org_data(self, org: Organization, data: dict) -> NoReturn:
        org.name = self.__parse_name(data)
        org.kpp = self.__parse_kpp(data)
        org.ogrn = self.__parse_ogrn(data)
        org.inn = self.__parse_inn(data)
        org.email = self.__parse_email(data)
        org.phone = self.__parse_phone(data)
        org.dp_phone = self.__parse_dp_phones(data)
        org.region = self.__parse_region(data)
        org.chief_name = self.__parse_chief_name(data)
        org.chief_position = self.__parse_chief_position(data)
        org.reg_date = self.__parse_reg_date(data)
        org.all_funcs = self.__parse_all_funcs(data)

    @staticmethod
    def __parse_name(data: dict) -> str:
        return search('shortName', data)

    @staticmethod
    def __parse_kpp(data: dict) -> str:
        return search('kpp', data)

    @staticmethod
    def __parse_ogrn(data: dict) -> str:
        return search('ogrn', data)

    @staticmethod
    def __parse_inn(data: dict) -> str:
        return search('inn', data)

    @staticmethod
    def __parse_email(data: dict) -> str:
        return search('orgEmail', data)

    @staticmethod
    def __parse_phone(data: dict) -> str:
        return extract_digits_from_string(search('phone', data))

    @staticmethod
    def __parse_dp_phones(data: dict) -> str:
        phones_str = ';'
        phones = search('additional_info.dispatcherPhones', data)
        return phones_str.join(phones)

    @staticmethod
    def __parse_region(data: dict) -> str:
        off_name = search('factualAddress.region.offName', data)
        if off_name in ('Санкт-Петербург', 'Москва', 'Севастополь'):
            return off_name
        else:
            return f"{off_name} {search('factualAddress.region.shortName', data)}"

    @staticmethod
    def __parse_chief_name(data: dict) -> str:
        return search('additional_info.chiefInfo.fio', data)

    @staticmethod
    def __parse_chief_position(data: dict) -> str:
        return search('additional_info.chiefInfo.position', data)

    @staticmethod
    def __parse_reg_date(data: dict) -> str:
        reg_date = search('stateRegistrationDate', data)
        if not reg_date:
            return ''
        date = datetime.strptime(reg_date, '%Y-%m-%d %H:%M:%S')
        return date.strftime('%d.%m.%Y')

    @staticmethod
    def __parse_all_funcs(data: dict) -> str:
        funcs_str = ';'
        funcs_parts = []
        roles = search('organizationRoles', data)
        for role in roles:
            role_name = search('role.organizationRoleName', role)
            if role_name == 'Ресурсоснабжающая организация':
                role_name = 'РСО'
            elif role_name == 'Управляющая организация':
                role_name = 'УО'
            elif role_name == 'Товарищество собственников жилья':
                role_name = 'ТСЖ'
            address = search('house.formattedAddress', role)
            if not address and search('region', role):
                off_name = search('region.offName', role)
                if off_name in ('Санкт-Петербург', 'Москва', 'Севастополь'):
                    address = off_name
                else:
                    address = f"{off_name} {search('region.shortName', role)}"
            else:
                address = 'Не указывается'
            funcs_parts.append(f"{role_name}={address}")
        return funcs_str.join(funcs_parts)

    async def save_orgs_data(self, orgs: list[Organization]) -> NoReturn:
        orgs_sheet = await self.get_orgs_sheet()
        data = [list(asdict(org).values()) for org in orgs if not await self.__find_org_by_link(org.link)]
        logger.debug(f"{len(data)} orgs to save")
        if len(data) > 0:
            await orgs_sheet.append_rows(values=data)

    @staticmethod
    async def get_orgs_sheet():
        agc = await agcm.authorize()
        sh = await agc.open_by_url('https://docs.google.com/spreadsheets/d/1-ykWC2wuPGOKI9Zqge8EE0tGcPki9s8uJrOM3Ti_yI8/')
        orgs_sheet = await sh.worksheet('Организации')
        return orgs_sheet

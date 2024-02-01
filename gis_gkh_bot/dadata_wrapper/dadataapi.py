import json
import os
from functools import lru_cache

from cachetools.func import ttl_cache
from dadata import Dadata
from loguru import logger

token = os.environ.get("DADATA_TOKEN")
secret = os.environ.get("DADATA_SECRET")
dadata = Dadata(token, secret)


@ttl_cache(maxsize=128, ttl=600)
def get_address_data(address):
    print('dadataapi get_address_data', address)
    print(f'dadataapi: поиск адреса {address}')
    dadata_service = Dadata(token, secret)
    result = dadata_service.clean("address", address)
    return AddressData(result) if result else None


@ttl_cache(maxsize=128, ttl=600)
def get_address_data_by_id(id_: str):
    print('dadataapi get_address_data_by_id')
    print(f'dadataapi: поиск по КадНомеру: {id_}')
    result = dadata.find_by_id('address', id_)
    print(len(result))
    print(result)
    return AddressData(result[0]['data']) if result else None


@ttl_cache(maxsize=128, ttl=600)
def get_organization_by_inn(inn):
    print(f'dadataapi: поиск ИНН {inn}')
    dadata_service = Dadata(token, secret)
    result = dadata_service.find_by_id('party', inn, 1, branch_type='MAIN')
    with open('./test_responses/dadata_org.json', 'w') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    if result:
        return CompanyData(result[0])
    else:
        return None


class AddressData:
    def __init__(self, data):
        self.source = data.get('source')
        self.result = data.get('result')
        self.postal_code = data.get('postal_code')
        self.country = data.get('country')
        self.country_iso_code = data.get('country_iso_code')
        self.federal_district = data.get('federal_district')
        self.region_fias_id = data.get('region_fias_id')
        self.region_kladr_id = data.get('region_kladr_id')
        self.region_iso_code = data.get('region_iso_code')
        self.region_with_type = data.get('region_with_type')
        self.region_type = data.get('region_type')
        self.region_type_full = data.get('region_type_full')
        self.region = data.get('region')
        self.area_fias_id = data.get('area_fias_id')
        self.area_kladr_id = data.get('area_kladr_id')
        self.area_with_type = data.get('area_with_type')
        self.area_type = data.get('area_type')
        self.area_type_full = data.get('area_type_full')
        self.area = data.get('area')
        self.city_fias_id = data.get('city_fias_id')
        self.city_kladr_id = data.get('city_kladr_id')
        self.city_with_type = data.get('city_with_type')
        self.city_type = data.get('city_type')
        self.city_type_full = data.get('city_type_full')
        self.city = data.get('city')
        self.city_area = data.get('city_area')
        self.city_district_fias_id = data.get('city_district_fias_id')
        self.city_district_kladr_id = data.get('city_district_kladr_id')
        self.city_district_with_type = data.get('city_district_with_type')
        self.city_district_type = data.get('city_district_type')
        self.city_district_type_full = data.get('city_district_type_full')
        self.city_district = data.get('city_district')
        self.settlement_fias_id = data.get('settlement_fias_id')
        self.settlement_kladr_id = data.get('settlement_kladr_id')
        self.settlement_with_type = data.get('settlement_with_type')
        self.settlement_type = data.get('settlement_type')
        self.settlement_type_full = data.get('settlement_type_full')
        self.settlement = data.get('settlement')
        self.street_fias_id = data.get('street_fias_id')
        self.street_kladr_id = data.get('street_kladr_id')
        self.street_with_type = data.get('street_with_type')
        self.street_type = data.get('street_type')
        self.street_type_full = data.get('street_type_full')
        self.street = data.get('street')
        self.stead_fias_id = data.get('stead_fias_id')
        self.stead_kladr_id = data.get('stead_kladr_id')
        self.stead_cadnum = data.get('stead_cadnum')
        self.stead_type = data.get('stead_type')
        self.stead_type_full = data.get('stead_type_full')
        self.stead = data.get('stead')
        self.house_fias_id = data.get('house_fias_id')
        self.house_kladr_id = data.get('house_kladr_id')
        self.house_cadnum = data.get('house_cadnum')
        self.house_type = data.get('house_type')
        self.house_type_full = data.get('house_type_full')
        self.house = data.get('house')
        self.block_type = data.get('block_type')
        self.block_type_full = data.get('block_type_full')
        self.block = data.get('block')
        self.entrance = data.get('entrance')
        self.floor = data.get('floor')
        self.flat_fias_id = data.get('flat_fias_id')
        self.flat_cadnum = data.get('flat_cadnum')
        self.flat_type = data.get('flat_type')
        self.flat_type_full = data.get('flat_type_full')
        self.flat = data.get('flat')
        self.flat_area = data.get('flat_area')
        self.square_meter_price = data.get('square_meter_price')
        self.flat_price = data.get('flat_price')
        self.postal_box = data.get('postal_box')
        self.fias_id = data.get('fias_id')
        self.fias_level = data.get('fias_level')
        self.fias_actuality_state = data.get('fias_actuality_state')
        self.kladr_id = data.get('kladr_id')
        self.capital_marker = data.get('capital_marker')
        self.okato = data.get('okato')
        self.oktmo = data.get('oktmo')
        self.tax_office = data.get('tax_office')
        self.tax_office_legal = data.get('tax_office_legal')
        self.timezone = data.get('timezone')
        self.geo_lat = data.get('geo_lat')
        self.geo_lon = data.get('geo_lon')
        self.beltway_hit = data.get('beltway_hit')
        self.beltway_distance = data.get('beltway_distance')
        self.qc_geo = data.get('qc_geo')
        self.qc_complete = data.get('qc_complete')
        self.qc_house = data.get('qc_house')
        self.qc = data.get('qc')
        self.unparsed_parts = data.get('unparsed_parts')
        self.metro = data.get('metro')


class CompanyData:
    def __init__(self, data):
        self.value = data['value']
        self.unrestricted_value = data['unrestricted_value']
        self.kpp = data['data']['kpp']
        self.capital = data['data']['capital']
        self.management = data['data']['management']
        if self.management:
            self.eio_fio = data['data']['management']['name']
            self.eio_position = data['data']['management']['post']
        else:
            self.eio_fio = ''
            self.eio_position = ''
        self.founders = data['data']['founders']
        self.managers = data['data']['managers']
        self.predecessors = data['data']['predecessors']
        self.successors = data['data']['successors']
        self.branch_type = data['data']['branch_type']
        self.branch_count = data['data']['branch_count']
        self.source = data['data']['source']
        self.hid = data['data']['hid']
        self.type = data['data']['type']
        self.state = data['data']['state']
        self.opf = data['data']['opf']
        self.name = data['data']['name']
        self.short_name = data['data']['name']['short_with_opf']
        self.inn = data['data']['inn']
        self.ogrn = data['data']['ogrn']
        self.okpo = data['data']['okpo']
        self.okato = data['data']['okato']
        self.oktmo = data['data']['oktmo']
        self.okogu = data['data']['okogu']
        self.okfs = data['data']['okfs']
        self.okved = data['data']['okved']
        self.okveds = data['data']['okveds']
        self.authorities = data['data']['authorities']
        self.documents = data['data']['documents']
        self.licenses = data['data']['licenses']
        self.finance = data['data']['finance']
        self.address = data['data']['address']
        self.phones = data['data']['phones']
        self.emails = data['data']['emails']
        self.ogrn_date = data['data']['ogrn_date']
        self.okved_type = data['data']['okved_type']
        self.employee_count = data['data']['employee_count']


if __name__ == '__main__':
    x = get_address_data('Санкт Петербург ул Марата д 40 кв.3')
    print(f'{x.postal_code}, {x.street_type}.{x.street}, {x.house_type}.{x.house}, {x.flat_type}.{x.flat}')

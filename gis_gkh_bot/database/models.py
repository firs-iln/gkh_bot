from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column

from datetime import datetime, date

from .enums import UserRolesEnum, ExecutorStatusEnum, OrganizationStatusEnum


class Base(DeclarativeBase):
    pass


class MKD(Base):
    __tablename__ = 'mkds'

    id: Mapped[str] = mapped_column(primary_key=True)
    address: Mapped[str]
    cad_id: Mapped[str]
    address_id: Mapped[str]
    total_area: Mapped[Optional[float]]
    total_flats_area: Mapped[Optional[float]]
    year_of_building: Mapped[Optional[int]]
    way_of_administration: Mapped[Optional[str]]
    management_organisation_inn: Mapped[Optional[str]]
    rso_inn: Mapped[Optional[str]]
    house_view_link: Mapped[Optional[str]]
    orgs_link: Mapped[Optional[str]]
    passport_link: Mapped[Optional[str]]
    region_code: Mapped[Optional[str]]
    postal_code: Mapped[Optional[str]]
    city: Mapped[Optional[str]]
    street: Mapped[Optional[str]]
    building_number: Mapped[Optional[str]]
    cad_num_mkd: Mapped[Optional[str]]
    yandex_maps_link: Mapped[Optional[str]]

    floors_count: Mapped[Optional[int]]
    entrances_count: Mapped[Optional[int]]
    elevators_count: Mapped[Optional[int]]
    land_cad_id: Mapped[Optional[str]]
    land_area: Mapped[Optional[float]]


class Organization(Base):
    __tablename__ = 'organizations'

    organization_inn: Mapped[str] = mapped_column(primary_key=True)
    executor_status: Mapped[ExecutorStatusEnum]
    organization_name: Mapped[str]
    region_name: Mapped[str]
    orgn: Mapped[str]

    registered_date: Mapped[Optional[date]]
    kpp: Mapped[Optional[str]]
    email: Mapped[Optional[str]]
    contacting_phone: Mapped[Optional[str]]
    dispatcher_phone: Mapped[Optional[str]]
    director_names: Mapped[Optional[str]]
    director_post: Mapped[Optional[str]]
    all_functions: Mapped[Optional[str]]
    organization_view_link: Mapped[Optional[str]]
    status: Mapped[Optional[OrganizationStatusEnum]]
    organization_name_short: Mapped[Optional[str]]
    ogrn_dadata: Mapped[Optional[str]]
    eio_names: Mapped[Optional[str]]
    eio_post: Mapped[Optional[str]]
    phone_dadata: Mapped[Optional[str]]
    email_dadata: Mapped[Optional[str]]
    dadata_link: Mapped[Optional[str]]


class Room(Base):
    __tablename__ = 'rooms'

    id: Mapped[str] = mapped_column(primary_key=True)

    mkd_id: Mapped[str] = mapped_column(ForeignKey('mkds.id'), nullable=False)
    number: Mapped[str]
    cad_id: Mapped[str]
    statutory_number: Mapped[Optional[str]]
    total_area: Mapped[Optional[float]]
    status: Mapped[Optional[str]]
    living_area: Mapped[Optional[float]]
    rooms_count: Mapped[Optional[int]]
    entrance_number: Mapped[Optional[int]]
    is_emergency: Mapped[Optional[bool]]
    reestr: Mapped[Optional[str]]
    address: Mapped[Optional[str]]
    room_number: Mapped[Optional[str]]
    cadnum: Mapped[Optional[str]]
    fias_code: Mapped[Optional[str]]
    area: Mapped[Optional[float]]
    fias_level: Mapped[Optional[str]]
    id_mkd: Mapped[Optional[str]]


class Session(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_datetime: Mapped[datetime]
    username: Mapped[str] = mapped_column(ForeignKey('users.username'))
    name: Mapped[str]


class User(Base):
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(primary_key=True)
    role: Mapped[UserRolesEnum] = mapped_column(default=UserRolesEnum.USER)


class DUOSS(Base):
    __tablename__ = 'duoss'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mkd: Mapped[str] = mapped_column(ForeignKey('mkds.id'))
    partition: Mapped[int] = mapped_column(ForeignKey('partitions.partition_code'), nullable=False)
    document_type: Mapped[str]
    document_number: Mapped[Optional[str]]
    document_date: Mapped[Optional[date]]
    comment: Mapped[Optional[str]]
    mkd_address: Mapped[Optional[str]]


class Partition(Base):
    __tablename__ = 'partitions'

    partition_code: Mapped[int] = mapped_column(primary_key=True)
    partition_name: Mapped[str] = mapped_column(nullable=False)

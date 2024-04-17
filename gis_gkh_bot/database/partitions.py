from typing import Optional, Union

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from .models import Partition

partitions = [
    (0, "Карточка МКД"),
    (1, "Общая информация"),
    (2, "Конструктивные элементы"),
    (3, "Выполняемые работы по СРОИ"),
    (4, "Оказываемые коммунальные услуги"),
    (5, "Использование общего имущества"),
    (6, "Информация о капитальном ремонте"),
    (7, "Информация об общих собраниях"),
    (8, "Отчет по управлению"),
]


def insert_partitions(engine: Union[Engine, AsyncEngine], partitions_data: Optional[list[tuple[int, str]]] = None):
    if partitions_data is None:
        partitions_data = partitions

    objs = [
        Partition(partition_code=x[0], partition_name=x[1]) for x in partitions_data
    ]

    session = sessionmaker(bind=engine)()  # type: ignore
    for obj in objs:
        session.add(obj)
    session.commit()
    session.close()
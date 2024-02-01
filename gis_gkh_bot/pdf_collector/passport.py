import asyncio
from typing import NoReturn

from playwright.async_api import Page, ElementHandle, PdfMargins
from loguru import logger

from parser.utils import Singleton, BASE_DIR
from .utils import save_pdf_file


class PassportInfoCollector:
    def __init__(self, passport_link: str, page: Page, address: str):
        self.__address = address
        self.__passport_link = passport_link
        self.__page = page

    async def collect_pdf(self) -> NoReturn:
        await self.__get_passport_page()
        await self.__click_all_btns()
        logger.info('Taking PDF...')
        await self.__download_page_pdf()

    async def __get_passport_page(self):
        await self.__page.goto(self.__passport_link)
        logger.info("Getting passport page...")
        await self.__page.wait_for_selector(
            '[ng-click="item.showChildren = !item.showChildren; loadChildItemsByParentItem(item);"]')

    async def __click_all_btns(self) -> NoReturn:
        await self.__click_first_level_btns()
        await self.__click_second_level_btns()
        await self.__click_all_third_level_btns()

    async def __click_first_level_btns(self) -> NoReturn:
        await self.__click_n_level_buttons_by_selector(
            1,
            '[ng-click="item.showChildren = !item.showChildren; loadChildItemsByParentItem(item);"]'
        )

    async def __click_second_level_btns(self) -> NoReturn:
        await self.__click_n_level_buttons_by_selector(2, 'tr.ng-scope:not(.ng-hide) .attr-body-td-node + td a')

    async def __click_all_third_level_btns(self) -> NoReturn:
        await self.__click_n_level_buttons_by_selector(
            3,
            'tr.ng-scope:not(.ng-hide) .attr-body-td-node[colspan="2"] + td a'
        )

    async def __click_n_level_buttons_by_selector(self, n: int, selector: str) -> NoReturn:
        btns = await self.__page.query_selector_all(selector)
        logger.info(f'Clicking all {n} level btns...')
        if n == 1:
            btns = btns[:-2]
        for index, btn in enumerate(btns):
            await btn.click()
            await asyncio.sleep(30)
            logger.info(f"{index + 1} / {len(btns)} btn is clicked")

    async def __download_page_pdf(self) -> NoReturn:
        await save_pdf_file(self.__page, BASE_DIR / 'test_responses' / f'Паспорт_МКД_{self.__address.strip()}.pdf')

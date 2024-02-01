import asyncio
import time
from enum import StrEnum
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse, parse_qs

from loguru import logger
from playwright.async_api import Page
from pypdf import PdfMerger

from parser.utils import BASE_DIR
from pdf_collector.utils import save_pdf_file


class Tab(StrEnum):
    GENERAL = 'li.text-center:nth-child(1)'
    CONSTRUCT_ELEMENTS = 'li.text-center:nth-child(2)'
    REPAIRINGS = 'li.text-center:nth-child(3)'
    UTILITIES = 'li.text-center:nth-child(4)'
    PUBLIC_PROPERTY = 'li.text-center:nth-child(5)'
    MAJOR_REPAIR = '.dropdown-menu-right > li:nth-child(1) > a:nth-child(1)'
    GENERAL_MEETINGS_INFO = '.dropdown-menu-right > li:nth-child(2) > a:nth-child(1)'
    REPORT = '.dropdown-menu-right > li:nth-child(3) > a:nth-child(1)'


class TabSelector(StrEnum):
    GENERAL = '.form-base_dim'
    CONSTRUCT_ELEMENTS = 'ef-och-duo-mkd-ce-common.ng-isolate-scope > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1)'
    REPAIRINGS = 'th.col-sm-12'
    UTILITIES = 'ef-och-duo-mkd-ps.ng-isolate-scope > div:nth-child(1) > div:nth-child(1) > table:nth-child(1)'
    PUBLIC_PROPERTY = '[ng-show="isActive(4)"]'
    MAJOR_REPAIR = '[ng-show="isActive(5)"]'
    GENERAL_MEETINGS_INFO = '[ng-show="isActive(6)"]'
    REPORT = '[ng-show="isActive(7)"]'


class ControlInfoCollector:
    def __init__(self, control_info_link: str, page: Page, address: str):
        self.__control_info_link = control_info_link
        self.__page = page
        self.__additional_tabs = (Tab.MAJOR_REPAIR.value, Tab.GENERAL_MEETINGS_INFO.value, Tab.REPORT.value)
        self.__address = address

    async def run(self) -> NoReturn:
        await self.__collect_all_info()

    async def __collect_all_info(self) -> NoReturn:
        await self.__page.goto(self.__control_info_link)
        for tab in Tab:
            await self.__get_control_info_tab(tab)
            index = self.__parse_tab_index_from_url()
            await self.__click_tab_btns_by_index(index)
            await save_pdf_file(self.__page, BASE_DIR / 'test_responses' / f'{self.__address}_{index}.pdf')
        self.__merge_pdfs_into_one_file(self.__address)

    async def __get_control_info_tab(self, tab: Tab) -> NoReturn:
        logger.debug(tab.name)
        if tab in self.__additional_tabs:
            await self.__click_dropdown_button()
        btn = await self.__page.wait_for_selector(tab.value)

        time.sleep(5)  # TODO: research why later

        await btn.click()
        if tab == Tab.REPAIRINGS:
            await self.__select_date_range()
        # await self.__page.wait_for_selector(TabSelector[tab.name].value, timeout=90_000)
        await asyncio.sleep(30)

    async def __click_dropdown_button(self) -> NoReturn:
        btn = await self.__page.wait_for_selector('.glyphicon-align-justify')
        await btn.click()
        await self.__page.wait_for_selector('.dropdown-menu-right')

    async def __select_date_range(self) -> NoReturn:
        logger.info('Select date range')
        try:
            select = await self.__page.wait_for_selector('.ui-select-toggle')
            await select.click()
            try:
                option = await self.__page.wait_for_selector('li.ui-select-choices-row:nth-child(1)')
                await option.click()
            except:
                return
        except Exception as ex:
            await self.__page.screenshot(path='./test_responses/fail.png', full_page=True)
            raise ex

    def __parse_tab_index_from_url(self) -> str:
        url = urlparse(self.__page.url)
        qs = parse_qs(url.fragment.replace("!/mkd?", ''))
        logger.debug("done")
        return qs.get('index')[0]

    async def __click_tab_btns_by_index(self, index: str) -> NoReturn:
        btns = await self.__page.query_selector_all(f'[ng-show="isActive({index})"] a.collapse-toggle__ctr')
        logger.info('Click tab btns' if len(btns) > 0 else 'No tab btns')
        for index, btn in enumerate(btns):
            await btn.click()
            await asyncio.sleep(10)
            logger.info(f'Clicked {index + 1} / {len(btns)} btn')

    @staticmethod
    def __merge_pdfs_into_one_file(address: str):
        logger.info('Merge PDFs...')
        files = sorted(Path(BASE_DIR / 'test_responses').glob(f"{address}_*.pdf"))
        merger = PdfMerger()
        for file in files:
            merger.append(file)

        merger.write(Path(BASE_DIR / 'test_responses' / f'ОУ_{address}.pdf'))
        merger.close()

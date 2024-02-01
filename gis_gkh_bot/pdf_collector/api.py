from pathlib import Path
from pathlib import Path
from typing import Literal

from playwright.async_api import async_playwright, Page

from parser.mkd import MKD
from parser.utils import Singleton, BASE_DIR
from pdf_collector.control_info import ControlInfoCollector
from pdf_collector.passport import PassportInfoCollector


class PDFCollector(metaclass=Singleton):
    def __init__(self):
        self.is_running = False

    async def run(self, action: Literal['control_info', 'passport'], passport_link: str, control_info_link: str,
                  address: str) -> Path:
        self.is_running = True
        async with async_playwright() as pw:
            context = await pw.chromium.launch(headless=True)
            async with context:
                page = await context.new_page()
                page.set_default_timeout(120_000)
                if action == 'passport':
                    path = await self.collect_passport_pdf(page, passport_link, address)
                else:
                    path = await self.collect_control_info_pdf(page, control_info_link, address)
                self.is_running = False
                return path

    @staticmethod
    async def collect_passport_pdf(page: Page, link: str, address: str) -> Path:
        if not Path(BASE_DIR / 'test_responses' / f'Паспорт_МКД_{address.replace("/", "_")}.pdf').exists():
            passport_info_collector = PassportInfoCollector(link, page, address)
            await passport_info_collector.collect_pdf()
        return Path(BASE_DIR / 'test_responses' / f'Паспорт_МКД_{address.replace("/", "_")}.pdf')

    @staticmethod
    async def collect_control_info_pdf(page: Page, link: str, address: str) -> Path:
        if not Path(BASE_DIR / 'test_responses' / f'ОУ_{address.replace("/", "_")}.pdf').exists():
            control_info_collector = ControlInfoCollector(link, page, address.replace("/", "_"))
            await control_info_collector.run()
        return Path(BASE_DIR / 'test_responses' / f'ОУ_{address.replace("/", "_")}.pdf')


async def run_collector(mkd: MKD):
    collector = PDFCollector()
    await collector.run(
        mkd.passport_link,
        mkd.orgs_link,
        mkd.address.replace("/", "_")
    )

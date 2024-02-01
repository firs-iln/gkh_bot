from pathlib import Path
from typing import NoReturn

from playwright.async_api import Page, PdfMargins


async def save_pdf_file(page: Page, path: Path) -> NoReturn:
    await page.emulate_media(media="print")
    margins = PdfMargins({'left': '2cm', 'right': '2cm', 'top': '2cm', 'bottom': '2cm'})
    await page.pdf(path=path, format='A4', print_background=True, scale=0.67,
                   display_header_footer=True, margin=margins)
    await page.emulate_media(media='screen')

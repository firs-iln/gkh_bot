from pathlib import Path

import gspread_asyncio
import pygsheets
from aiohttp import ClientSession
from bs4 import BeautifulSoup as soup, SoupStrainer
from google.oauth2.service_account import Credentials
from pygsheets import Worksheet

BASE_DIR = Path(__file__).parent.parent.resolve()


def extract_digits_from_string(string: str) -> str:
    return ''.join((char for char in string if char.isdigit()))


async def get_page_soup(session: ClientSession, link: str) -> soup:
    async with session.get(link) as response:
        return soup(await response.text(), features='lxml', parse_only=SoupStrainer('body'))


# First, set up a callback function that fetches our credentials off the disk.
# gspread_asyncio needs this to re-authenticate when credentials expire.

def get_creds():
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    creds = Credentials.from_service_account_file("gis-gkh-dce0833e31ca.json")
    scoped = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    return scoped


# Create an AsyncioGspreadClientManager object which
# will give us access to the Spreadsheet API.

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
__gc = pygsheets.authorize(service_file='./gis-gkh-dce0833e31ca.json')
__sh = __gc.open_by_url('https://docs.google.com/spreadsheets/d/1kGCdugwpVwuDO5LRC7tOxIkvMt_5iFQlGphLMAL107A/edit#gid=0')
__sh.share('', role='writer', type='anyone')
orgs_sheet: Worksheet = __sh.worksheet_by_title('Организации')
mkd_sheet: Worksheet = __sh.worksheet_by_title('МКД')
rooms_sheet: Worksheet = __sh.worksheet_by_title('Помещения')


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

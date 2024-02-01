import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio.utils import from_url

TOKEN = os.environ.get("TOKEN")
REDIS_HOST = os.environ.get("REDIS_HOST")

bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
__redis = from_url(REDIS_HOST)
__redis_storage = RedisStorage(__redis)
dp = Dispatcher(storage=__redis_storage)

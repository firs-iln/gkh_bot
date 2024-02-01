from loguru import logger

import asyncio

from bot.runner import run_bot
from pdf_collector.api import run_collector


async def main():
    await run_bot()


if __name__ == '__main__':
    with logger.catch():
        asyncio.run(main())
        # asyncio.run(run_collector())

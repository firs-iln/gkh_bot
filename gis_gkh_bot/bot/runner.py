from aiogram.types import BotCommand
from loguru import logger

from .handlers import start, infogis
from .config.bot import bot, dp


async def register_commands() -> None:
    commands = [
        BotCommand(command="gisgkh", description="Получить данные ГИС ЖКХ"),
        BotCommand(command="infogis", description="Показать данные по дому"),
        BotCommand(command="cancel", description="Отменить действие"),

    ]
    await bot.set_my_commands(commands)


async def run_bot():
    dp.include_router(start.router)
    dp.include_router(infogis.router)
    await register_commands()
    logger.success("Bot has started successfully")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

import logging
import log
from settings import Settings
from settings import settings as bot_settings

from db import Db
from services.api import ApiService
from services.storage import StorageService
from services.bot import BotService


def run(settings: Settings, logger: logging.Logger) -> None:
    db_service = Db(settings.postgres_dsn, logger)
    storage = StorageService(db_service, logger)
    api_service = ApiService(storage, settings.data_api_token, logger)
    api_service.update()
    BotService(storage, bot_settings.bot_token, logger)


if __name__ == '__main__':
    logger_ = log.get_logger("euro_oracle_bot", bot_settings.logger_level)
    logger_.info("Run Euro 2020 Oracle telegram bot")
    logger_.debug("Config: %s", bot_settings.json())
    run(bot_settings, logger_)

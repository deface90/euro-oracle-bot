"""
Settings module
"""
from pydantic import BaseSettings, PostgresDsn  # pylint: disable=E0611,E0401


# pylint: disable=too-few-public-methods
class Settings(BaseSettings):
    """
    :attr: bot_token
    :attr: postgres_dsn
    :attr: "logger_level" logging level
    """

    bot_token: str
    data_api_token: str
    postgres_dsn: PostgresDsn
    logger_level: str = "DEBUG"

    class Config:
        """
        Класс конфигурации настроек.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"


settings: Settings = Settings()

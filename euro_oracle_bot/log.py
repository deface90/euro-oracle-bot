import enum
import logging
from typing import Optional


class LogLevel(enum.Enum):
    QUIET = "NOTSET"
    FATAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


def get_logger(service_name: Optional[str] = None, level: str = "ERROR"):
    if hasattr(LogLevel, level):
        level = getattr(LogLevel, level).value
    else:
        raise ValueError("unexpected value for log_level {}".format(level))
    format_ = "%(asctime)s %(module)s %(levelname)s: %(message)s"
    logging.basicConfig(format=format_, datefmt='%Y-%m-%d %H:%M:%S %Z')
    logger = logging.getLogger(service_name)
    logger.setLevel(level)
    return logger

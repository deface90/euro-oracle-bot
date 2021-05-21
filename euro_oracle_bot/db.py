"""
Database service classes
"""
from logging import Logger

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError


class SessionContext:
    _logger: Logger

    def __init__(self, session):
        self.session = session
        if self._logger is None:
            raise AttributeError("logger not set")

    @classmethod
    def set_logger(cls, logger):
        cls._logger = logger

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(f"DB error: {exc_val.args}")
            self.session.rollback()
            if issubclass(exc_type, SQLAlchemyError):
                raise Exception from exc_val
        else:
            self.session.commit()
        self.session.close()


class Db:
    def __init__(self, dsn: str, logger: Logger):
        """
        :arg: dsn - connection url
        :arg: logger - logger object
        """
        self._dsn = dsn
        self._engine = create_engine(dsn, client_encoding='utf8')
        self._session_maker = sessionmaker(bind=self._engine, class_=Session)
        self.logger = logger
        SessionContext.set_logger(logger)

    def close(self):
        self._engine.dispose()
        self._engine = None
        self._session_maker = None

    def session_scope(self) -> SessionContext:
        session_ = self._session_maker(expire_on_commit=False)
        return SessionContext(session_)

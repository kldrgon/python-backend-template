"""SQLAlchemy session management - simple async version."""

from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from enum import Enum
import os
from typing import Any, AsyncGenerator, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.expression import Delete, Insert, Update

from pami_event_framework.utils import mask_url

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

session_context: ContextVar[str] = ContextVar("session_context")


def get_session_context() -> str:
    return session_context.get()


def set_session_context(session_id: str) -> Token:
    return session_context.set(session_id)


def reset_session_context(context: Token) -> None:
    session_context.reset(context)


class EngineType(Enum):
    WRITER = "writer"
    READER = "reader"


class SessionManager:
    def __init__(
        self,
        writer_db_url: str,
        reader_db_url: str | None = None,
        *,
        disable_pooling: bool = False,
        engine_options: Optional[Dict[str, Any]] = None,
    ):
        self.writer_db_url = writer_db_url
        self.reader_db_url = reader_db_url
        self.disable_pooling = disable_pooling
        self.engine_options = engine_options or {}

        writer_engine = self._create_engine(self.writer_db_url)
        need_separate_reader = reader_db_url and reader_db_url != self.writer_db_url
        self._engines = {
            EngineType.WRITER: writer_engine,
            EngineType.READER: (
                self._create_engine(reader_db_url)
                if need_separate_reader
                else writer_engine
            ),
        }
        self._async_session_factory = async_sessionmaker(
            class_=AsyncSession,
            sync_session_class=self._create_routing_session_class(),
            expire_on_commit=False,
        )
        self.session = async_scoped_session(
            session_factory=self._async_session_factory,
            scopefunc=get_session_context,
        )
        logger.info("session_manager_initialized", writer=mask_url(writer_db_url), reader=mask_url(self.reader_db_url))

    def _create_engine(self, db_url: str) -> AsyncEngine:
        options: Dict[str, Any] = {"pool_recycle": 3600, **self.engine_options}
        if self.disable_pooling:
            options["poolclass"] = NullPool
        return create_async_engine(db_url, **options)

    def _create_routing_session_class(self):
        manager = self

        class RoutingSession(Session):
            def get_bind(self, mapper=None, clause=None, **kw):
                engines = manager._engines
                if self._flushing or isinstance(clause, (Update, Delete, Insert)):
                    return engines[EngineType.WRITER].sync_engine

                from sqlalchemy.sql import Select

                if isinstance(clause, Select):
                    if hasattr(clause, "_for_update_arg") and clause._for_update_arg is not None:
                        return engines[EngineType.WRITER].sync_engine
                return engines[EngineType.READER].sync_engine

        return RoutingSession

    def init_for_worker(self) -> None:
        logger.info("worker_mode_enabled_for_session_manager")

    def get_session(self) -> async_scoped_session:
        return self.session

    @asynccontextmanager
    async def session_factory(self) -> AsyncGenerator[AsyncSession, None]:
        _session = self._async_session_factory()
        try:
            yield _session
            await _session.close()
        except GeneratorExit:
            raise
        except BaseException:
            await _session.close()
            raise

    async def close(self) -> None:
        for engine in self._engines.values():
            await engine.dispose()


class Base(DeclarativeBase):
    pass


_session_manager: Optional[SessionManager] = None


def _ensure_session_manager() -> SessionManager:
    """Lazy initialize a process-wide session manager."""
    global _session_manager
    if _session_manager is not None:
        return _session_manager

    from core.config import config as app_config

    is_test_env = os.environ.get("ENV") == "test" or app_config.app.env == "test"
    _session_manager = SessionManager(
        writer_db_url=app_config.db.writer_db_url,
        reader_db_url=app_config.db.reader_db_url,
        disable_pooling=is_test_env,
    )
    logger.info("session_manager_initialized_lazily")
    return _session_manager


def create_session_manager(
    *,
    writer_db_url: str,
    reader_db_url: Optional[str] = None,
    disable_pooling: bool = False,
    engine_options: Optional[Dict[str, Any]] = None,
) -> SessionManager:
    return SessionManager(
        writer_db_url=writer_db_url,
        reader_db_url=reader_db_url,
        disable_pooling=disable_pooling,
        engine_options=engine_options,
    )


@asynccontextmanager
async def session_factory() -> AsyncGenerator[AsyncSession, None]:
    manager = _ensure_session_manager()
    async with manager.session_factory() as session:
        yield session


def get_session() -> async_scoped_session:
    return _ensure_session_manager().get_session()


async def close_session_manager() -> None:
    global _session_manager
    if _session_manager is not None:
        await _session_manager.close()
        _session_manager = None

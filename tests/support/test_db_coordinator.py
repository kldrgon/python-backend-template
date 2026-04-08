from alembic import command
import time
from alembic.util.exc import CommandError
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, Engine, text
from sqlalchemy.engine import make_url, URL
from sqlalchemy.exc import DBAPIError

from core.config import config


class TestDbCoordinator:
    __test__ = False

    EXCLUDE_TABLES = {"alembic_version"}

    def __init__(self):
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            sync_url = self._make_sync_url(config.db.writer_db_url)
            self._engine = create_engine(url=sync_url)
            self._ensure_test_database(self._engine)
        return self._engine

    def _ensure_test_database(self, engine: Engine) -> None:
        db_name = (engine.url.database or "").lower()
        if "test" not in db_name:
            raise RuntimeError(
                f"危险操作：禁止在非测试库上执行测试操作！"
                f"当前数据库名为: {db_name!r}。"
                f"请确保数据库名包含 'test' 关键字。"
            )

    def apply_alembic(self) -> None:
        try:
            self._upgrade_to_head()
        except CommandError as exc:
            if not self._is_missing_revision_error(exc):
                raise
            self._reset_database_for_migrations()
            self._upgrade_to_head()

    def delete_all(self) -> None:
        """用 DELETE 清空所有表，避免 TRUNCATE 的 ACCESS EXCLUSIVE 锁"""
        tables = self._get_all_tables(engine=self.engine)
        with self.engine.begin() as conn:
            preparer = self.engine.dialect.identifier_preparer
            conn.execute(text("SET session_replication_role = 'replica'"))
            for table in tables:
                quoted = preparer.quote(table)
                conn.execute(text(f"DELETE FROM {quoted}"))
            conn.execute(text("SET session_replication_role = 'origin'"))

    def truncate_all(self) -> None:
        tables = self._get_all_tables(engine=self.engine)
        dialect = self.engine.dialect.name
        preparer = self.engine.dialect.identifier_preparer
        quoted_tables = [preparer.quote(t) for t in tables]

        for attempt in range(5):
            try:
                with self.engine.begin() as conn:
                    conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                    if dialect == "postgresql":
                        joined = ", ".join(quoted_tables)
                        if joined:
                            conn.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))
                    else:
                        for table in quoted_tables:
                            conn.execute(text(f"TRUNCATE TABLE {table}"))
                return
            except DBAPIError as exc:
                if "lock timeout" not in str(exc).lower():
                    raise
                if attempt < 4:
                    time.sleep(0.5 * (attempt + 1))
                    continue

                lock_rows = []
                try:
                    with self.engine.connect() as conn:
                        lock_rows = conn.execute(
                            text(
                                """
                                SELECT
                                    pid,
                                    state,
                                    wait_event_type,
                                    wait_event,
                                    left(query, 120) AS query
                                FROM pg_stat_activity
                                WHERE datname = current_database()
                                  AND pid <> pg_backend_pid()
                                ORDER BY query_start
                                LIMIT 8
                                """
                            )
                        ).mappings().all()
                except Exception:
                    lock_rows = []

                lock_details = "; ".join(
                    f"pid={r['pid']} state={r['state']} wait={r['wait_event_type']}/{r['wait_event']} sql={r['query']}"
                    for r in lock_rows
                )
                raise RuntimeError(
                    "truncate_all 发生锁等待超时（重试后仍失败）。"
                    f"请先清理测试库残留连接。当前活动连接: {lock_details}"
                ) from exc

    def _upgrade_to_head(self) -> None:
        alembic_cfg = AlembicConfig("alembic.ini")
        alembic_cfg.attributes["connection"] = self.engine
        with self.engine.begin() as conn:
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")

    def _is_missing_revision_error(self, exc: CommandError) -> bool:
        message = str(exc)
        return (
            "Can't locate revision identified by" in message
            or "No such revision or branch" in message
        )

    def _reset_database_for_migrations(self) -> None:
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        preparer = self.engine.dialect.identifier_preparer

        with self.engine.begin() as conn:
            conn.execute(text("SET session_replication_role = 'replica'"))
            for table_name in tables:
                quoted = preparer.quote(table_name)
                conn.execute(text(f"DROP TABLE IF EXISTS {quoted} CASCADE"))
            conn.execute(text("SET session_replication_role = 'origin'"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL
                    )
                    """
                )
            )

    def _get_all_tables(self, *, engine: Engine) -> list[str]:
        inspector = inspect(engine)
        tables = []
        for table_name in inspector.get_table_names():
            if table_name in self.EXCLUDE_TABLES:
                continue
            tables.append(table_name)
        return tables

    def _make_sync_url(self, async_url: str) -> str:
        url = make_url(async_url)
        if url.get_backend_name() in ("postgresql", "postgres"):
            drivername = "postgresql+psycopg"
        elif url.get_backend_name() in ("mysql",):
            drivername = "mysql+pymysql"
        else:
            drivername = url.get_backend_name()

        sync_url = URL.create(
            drivername=drivername,
            username=url.username,
            password=url.password,
            host=url.host,
            port=url.port,
            database=url.database,
            query=url.query,
        )
        return sync_url.render_as_string(hide_password=False)

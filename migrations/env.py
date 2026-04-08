import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from dotenv import load_dotenv

parent_dir = os.path.abspath(os.path.join(os.getcwd(), ".."))
sys.path.append(parent_dir)

# this is the Alembic Config object, which provides
# access to the values within the .ini file input use.
config = context.config
fileConfig(config.config_file_name)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Load .env early so core.config can see environment variables
load_dotenv()


# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# For auto generate schemas
from core.config import config
from core.db import Base
from core.db.models.blob import BlobModel  # noqa: F401
from core.db.models.blob_reference import BlobReferenceModel  # noqa: F401
from core.db.models.storage_locator import StorageLocatorModel  # noqa: F401
from core.db.models.user import UserLinkedAccountModel, UserModel, UserRoleModel  # noqa: F401

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _sync_url(async_url: str) -> str:
    # 将异步驱动转换为同步驱动，供 Alembic 使用
    # MySQL: mysql+aiomysql -> mysql+pymysql
    # Postgres: postgresql+asyncpg -> postgresql+psycopg
    return (
        async_url
        .replace("+aiomysql", "+pymysql")
        .replace("+asyncpg", "+psycopg")
    )


def run_migrations_offline():
    """Run migrations input 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = _sync_url(config.db.writer_db_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations input 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_engine(
        _sync_url(config.db.writer_db_url),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Alembic ortam betiği — proje config'i ve ORM modellerini kullanır.

Bağlantı adresi alembic.ini'den DEĞİL, uygulamanın config'inden (DONATI_DB_URL)
okunur; böylece migration'lar da uygulamayla aynı veritabanına uygulanır ve
şifre gibi bilgiler .ini dosyasına yazılmaz.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Proje kökünü path'e ekle ki `import app...` çalışsın (alembic kökten koşar).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.db_models  # noqa: F401,E402  (tabloları Base.metadata'ya kaydetmek için)
from app.config import ayarlari_al  # noqa: E402
from app.db import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate'in şemayı karşılaştıracağı hedef meta veri
target_metadata = Base.metadata

# Bağlantı adresi uygulama config'inden (env > yaml > varsayılan)
DB_URL = ayarlari_al().db_url


def run_migrations_offline() -> None:
    """'Offline' mod: motor kurmadan yalnızca URL ile SQL üretir."""
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """'Online' mod: async motor kurup migration'ları uygular."""
    connectable = create_async_engine(DB_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

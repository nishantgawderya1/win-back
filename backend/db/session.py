"""Async engine + session factory. Import get_db as a FastAPI dependency."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy import inspect, text

from backend.config import settings
from backend.db.models import Base

engine = create_async_engine(settings.database_url, echo=False, future=True)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Create tables, then add any columns missing from an older database.

    create_all() only creates tables it does not find; it never alters one that
    already exists. Columns added to a model after a database was first written
    would therefore be missing at runtime, which surfaces as a confusing
    OperationalError on the next query rather than at startup. This project has
    no migration tool, so reconcile the additive case directly — SQLite can add
    a nullable column in place, and every column added here is nullable or
    defaulted.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def _add_missing_columns(conn) -> None:
    inspector = inspect(conn)
    for table in Base.metadata.sorted_tables:
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            ddl = column.type.compile(dialect=conn.dialect)
            null = "" if column.nullable else " NOT NULL DEFAULT 0"
            conn.execute(
                text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {ddl}{null}')
            )
            print(f"[db] added {table.name}.{column.name}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

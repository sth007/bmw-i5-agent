from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


def require_test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required for database tests. Refusing to use DATABASE_URL as a fallback."
        )
    assert_test_database_url(database_url)
    return database_url


def extract_database_name(database_url: str) -> str:
    return make_url(database_url).database or ""


def assert_test_database_url(database_url: str) -> None:
    database_name = extract_database_name(database_url)
    if "test" not in database_name.lower():
        raise RuntimeError(
            f"Refusing to run database tests against non-test database: {database_name}"
        )


def ensure_database_exists(database_url: str, admin_database_url: str | None = None) -> None:
    target_url = make_url(database_url)
    admin_url = admin_database_url or _admin_database_url(target_url)
    engine = create_engine(admin_url, future=True, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": target_url.database},
            ).scalar()
            if not exists:
                connection.execute(
                    text(f'CREATE DATABASE "{target_url.database}"')
                )
    finally:
        engine.dispose()


def _admin_database_url(target_url: URL) -> str:
    return str(target_url.set(database="postgres"))

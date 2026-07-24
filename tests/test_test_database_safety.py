import os

import pytest

from app.database.test_database import (
    assert_test_database_url,
    extract_database_name,
    require_test_database_url,
)


def test_extract_database_name_returns_database_name() -> None:
    assert (
        extract_database_name(
            "postgresql+psycopg://bmw_agent:password@postgres:5432/bmw_agent_test"
        )
        == "bmw_agent_test"
    )


def test_assert_test_database_url_accepts_test_database() -> None:
    assert_test_database_url(
        "postgresql+psycopg://bmw_agent:password@postgres:5432/bmw_agent_test"
    )


def test_assert_test_database_url_rejects_application_database() -> None:
    with pytest.raises(
        RuntimeError,
        match="Refusing to run database tests against non-test database: bmw_agent_app",
    ):
        assert_test_database_url(
            "postgresql+psycopg://bmw_agent:password@postgres:5432/bmw_agent_app"
        )


def test_require_test_database_url_requires_explicit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    with pytest.raises(
        RuntimeError,
        match="TEST_DATABASE_URL is required for database tests",
    ):
        require_test_database_url()


def test_require_test_database_url_does_not_fallback_to_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://bmw_agent:password@postgres:5432/bmw_agent_app",
    )

    with pytest.raises(
        RuntimeError,
        match="TEST_DATABASE_URL is required for database tests",
    ):
        require_test_database_url()

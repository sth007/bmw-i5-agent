from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.session import get_db
from app.main import app


def _database_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://bmw_agent:bmw_agent@localhost:5432/bmw_agent_app",
        ),
    )


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(_database_url(), future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    with Session(db_engine, future=True, expire_on_commit=False) as session:
        yield session
        session.rollback()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

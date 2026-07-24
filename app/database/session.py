import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from collections.abc import Generator

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL ist nicht gesetzt.")

engine = create_engine(
    DATABASE_URL,
    echo=False,          # später zum Debuggen auf True setzen
    pool_pre_ping=True,  # prüft automatisch, ob die DB-Verbindung noch lebt
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
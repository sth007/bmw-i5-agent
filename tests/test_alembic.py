from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import settings


def test_alembic_upgrade_and_rollback() -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url)
    engine = create_engine(settings.database_url, future=True)

    command.upgrade(config, "head")
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "campaign" in table_names
    assert "dealer_offer" in table_names
    assert "price_history" not in table_names

    command.downgrade(config, "4f1e140dbedd")
    inspector = inspect(engine)
    table_names_after_downgrade = set(inspector.get_table_names())

    assert "campaign" not in table_names_after_downgrade
    assert "price_history" in table_names_after_downgrade

    command.upgrade(config, "head")

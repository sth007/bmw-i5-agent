from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.entities.dealer import Dealer  # noqa: F401
from app.database.base import Base
from app.entities.offer import Offer
from app.schemas.offer import OfferImport
from app.services.offer_import_service import OfferImportService


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    return Session(engine)


def create_offer_import(
    *,
    price: Decimal = Decimal("65000.00"),
    title: str = "BMW i5 Touring xDrive40",
) -> OfferImport:
    return OfferImport(
        source="test",
        external_id="offer-4711",
        dealer_id=None,
        title=title,
        model="i5 Touring",
        variant="xDrive40",
        price=price,
        currency="EUR",
        mileage_km=12000,
        first_registration="2025-03",
        power_kw=290,
        fuel_type="electric",
        transmission="automatic",
        drivetrain="xDrive",
        color="black",
        vin=None,
        url="https://example.com/offers/4711",
        image_url="https://example.com/images/4711.jpg",
    )


def test_import_creates_new_offer() -> None:
    with create_test_session() as session:
        service = OfferImportService(session)

        result = service.import_offers(
            [create_offer_import()]
        )

        assert result.received == 1
        assert result.created == 1
        assert result.updated == 0
        assert result.unchanged == 0

        stored_offer = session.query(Offer).one()

        assert stored_offer.source == "test"
        assert stored_offer.external_id == "offer-4711"
        assert stored_offer.price == Decimal("65000.00")
        assert stored_offer.is_active is True


def test_import_identical_offer_is_unchanged() -> None:
    with create_test_session() as session:
        service = OfferImportService(session)
        offer_data = create_offer_import()

        first_result = service.import_offers([offer_data])
        second_result = service.import_offers([offer_data])

        assert first_result.created == 1

        assert second_result.received == 1
        assert second_result.created == 0
        assert second_result.updated == 0
        assert second_result.unchanged == 1

        assert session.query(Offer).count() == 1


def test_import_changed_price_updates_offer() -> None:
    with create_test_session() as session:
        service = OfferImportService(session)

        service.import_offers(
            [
                create_offer_import(
                    price=Decimal("65000.00")
                )
            ]
        )

        result = service.import_offers(
            [
                create_offer_import(
                    price=Decimal("62500.00")
                )
            ]
        )

        assert result.received == 1
        assert result.created == 0
        assert result.updated == 1
        assert result.unchanged == 0

        stored_offer = session.query(Offer).one()

        assert stored_offer.price == Decimal("62500.00")


def test_import_changed_title_updates_offer() -> None:
    with create_test_session() as session:
        service = OfferImportService(session)

        service.import_offers(
            [
                create_offer_import(
                    title="BMW i5 Touring"
                )
            ]
        )

        result = service.import_offers(
            [
                create_offer_import(
                    title="BMW i5 Touring xDrive40 M Sport"
                )
            ]
        )

        assert result.updated == 1

        stored_offer = session.query(Offer).one()

        assert (
            stored_offer.title
            == "BMW i5 Touring xDrive40 M Sport"
        )
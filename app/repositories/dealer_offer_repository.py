import sqlite3
from datetime import date, datetime
from pathlib import Path

from app.domain.dealer_offer import DealerOffer


class DealerOfferRepository:
    """
    Speichert und lädt DealerOffer-Objekte in einer SQLite-Datenbank.
    """

    def __init__(self, database_path: str | Path = "data/bmw_agent.db"):
        self.database_path = Path(database_path)

        if str(self.database_path) != ":memory:":
            self.database_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dealer_offers (
                    offer_id TEXT PRIMARY KEY,

                    campaign_id TEXT NOT NULL,
                    configuration_id TEXT NOT NULL,
                    dealer_id TEXT NOT NULL,

                    list_price TEXT NOT NULL,
                    offer_price TEXT NOT NULL,

                    delivery_date TEXT,
                    production_date TEXT,

                    financing_available INTEGER NOT NULL,
                    leasing_available INTEGER NOT NULL,
                    trade_in_possible INTEGER NOT NULL,

                    contact_person TEXT,

                    email_subject TEXT,
                    email_text TEXT,

                    pdf_filename TEXT,

                    received_at TEXT NOT NULL,
                    notes TEXT
                )
                """
            )

            connection.commit()

    def save(self, offer: DealerOffer) -> DealerOffer:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO dealer_offers (
                        offer_id,
                        campaign_id,
                        configuration_id,
                        dealer_id,
                        list_price,
                        offer_price,
                        delivery_date,
                        production_date,
                        financing_available,
                        leasing_available,
                        trade_in_possible,
                        contact_person,
                        email_subject,
                        email_text,
                        pdf_filename,
                        received_at,
                        notes
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        offer.offer_id,
                        offer.campaign_id,
                        offer.configuration_id,
                        offer.dealer_id,
                        str(offer.list_price),
                        str(offer.offer_price),
                        self._date_to_string(offer.delivery_date),
                        self._date_to_string(offer.production_date),
                        int(offer.financing_available),
                        int(offer.leasing_available),
                        int(offer.trade_in_possible),
                        offer.contact_person,
                        offer.email_subject,
                        offer.email_text,
                        offer.pdf_filename,
                        offer.received_at.isoformat(),
                        offer.notes,
                    ),
                )

                connection.commit()

        except sqlite3.IntegrityError as error:
            raise ValueError(
                f"Das Angebot {offer.offer_id} ist bereits gespeichert."
            ) from error

        return offer

    def get_by_id(self, offer_id: str) -> DealerOffer | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM dealer_offers
                WHERE offer_id = ?
                """,
                (offer_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_offer(row)

    def list_all(self) -> list[DealerOffer]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM dealer_offers
                ORDER BY received_at DESC
                """
            ).fetchall()

        return [
            self._row_to_offer(row)
            for row in rows
        ]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS offer_count
                FROM dealer_offers
                """
            ).fetchone()

        return int(row["offer_count"])

    @staticmethod
    def _date_to_string(value: date | None) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _string_to_date(value: str | None) -> date | None:
        if value is None:
            return None

        return date.fromisoformat(value)

    @classmethod
    def _row_to_offer(
        cls,
        row: sqlite3.Row,
    ) -> DealerOffer:
        return DealerOffer(
            offer_id=row["offer_id"],
            campaign_id=row["campaign_id"],
            configuration_id=row["configuration_id"],
            dealer_id=row["dealer_id"],
            list_price=row["list_price"],
            offer_price=row["offer_price"],
            delivery_date=cls._string_to_date(
                row["delivery_date"]
            ),
            production_date=cls._string_to_date(
                row["production_date"]
            ),
            financing_available=bool(
                row["financing_available"]
            ),
            leasing_available=bool(
                row["leasing_available"]
            ),
            trade_in_possible=bool(
                row["trade_in_possible"]
            ),
            contact_person=row["contact_person"],
            email_subject=row["email_subject"],
            email_text=row["email_text"],
            pdf_filename=row["pdf_filename"],
            received_at=datetime.fromisoformat(
                row["received_at"]
            ),
            notes=row["notes"],
        )
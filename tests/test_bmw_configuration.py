from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.bmw_configuration import BMWConfiguration


def test_valid_bmw_configuration() -> None:
    configuration = BMWConfiguration(
        configuration_id="chtwyiio",
        configuration_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        model="BMW i5 Touring",
        variant="xDrive40",
        package="M Sportpaket",
        maximum_target_price=Decimal("60000.00"),
        payment_preference="cash",
        equipment=[
            "M Sportpaket",
            "Driving Assistant Professional",
            "M Sportpaket",
            "  ",
        ],
    )

    assert configuration.configuration_id == "chtwyiio"
    assert configuration.maximum_target_price == Decimal("60000.00")
    assert configuration.equipment == [
        "M Sportpaket",
        "Driving Assistant Professional",
    ]


def test_empty_model_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BMWConfiguration(
            configuration_id="chtwyiio",
            configuration_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
            model="   ",
            variant="xDrive40",
            maximum_target_price=Decimal("60000.00"),
        )


def test_negative_target_price_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BMWConfiguration(
            configuration_id="chtwyiio",
            configuration_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
            model="BMW i5 Touring",
            variant="xDrive40",
            maximum_target_price=Decimal("-1.00"),
        )


def test_invalid_payment_preference_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BMWConfiguration(
            configuration_id="chtwyiio",
            configuration_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
            model="BMW i5 Touring",
            variant="xDrive40",
            maximum_target_price=Decimal("60000.00"),
            payment_preference="leasing",  # type: ignore[arg-type]
        )
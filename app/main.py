from decimal import Decimal

from domain.bmw_configuration import BMWConfiguration


def main() -> None:
    configuration = BMWConfiguration(
        configuration_id="chtwyiio",
        configuration_url="https://configure.bmw.de/de_DE/configid/chtwyiio",
        model="BMW i5 Touring",
        variant="xDrive40",
        package="M Sportpaket",
        maximum_target_price=Decimal("60000.00"),
        payment_preference="cash",
        equipment=[],
    )

    print(configuration.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
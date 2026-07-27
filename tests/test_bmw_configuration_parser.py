from __future__ import annotations

from app.schemas.campaign import CampaignCustomerInput
from app.services.bmw_configuration_parser import BMWConfigurationParserService
from app.services.campaign_service import CampaignService


FULL_CONFIGURATION_URL = (
    "https://configure.bmw.de/de_DE/configure/"
    "G61E/51HH/FKSFU,P0A90,S0337,S03G9,S0337,S09QV/SE000001"
    "?initialConfigId=chtwyiio&effectDate=2026-09-08"
)


def test_full_configuration_url_extracts_expected_fields(db_session) -> None:
    service = BMWConfigurationParserService(db_session)

    parsed = service.parse(FULL_CONFIGURATION_URL)

    assert parsed.source.configuration_id == "chtwyiio"
    assert parsed.source.effect_date.isoformat() == "2026-09-08"
    assert parsed.vehicle.series_code == "G61E"
    assert parsed.vehicle.model_code == "51HH"
    assert parsed.configuration.paint.code == "P0A90"
    assert parsed.configuration.upholstery.code == "FKSFU"
    assert [option.code for option in parsed.configuration.options] == ["S0337", "S03G9", "S09QV"]
    assert parsed.parser.status == "PARTIALLY_PARSED"
    assert parsed.parser.warnings == ["Unknown option code: S09QV"]


def test_parse_and_store_is_idempotent_for_same_configuration(db_session) -> None:
    service = BMWConfigurationParserService(db_session)

    first = service.parse_and_store(FULL_CONFIGURATION_URL)
    db_session.commit()
    second = service.parse_and_store(FULL_CONFIGURATION_URL)
    db_session.commit()

    assert first.id == second.id
    assert len(second.features) == 5


def test_campaign_create_from_full_configuration_url_creates_vehicle_reference(db_session) -> None:
    parsed_configuration = BMWConfigurationParserService(db_session).parse_and_store(FULL_CONFIGURATION_URL)
    db_session.commit()

    response = CampaignService(db_session).create_from_config(
        campaign_name="BMW i5 Vollkonfiguration",
        config_url=FULL_CONFIGURATION_URL,
        dealer_limit=1,
        customer=CampaignCustomerInput(name="Max Mustermann"),
        maximum_target_price=57000,
        payment_preference="cash",
    )

    campaign = CampaignService(db_session).get_campaign(response.campaign_id)

    assert response.config_id == "chtwyiio"
    assert campaign is not None
    assert campaign.configuration is not None
    assert campaign.configuration.vehicle_configuration_id == parsed_configuration.id
    assert campaign.configuration.requirements[0].feature_key == "vehicle.model_name"

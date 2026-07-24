from decimal import Decimal

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.configuration_requirement import ConfigurationRequirement
from app.repositories.campaign_repository import CampaignRepository


def test_campaign_repository_persists_nested_configuration(db_session) -> None:
    campaign = Campaign(name="BMW i5 Juli", status="draft", notes="Test")
    campaign.configuration = CampaignConfiguration(
        model="BMW i5",
        variant="eDrive40",
        maximum_target_price=Decimal("70000.00"),
        payment_preference="cash",
    )
    campaign.configuration.requirements = [
        ConfigurationRequirement(
            feature_key="Farbe",
            feature_value="Schwarz",
            normalized_key="farbe",
            normalized_value="schwarz",
            is_mandatory=True,
        )
    ]

    repository = CampaignRepository(db_session)
    repository.add(campaign)
    repository.commit()

    loaded = repository.get(campaign.id)

    assert loaded is not None
    assert loaded.configuration.model == "BMW i5"
    assert loaded.configuration.requirements[0].normalized_key == "farbe"


def test_session_rollback_discards_uncommitted_changes(db_session) -> None:
    campaign = Campaign(name="Rollback", status="draft")
    db_session.add(campaign)
    db_session.flush()
    db_session.rollback()

    assert CampaignRepository(db_session).get(campaign.id) is None


def test_tests_run_against_postgresql(db_engine) -> None:
    assert db_engine.dialect.name == "postgresql"

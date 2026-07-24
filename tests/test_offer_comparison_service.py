from decimal import Decimal
from uuid import uuid4

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.configuration_requirement import ConfigurationRequirement
from app.entities.dealer_offer import DealerOffer
from app.entities.dealer_offer_feature import DealerOfferFeature
from app.services.offer_comparison_service import OfferComparisonService


def build_configuration() -> CampaignConfiguration:
    campaign = Campaign(name="BMW i5", status="draft")
    configuration = CampaignConfiguration(
        campaign=campaign,
        model="BMW i5",
        variant="eDrive40",
        maximum_target_price=Decimal("70000.00"),
        payment_preference="either",
    )
    configuration.requirements = [
        ConfigurationRequirement(
            feature_key="Lackierung",
            feature_value="Black Sapphire",
            normalized_key="lackierung",
            normalized_value="black sapphire",
            is_mandatory=True,
        ),
        ConfigurationRequirement(
            feature_key="Panoramadach",
            feature_value="ja",
            normalized_key="panoramadach",
            normalized_value="true",
            is_mandatory=False,
        ),
    ]
    return configuration


def test_exact_offer_scores_100() -> None:
    configuration = build_configuration()
    offer = DealerOffer(
        campaign_id=uuid4(),
        dealer_name="Dealer A",
        raw_response="Antwort",
        total_price=Decimal("65000.00"),
    )
    offer.features = [
        DealerOfferFeature(
            feature_key="Lackierung",
            feature_value="Black Sapphire",
            normalized_key="lackierung",
            normalized_value="black sapphire",
            is_available=True,
        ),
        DealerOfferFeature(
            feature_key="Panoramadach",
            feature_value="ja",
            normalized_key="panoramadach",
            normalized_value="true",
            is_available=True,
        ),
    ]

    result = OfferComparisonService().compare(configuration, offer)

    assert result.category == "exact"
    assert result.score == 100


def test_optional_mismatch_becomes_alternative() -> None:
    configuration = build_configuration()
    offer = DealerOffer(
        campaign_id=uuid4(),
        dealer_name="Dealer B",
        raw_response="Antwort",
        total_price=Decimal("64000.00"),
    )
    offer.features = [
        DealerOfferFeature(
            feature_key="Lackierung",
            feature_value="Black Sapphire",
            normalized_key="lackierung",
            normalized_value="black sapphire",
            is_available=True,
        ),
    ]

    result = OfferComparisonService().compare(configuration, offer)

    assert result.category == "alternative"
    assert 60 <= result.score <= 99


def test_mandatory_mismatch_becomes_incompatible() -> None:
    configuration = build_configuration()
    offer = DealerOffer(
        campaign_id=uuid4(),
        dealer_name="Dealer C",
        raw_response="Antwort",
        total_price=Decimal("63000.00"),
    )
    offer.features = [
        DealerOfferFeature(
            feature_key="Lackierung",
            feature_value="Frozen Pure Grey",
            normalized_key="lackierung",
            normalized_value="frozen pure grey",
            is_available=True,
        ),
    ]

    result = OfferComparisonService().compare(configuration, offer)

    assert result.category == "incompatible"
    assert 0 <= result.score <= 59

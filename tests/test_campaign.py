import pytest

from app.domain.campaign import Campaign, CampaignStatus


def create_campaign() -> Campaign:
    return Campaign(
        campaign_id="campaign-001",
        name="BMW i5 Händleranfrage Juli 2026",
        configuration_id="chtwyiio",
        dealer_ids=[
            "dealer-001",
            "dealer-002",
            "dealer-003",
        ],
        batch_size=2,
    )


def test_campaign_is_created_as_draft() -> None:
    campaign = create_campaign()

    assert campaign.status == CampaignStatus.DRAFT
    assert campaign.contacted_count == 0
    assert campaign.replied_count == 0
    assert campaign.remaining_count == 3


def test_campaign_can_be_started() -> None:
    campaign = create_campaign()

    campaign.start()

    assert campaign.status == CampaignStatus.RUNNING
    assert campaign.started_at is not None


def test_campaign_without_dealers_cannot_start() -> None:
    campaign = Campaign(
        campaign_id="campaign-002",
        name="Leere Kampagne",
        configuration_id="chtwyiio",
        dealer_ids=[],
    )

    assert campaign.can_start() is False

    with pytest.raises(ValueError):
        campaign.start()


def test_next_dealer_batch_respects_batch_size() -> None:
    campaign = create_campaign()

    assert campaign.next_dealer_batch() == [
        "dealer-001",
        "dealer-002",
    ]


def test_contacted_dealer_is_removed_from_next_batch() -> None:
    campaign = create_campaign()

    campaign.mark_contacted("dealer-001")

    assert campaign.next_dealer_batch() == [
        "dealer-002",
        "dealer-003",
    ]
    assert campaign.contacted_count == 1
    assert campaign.remaining_count == 2


def test_unknown_dealer_cannot_be_marked_contacted() -> None:
    campaign = create_campaign()

    with pytest.raises(ValueError):
        campaign.mark_contacted("dealer-999")


def test_reply_requires_previous_contact() -> None:
    campaign = create_campaign()

    with pytest.raises(ValueError):
        campaign.mark_replied("dealer-001")


def test_contacted_dealer_can_be_marked_replied() -> None:
    campaign = create_campaign()

    campaign.mark_contacted("dealer-001")
    campaign.mark_replied("dealer-001")

    assert campaign.replied_dealer_ids == ["dealer-001"]
    assert campaign.replied_count == 1


def test_campaign_can_be_paused() -> None:
    campaign = create_campaign()

    campaign.start()
    campaign.pause()

    assert campaign.status == CampaignStatus.PAUSED


def test_campaign_can_be_completed() -> None:
    campaign = create_campaign()

    campaign.start()
    campaign.complete()

    assert campaign.status == CampaignStatus.COMPLETED
    assert campaign.completed_at is not None